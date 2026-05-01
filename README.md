# efficiency-mode

Claude Code 토큰/비용 최소화 플러그인.

## 기능

| 컴포넌트 | 동작 | 효과 |
|---------|------|------|
| **UserPromptSubmit 훅** | 매 프롬프트마다 간결 응답 지시 주입 | 출력 토큰 30~50% 절감 |
| **Stop 훅** | 세션 길이 감시 (10/18/25턴) | 컨텍스트 폭발 방지 |
| `/opt <prompt>` | Ollama로 프롬프트 압축 | 입력 의도 명확화 |
| `/slim` | 세션 요약 + compact 가이드 | 수동 컨텍스트 정리 |

## 설치

### 로컬 플러그인 (현재)

settings.json hooks에 직접 등록되어 있음:

```json
{
  "hooks": {
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "python.exe .../hooks/prompt_compress.py" }] }],
    "Stop": [{ "hooks": [{ "type": "command", "command": "python.exe .../hooks/session_guard.py" }] }]
  }
}
```

skills는 `~/.claude/commands/`에 복사하거나 플러그인 설치 후 자동 로드.

## 요구사항

- Python 3.9+
- Ollama (선택, `/opt` 커맨드용): `ollama serve`
  - 모델: `minicpm-v:latest` 또는 `llava-phi3:latest`

## 세션 가드 임계값

| 턴 수 | 동작 |
|------|------|
| 10턴 | "compact 가능" 알림 |
| 18턴 | compact 권고 |
| 25턴 | 긴급 compact 촉구 |
