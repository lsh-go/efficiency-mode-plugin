#!/usr/bin/env python3
"""PreToolUse hook — Read 호출 시 limit 없으면 경고 주입.

동작:
  - Read 호출에 limit 파라미터 없으면 systemMessage로 경고
  - Grep/Glob 대안 제시
  - 차단(block)은 안 함 — Claude가 판단해서 limit 추가하도록 유도

토큰 절감 원리:
  - Read 전체 파일 = 수천 토큰 (예: 500줄 파일 ≈ 3,000 토큰)
  - Read limit:100 = ~600 토큰
  - Grep 결과 = 수십 토큰
  이 훅이 Claude를 Grep/제한 Read로 유도 → 파일 읽기 토큰 70~90% 절감
"""
import sys
import json


# 전체 읽기가 정당한 확장자 (작은 설정 파일 등)
SMALL_FILE_EXTENSIONS = {".env", ".cfg", ".ini", ".toml", ".yaml", ".yml"}


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return

    tool_name = data.get("tool_name", "")

    if tool_name != "Read":
        print(json.dumps({}))
        return

    tool_input = data.get("tool_input", {})
    file_path = tool_input.get("file_path", "")
    has_limit = tool_input.get("limit") is not None
    has_offset = tool_input.get("offset") is not None

    # limit 있으면 통과
    if has_limit:
        print(json.dumps({}))
        return

    # 작은 파일 확장자면 통과
    ext = "." + file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    if ext in SMALL_FILE_EXTENSIONS:
        print(json.dumps({}))
        return

    msg = (
        f"COST GUARD: Reading '{file_path}' without limit may use thousands of tokens. "
        "Before proceeding, consider: "
        "(1) Grep for specific content instead of reading the full file, "
        "(2) Add limit:100 to read only the first 100 lines, "
        "(3) Use offset+limit to read a specific section. "
        "Only read the full file if ALL content is needed."
    )

    print(json.dumps({"systemMessage": msg}))


if __name__ == "__main__":
    main()
    sys.exit(0)
