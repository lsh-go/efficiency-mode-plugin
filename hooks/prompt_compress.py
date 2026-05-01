#!/usr/bin/env python3
"""UserPromptSubmit hook — Claude 응답 간소화 지시 주입.

전략:
  - Ollama 의존 제거 (minicpm-v/llava-phi3은 압축에 부적합)
  - 핵심 효과: Claude 출력에 conciseness 지시 → 응답 토큰 30~50% 절감
  - 슬래시 커맨드 (/compact, /clear 등)는 패스

비용 절감 원리:
  - Claude의 기본 행동: 서문, 질문 재진술, 마무리 요약 등을 포함
  - 이 훅이 매 턴마다 "간결하게"를 주입 → 응답 토큰 대폭 감소
  - 입력 토큰은 systemMessage 20~30 토큰 추가되지만
    출력 토큰 절감이 훨씬 크므로 net positive
"""
import sys
import json

CONCISE_INSTRUCTION = (
    "EFFICIENCY MODE: "
    "Respond concisely. No preamble, no restating the question, no trailing summary. "
    "Lead with the answer. Skip explanations unless explicitly asked. "
    "Use code/lists over prose when appropriate."
)


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        print(json.dumps({}))
        return

    user_msg = data.get("prompt", "")

    # 슬래시 커맨드 / 빈 메시지 패스
    if not user_msg or user_msg.startswith("/"):
        print(json.dumps({}))
        return

    print(json.dumps({"systemMessage": CONCISE_INSTRUCTION}))


if __name__ == "__main__":
    main()
    sys.exit(0)
