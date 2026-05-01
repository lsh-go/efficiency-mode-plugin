---
description: Summarize current session and guide to /compact or /clear to reduce context size and save costs.
---

The user wants to reduce context size to minimize API costs.

Do the following in order:

1. **현재 세션 상태 요약** (2-3줄):
   - 이번 세션에서 다룬 핵심 작업 목록
   - 결정된 사항 / 완료된 작업
   - 아직 진행 중인 작업

2. **비용 절감 조언** - 상황에 맞게 하나를 선택:
   - 새 주제로 넘어간다면: `/clear` 로 완전 초기화 권장
   - 현재 작업 이어간다면: `/compact` 로 히스토리 압축 권장
   - 짧은 세션이라면: 그냥 계속해도 됨

3. 다음 텍스트를 그대로 출력:
   ```
   [SLIM] 위 요약을 메모해두고 /compact 또는 /clear 를 실행하세요.
   /compact — 현재 컨텍스트 압축 (대화 이어감)
   /clear   — 완전 초기화 (새 주제 시작 시)
   ```

짧고 직접적으로 처리할 것. 추가 설명 불필요.
