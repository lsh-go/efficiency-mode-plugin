#!/usr/bin/env python3
"""Stop hook — 세션 길이 감시, /compact 타이밍 제안.

동작:
  - 매 응답 완료 후 실행
  - human turns 수 기반으로 compact 필요 여부 판단
  - transcript 크기(chars)로 실제 컨텍스트 부하 추정

threshold:
  - 10턴 이상: 주의 (soft)
  - 18턴 이상: 강력 권고 → /compact 실행 촉구
  - 25턴 이상: 긴급 — 현재 대화 요약 후 /compact 유도
"""
import sys
import json

WARN_TURNS = 10
COMPACT_TURNS = 18
URGENT_TURNS = 25

# 컨텍스트 부하 추정 (chars → approximate tokens)
CHARS_PER_TOKEN = 3.5
COMPACT_SUGGESTION_TOKENS = 40_000  # ~40K 토큰 이상이면 권고


def count_transcript(transcript: list) -> tuple[int, int]:
    """(human_turns, total_chars) 반환."""
    human = sum(1 for m in transcript if m.get("role") in ("human", "user"))
    total = sum(len(str(m.get("content", ""))) for m in transcript)
    return human, total


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return

    transcript = data.get("transcript", [])
    if not transcript:
        print(json.dumps({}))
        return

    human_turns, total_chars = count_transcript(transcript)
    est_tokens = int(total_chars / CHARS_PER_TOKEN)

    result = {}

    if human_turns >= URGENT_TURNS:
        result["systemMessage"] = (
            f"[SESSION GUARD] URGENT: {human_turns} turns / ~{est_tokens:,} tokens. "
            "Context is critically long — costs are high. "
            "Type /compact NOW to compress history before continuing."
        )
    elif human_turns >= COMPACT_TURNS or est_tokens >= COMPACT_SUGGESTION_TOKENS:
        result["systemMessage"] = (
            f"[SESSION GUARD] {human_turns} turns / ~{est_tokens:,} tokens. "
            "Consider running /compact to reduce context and save costs."
        )
    elif human_turns >= WARN_TURNS:
        result["systemMessage"] = (
            f"[SESSION GUARD] {human_turns} turns in session. "
            "Context growing — /compact available when ready."
        )

    print(json.dumps(result))


if __name__ == "__main__":
    main()
    sys.exit(0)
