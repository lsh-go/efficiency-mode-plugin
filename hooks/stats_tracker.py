#!/usr/bin/env python3
"""efficiency-mode 비용 절감 추적 모듈.

훅들이 import해서 사용:
  from stats_tracker import record_file_intercept, record_prompt_turn, record_session_end

CLI 리포트:
  python3 stats_tracker.py --report
  python3 stats_tracker.py --reset
"""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

STATS_PATH = Path.home() / ".claude" / "efficiency-mode-stats.json"
MAX_EVENTS = 300
INPUT_PRICE_PER_M = 3.0   # $3 / 1M input tokens (Claude Sonnet)
OUTPUT_PRICE_PER_M = 15.0  # $15 / 1M output tokens


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _empty_stats() -> dict:
    return {
        "schema_version": 1,
        "created_at": _now_iso(),
        "last_updated": _now_iso(),
        "totals": {
            "file_read_intercepts": 0,
            "tokens_saved_input": 0,
            "cost_saved_usd": 0.0,
            "prompt_turns_compressed": 0,
            "sessions_tracked": 0,
        },
        "daily": {},
        "events": [],
    }


def _empty_daily() -> dict:
    return {
        "file_read_intercepts": 0,
        "tokens_saved_input": 0,
        "cost_saved_usd": 0.0,
        "prompt_turns_compressed": 0,
    }


def load_stats() -> dict:
    try:
        if STATS_PATH.exists():
            return json.loads(STATS_PATH.read_text(encoding="utf-8"))
    except Exception:
        pass
    return _empty_stats()


def save_stats(stats: dict) -> None:
    try:
        stats["last_updated"] = _now_iso()
        tmp = STATS_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(str(tmp), str(STATS_PATH))
    except Exception:
        pass


def record_file_intercept(file_path: str, original_tokens: int, summary_tokens: int) -> None:
    """Ollama가 파일을 요약해서 차단했을 때 호출."""
    try:
        saved = max(0, original_tokens - summary_tokens)
        cost = saved / 1_000_000 * INPUT_PRICE_PER_M

        stats = load_stats()
        today = _today()

        stats["totals"]["file_read_intercepts"] += 1
        stats["totals"]["tokens_saved_input"] += saved
        stats["totals"]["cost_saved_usd"] = round(
            stats["totals"]["cost_saved_usd"] + cost, 6
        )

        day = stats["daily"].setdefault(today, _empty_daily())
        day["file_read_intercepts"] += 1
        day["tokens_saved_input"] += saved
        day["cost_saved_usd"] = round(day["cost_saved_usd"] + cost, 6)

        stats["events"].append({
            "ts": _now_iso(),
            "type": "file_intercept",
            "file": os.path.basename(file_path),
            "original_tokens": original_tokens,
            "summary_tokens": summary_tokens,
            "saved_tokens": saved,
            "cost_saved_usd": round(cost, 6),
        })
        # 최근 MAX_EVENTS개만 유지
        if len(stats["events"]) > MAX_EVENTS:
            stats["events"] = stats["events"][-MAX_EVENTS:]

        save_stats(stats)
    except Exception:
        pass


def record_prompt_turn() -> None:
    """efficiency-mode로 처리된 프롬프트 턴마다 호출."""
    try:
        stats = load_stats()
        today = _today()

        stats["totals"]["prompt_turns_compressed"] += 1
        day = stats["daily"].setdefault(today, _empty_daily())
        day["prompt_turns_compressed"] += 1

        save_stats(stats)
    except Exception:
        pass


def record_session_end(human_turns: int, est_tokens: int, session_id: str = "") -> None:
    """Stop 훅 실행마다 호출 (세션 스냅샷 갱신)."""
    try:
        stats = load_stats()
        today = _today()

        # 같은 session_id면 덮어쓰기, 없으면 append + sessions_tracked +1
        existing_idx = None
        if session_id:
            for i, ev in enumerate(stats["events"]):
                if ev.get("type") == "session_snapshot" and ev.get("session_id") == session_id:
                    existing_idx = i
                    break

        event = {
            "ts": _now_iso(),
            "type": "session_snapshot",
            "session_id": session_id,
            "human_turns": human_turns,
            "est_tokens": est_tokens,
        }

        if existing_idx is not None:
            stats["events"][existing_idx] = event
        else:
            stats["totals"]["sessions_tracked"] += 1
            stats["daily"].setdefault(today, _empty_daily())
            stats["events"].append(event)
            if len(stats["events"]) > MAX_EVENTS:
                stats["events"] = stats["events"][-MAX_EVENTS:]

        save_stats(stats)
    except Exception:
        pass


# ─────────────────────────────────────────────
# CLI Report
# ─────────────────────────────────────────────

def print_report():
    stats = load_stats()
    t = stats["totals"]
    created = stats.get("created_at", "")[:10]

    print("=" * 50)
    print("  efficiency-mode  Cost Savings Report")
    print("=" * 50)
    print(f"  Tracking since : {created}")
    print(f"  Last updated   : {stats.get('last_updated','')[:19].replace('T',' ')}")
    print()
    print("  [ Ollama File Interception ]")
    print(f"  Files intercepted  : {t['file_read_intercepts']:,}")
    print(f"  Input tokens saved : {t['tokens_saved_input']:,}")
    print(f"  Cost saved (est.)  : ${t['cost_saved_usd']:.4f} USD")
    print()
    print("  [ Session Activity ]")
    print(f"  Prompt turns       : {t['prompt_turns_compressed']:,}")
    print(f"  Sessions tracked   : {t['sessions_tracked']:,}")
    print()

    # 최근 7일
    daily = stats.get("daily", {})
    recent = sorted(daily.keys())[-7:]
    if recent:
        print("  [ Last 7 Days ]")
        print(f"  {'Date':<12} {'Intercepts':>10} {'Tokens Saved':>13} {'Cost Saved':>11}")
        print(f"  {'-'*12} {'-'*10} {'-'*13} {'-'*11}")
        for date in recent:
            d = daily[date]
            print(
                f"  {date:<12} {d['file_read_intercepts']:>10,} "
                f"{d['tokens_saved_input']:>13,} "
                f"${d['cost_saved_usd']:>10.4f}"
            )
        print()

    print(f"  Total estimated savings: ${t['cost_saved_usd']:.4f} USD")
    print("=" * 50)


def print_reset():
    if STATS_PATH.exists():
        STATS_PATH.unlink()
        print("Stats reset.")
    else:
        print("No stats file found.")


if __name__ == "__main__":
    if "--reset" in sys.argv:
        print_reset()
    else:
        print_report()
