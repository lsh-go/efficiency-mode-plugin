#!/usr/bin/env python3
"""PreToolUse hook — Read 가로채서 Ollama로 요약 후 Claude에 전달.

동작 우선순위:
  1. limit 있으면 → 통과 (이미 제한됨)
  2. 작은 파일 확장자 → 통과
  3. 파일 크기 < 100줄 → 통과
  4. Ollama 실행 중 → 파일 읽어서 Ollama 요약 → block + 요약 전달
  5. Ollama 없음 → 경고 systemMessage만 주입

토큰 절감:
  - 500줄 Python 파일 원본: ~3,000 토큰
  - Ollama 요약본: ~200~400 토큰
  - 절감률: ~85%
"""
import sys
import json
import os
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from stats_tracker import record_file_intercept as _record
    _HAS_TRACKER = True
except ImportError:
    _HAS_TRACKER = False

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "minicpm-v:latest"
OLLAMA_TIMEOUT = 25  # 초 (큰 파일은 시간 걸림)

# 전체 읽기 허용 확장자 (보통 작고 전체 맥락 필요)
PASSTHROUGH_EXTENSIONS = {".env", ".cfg", ".ini", ".toml", ".yaml", ".yml", ".json"}

# Ollama에 보낼 최대 문자 수 (컨텍스트 초과 방지)
MAX_CONTENT_CHARS = 8000


def get_user_question(transcript: list) -> str:
    """transcript에서 가장 최근 사용자 메시지 추출."""
    for msg in reversed(transcript):
        if msg.get("role") in ("human", "user"):
            content = msg.get("content", "")
            if isinstance(content, list):
                # multipart content
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return block.get("text", "")[:300]
            return str(content)[:300]
    return ""


def read_file_content(file_path: str):
    """파일 읽기 시도 (절대/상대 경로 모두)."""
    paths = [file_path]
    # 상대 경로면 cwd 기준으로도 시도
    if not os.path.isabs(file_path):
        paths.append(os.path.join(os.getcwd(), file_path))

    for p in paths:
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            continue
    return None


def call_ollama(content: str, question: str):
    """Ollama로 파일 내용 요약 요청."""
    system = (
        "You are a code analysis assistant. "
        "Given a user question and file content, extract ONLY the relevant parts. "
        "Include: relevant functions/classes/variables, their signatures, key logic. "
        "Exclude: unrelated code, imports not relevant to the question, comments. "
        "Be concise. Use the same language as the question."
    )

    prompt = (
        f"Question: {question}\n\n"
        f"File content:\n```\n{content[:MAX_CONTENT_CHARS]}\n```\n\n"
        "Extract only the parts relevant to the question:"
    )

    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "system": system,
        "prompt": prompt,
        "stream": False,
        "options": {
            "num_predict": 800,
            "temperature": 0.1,
        }
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=OLLAMA_TIMEOUT) as resp:
            result = json.loads(resp.read())
            return result.get("response", "").strip()
    except Exception:
        return None


def is_ollama_running() -> bool:
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=2):
            return True
    except Exception:
        return False


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return

    if data.get("tool_name") != "Read":
        print(json.dumps({}))
        return

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")

    # limit 있으면 통과
    if tool_input.get("limit") is not None:
        print(json.dumps({}))
        return

    # 허용 확장자 통과
    ext = ("." + file_path.rsplit(".", 1)[-1].lower()) if "." in file_path else ""
    if ext in PASSTHROUGH_EXTENSIONS:
        print(json.dumps({}))
        return

    # 파일 읽기
    content = read_file_content(file_path)
    if content is None:
        print(json.dumps({}))
        return

    lines = content.splitlines()

    # 짧은 파일(100줄 이하) 통과
    if len(lines) <= 100:
        print(json.dumps({}))
        return

    # Ollama 없으면 경고만
    if not is_ollama_running():
        msg = (
            f"COST GUARD: '{file_path}' is {len(lines)} lines (~{len(lines)*6} tokens). "
            "Add limit parameter or use Grep for specific content."
        )
        print(json.dumps({"systemMessage": msg}))
        return

    # Ollama로 요약
    question = get_user_question(data.get("transcript", []))
    if not question:
        question = "Summarize the key functions and structure of this file."

    summary = call_ollama(content, question)

    if summary:
        original_tokens = len(lines) * 6  # 대략적 추정
        summary_tokens = len(summary) // 4
        saved = original_tokens - summary_tokens

        if _HAS_TRACKER:
            _record(file_path, original_tokens, summary_tokens)

        block_reason = (
            f"[Ollama summarized '{file_path}': {len(lines)} lines → ~{summary_tokens} tokens "
            f"(saved ~{saved} tokens)]\n\n"
            f"{summary}\n\n"
            f"[End of Ollama summary. Do not re-read this file unless the summary is insufficient.]"
        )
        print(json.dumps({"decision": "block", "reason": block_reason}))
    else:
        # 요약 실패 → 경고만
        msg = (
            f"COST GUARD: Ollama summarization failed for '{file_path}'. "
            "Add limit:100 to read only relevant lines."
        )
        print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    main()
    sys.exit(0)
