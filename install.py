#!/usr/bin/env python3
"""efficiency-mode 플러그인 설치 스크립트.

사용법:
  python install.py           # 설치
  python install.py --remove  # 제거
  python install.py --check   # 설치 상태 확인

지원 OS: Windows, macOS, Linux
Python: 3.8+
"""
import os
import sys
import json
import shutil
import argparse
import platform
from pathlib import Path

# Windows 콘솔 UTF-8 출력
if platform.system() == "Windows":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

PLUGIN_NAME = "efficiency-mode"
PLUGIN_DIR = Path(__file__).parent.resolve()


def get_claude_dir() -> Path:
    """OS별 ~/.claude 디렉토리 경로."""
    if platform.system() == "Windows":
        return Path(os.environ.get("USERPROFILE", "~")) / ".claude"
    return Path.home() / ".claude"


def find_python() -> str:
    """설치된 Python 실행 경로 탐색."""
    candidates = [
        sys.executable,  # 현재 스크립트 실행 중인 Python
        "C:/ProgramData/Anaconda3/python.exe",
        "C:/Users/" + os.environ.get("USERNAME", "") + "/Anaconda3/python.exe",
        "/usr/bin/python3",
        "/usr/local/bin/python3",
        "python3",
        "python",
    ]
    for path in candidates:
        if Path(path).exists() or shutil.which(path):
            return path
    return sys.executable


def read_settings(settings_path: Path) -> dict:
    if settings_path.exists():
        try:
            return json.loads(settings_path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def write_settings(settings_path: Path, data: dict):
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8"
    )


def install(python_exe: str, claude_dir: Path):
    """플러그인 설치."""
    # 1. 플러그인 파일 복사
    target_plugin_dir = claude_dir / "plugins" / "local" / PLUGIN_NAME
    if target_plugin_dir.exists() and target_plugin_dir != PLUGIN_DIR:
        shutil.rmtree(target_plugin_dir)
    if target_plugin_dir != PLUGIN_DIR:
        shutil.copytree(PLUGIN_DIR, target_plugin_dir)
        print(f"[OK] 플러그인 복사: {target_plugin_dir}")
    else:
        print(f"[OK] 플러그인 이미 위치: {target_plugin_dir}")

    hook_compress = str(target_plugin_dir / "hooks" / "prompt_compress.py")
    hook_guard = str(target_plugin_dir / "hooks" / "session_guard.py")

    # Windows 경로 슬래시 통일
    if platform.system() == "Windows":
        hook_compress = hook_compress.replace("\\", "/")
        hook_guard = hook_guard.replace("\\", "/")
        python_exe = python_exe.replace("\\", "/")

    # 2. settings.json에 훅 등록
    settings_path = claude_dir / "settings.json"
    settings = read_settings(settings_path)

    hooks = settings.setdefault("hooks", {})

    # UserPromptSubmit
    ups_hooks = hooks.setdefault("UserPromptSubmit", [])
    compress_cmd = f"{python_exe} {hook_compress}"
    # 중복 방지: 같은 hook이 없으면 추가
    existing_cmds = [
        h["command"]
        for entry in ups_hooks
        for h in entry.get("hooks", [])
    ]
    if compress_cmd not in existing_cmds:
        ups_hooks.append({"hooks": [{"type": "command", "command": compress_cmd, "timeout": 5}]})
        print(f"[OK] UserPromptSubmit 훅 등록")
    else:
        print(f"[--] UserPromptSubmit 훅 이미 등록됨")

    # Stop
    stop_hooks = hooks.setdefault("Stop", [])
    guard_cmd = f"{python_exe} {hook_guard}"
    existing_stop = [
        h["command"]
        for entry in stop_hooks
        for h in entry.get("hooks", [])
    ]
    if guard_cmd not in existing_stop:
        stop_hooks.append({"hooks": [{"type": "command", "command": guard_cmd, "timeout": 5}]})
        print(f"[OK] Stop 훅 등록")
    else:
        print(f"[--] Stop 훅 이미 등록됨")

    write_settings(settings_path, settings)

    # 3. 커맨드 등록 (~/.claude/commands/)
    commands_dir = claude_dir / "commands"
    commands_dir.mkdir(exist_ok=True)
    for skill_name in ["opt", "slim"]:
        src = target_plugin_dir / "skills" / skill_name / "SKILL.md"
        dst = commands_dir / f"{skill_name}.md"
        if src.exists():
            shutil.copy2(src, dst)
            print(f"[OK] /{skill_name} 커맨드 등록")

    print("\n설치 완료.")
    print("- 훅: Claude Code 재시작 시 자동 활성화")
    print("- 슬래시 커맨드: /opt <prompt>, /slim")


def remove(claude_dir: Path):
    """플러그인 제거."""
    settings_path = claude_dir / "settings.json"
    settings = read_settings(settings_path)
    plugin_path_fragment = f"plugins/local/{PLUGIN_NAME}"

    # hooks에서 이 플러그인 항목 제거
    changed = False
    for event in ("UserPromptSubmit", "Stop"):
        original = settings.get("hooks", {}).get(event, [])
        filtered = [
            entry for entry in original
            if not any(
                plugin_path_fragment in h.get("command", "")
                for h in entry.get("hooks", [])
            )
        ]
        if len(filtered) != len(original):
            settings["hooks"][event] = filtered
            changed = True
            print(f"[OK] {event} 훅 제거")

    if changed:
        write_settings(settings_path, settings)

    # 커맨드 제거
    for skill_name in ["opt", "slim"]:
        cmd_path = claude_dir / "commands" / f"{skill_name}.md"
        if cmd_path.exists():
            cmd_path.unlink()
            print(f"[OK] /{skill_name} 커맨드 제거")

    # 플러그인 디렉토리 제거
    target = claude_dir / "plugins" / "local" / PLUGIN_NAME
    if target.exists():
        shutil.rmtree(target)
        print(f"[OK] 플러그인 디렉토리 제거: {target}")

    print("\n제거 완료.")


def check(claude_dir: Path):
    """설치 상태 확인."""
    print(f"Claude dir: {claude_dir}")
    plugin_dir = claude_dir / "plugins" / "local" / PLUGIN_NAME
    print(f"Plugin dir: {'존재' if plugin_dir.exists() else '없음'} ({plugin_dir})")

    settings = read_settings(claude_dir / "settings.json")
    plugin_fragment = f"plugins/local/{PLUGIN_NAME}"

    for event in ("UserPromptSubmit", "Stop"):
        hooks = settings.get("hooks", {}).get(event, [])
        found = any(
            plugin_fragment in h.get("command", "")
            for entry in hooks
            for h in entry.get("hooks", [])
        )
        print(f"Hook {event}: {'등록됨' if found else '없음'}")

    for skill in ["opt", "slim"]:
        cmd = claude_dir / "commands" / f"{skill}.md"
        print(f"Command /{skill}: {'등록됨' if cmd.exists() else '없음'}")


def main():
    parser = argparse.ArgumentParser(description=f"{PLUGIN_NAME} 플러그인 설치/제거")
    parser.add_argument("--remove", action="store_true", help="플러그인 제거")
    parser.add_argument("--check", action="store_true", help="설치 상태 확인")
    parser.add_argument("--python", default=None, help="Python 실행 경로 지정")
    args = parser.parse_args()

    claude_dir = get_claude_dir()
    python_exe = args.python or find_python()

    print(f"Python: {python_exe}")
    print(f"Claude: {claude_dir}\n")

    if args.check:
        check(claude_dir)
    elif args.remove:
        remove(claude_dir)
    else:
        install(python_exe, claude_dir)


if __name__ == "__main__":
    main()
