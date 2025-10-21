import argparse
import json
import time
import subprocess
from datetime import datetime, timezone
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import Request, urlopen
from urllib.error import URLError

from damai_simplify import (
    AppTicketConfig,
    ConfigValidationError,
    DamaiAppTicketRunner,
    FailureReason,
    LogLevel,
)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Damai app ticket grabbing (Appium)")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="配置文件路径，默认使用 damai_simplify/config.jsonc",
    )
    return parser.parse_args()


def _export_reports(target: Path, runs: List[Dict[str, Any]]) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc)
    export_payload = {
        "generated_at": now_utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "overall_success": all(item["success"] for item in runs),
        "runs": [
            {
                "session": item["session"],
                "success": item["success"],
                "config": {
                    "server_url": item["config"].server_url,
                    "users": item["config"].users,
                    "keyword": item["config"].keyword,
                    "city": item["config"].city,
                    "date": item["config"].date,
                    "price": item["config"].price,
                    "price_index": item["config"].price_index,
                    "device_caps": item["config"].device_caps,
                },
                "report": item["report"].to_dict() if item["report"] else None,
            }
            for item in runs
        ],
    }
    target.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


def _export_report(target: Path, run: Dict[str, Any]) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc)
    export_payload = {
        "generated_at": now_utc.isoformat(timespec="seconds").replace("+00:00", "Z"),
        "overall_success": run["success"],
        "run":
            {
                "session": run["session"],
                "success": run["success"],
                "config": run["config"],
                "report": run["report"].to_dict() if run["report"] else None,
            }

    }
    target.write_text(json.dumps(export_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return target


# 解析时间
def _local_tz():
    """Return the current local timezone object."""
    return datetime.now().astimezone().tzinfo


def _parse_start_at_text(text: str) -> datetime:
    """Parse --start-at into an aware UTC datetime.

    Accepts:
      - ISO8601 like '2025-10-01T20:00:00+08:00' or '2025-10-01T12:00:00Z'
      - 'YYYY-MM-DD HH:MM:SS' (treated as local timezone)
    """
    raw = text.strip()
    # Normalize 'Z' suffix to +00:00 for fromisoformat
    norm = raw.replace("Z", "+00:00")
    dt: Optional[datetime] = None
    try:
        dt = datetime.fromisoformat(norm)
    except Exception:
        # Try to replace space with 'T'
        try:
            dt = datetime.fromisoformat(norm.replace(" ", "T"))
        except Exception:
            dt = None
    if dt is None:
        raise ValueError(f"无法解析开抢时间: {text}")

    if dt.tzinfo is None:
        # Assume local timezone when timezone info missing
        dt = dt.replace(tzinfo=_local_tz())
    return dt.astimezone(timezone.utc)


# 定时等待 & 预热检查
def _check_appium_status(server_url: str, timeout: float = 3.0) -> bool:
    """Check Appium /status endpoint quickly."""
    base = server_url.rstrip("/")
    status_url = f"{base}/status"
    try:
        req = Request(status_url)
        with urlopen(req, timeout=timeout) as resp:
            return resp.status == 200
    except URLError:
        return False
    except Exception:
        return False


def _adb_ready(timeout: float = 5.0) -> bool:
    """Check if any adb device is in 'device' state (best-effort)."""
    try:
        proc = subprocess.run(
            ["adb", "devices", "-l"],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            return False
        lines = (proc.stdout or "").strip().splitlines()
        # Skip header line, look for any 'device' (but not 'unauthorized', 'offline')
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 2 and parts[1].lower() == "device":
                return True
        return False
    except Exception:
        return False


def _wait_until_utc(start_at_time: str, warmup_sec: int = 0, server_url: Optional[str] = None) -> None:
    """Wait until target UTC time with optional warmup checks."""
    target_utc = _parse_start_at_text(start_at_time)
    now_utc = datetime.now(timezone.utc)
    remain = (target_utc - now_utc).total_seconds() - 1.0

    if remain <= 0:
        raise RuntimeError("[error] 开抢时间已过")

    warmup = max(0, int(warmup_sec or 0))
    if 0 < warmup < remain:
        sleep_sec = remain - warmup
        print(f"[INFO] 距离开抢还有 {remain:.2f}s，先等待 {sleep_sec:.2f}s 后进入预热检查。")
        time.sleep(sleep_sec)

    # Warmup window (best-effort health checks)
    if warmup > 0:
        if server_url:
            # 预热，构造驱动并检查相关状态

            ok = _check_appium_status(server_url)
            status = "OK" if ok else "FAIL"
            print(f"[INFO] Appium /status 预热检查: {status} ({server_url})")
        adb_ok = _adb_ready()
        print(f"[INFO] adb 设备状态: {'OK' if adb_ok else 'FAIL'}")

    # Final precise wait to the target moment
    while True:
        now_utc = datetime.now(timezone.utc)
        remain = (target_utc - now_utc).total_seconds() - 1.0
        if remain <= 0:
            break
        if remain > 1.0:
            # Sleep most of the remaining time, keep 1s for fine-grained loop
            time.sleep(remain - 1.0)

    print("[INFO] 到点，开始执行抢票流程。")


def main() -> int:
    # 配置文件读取
    args = _parse_args()
    try:
        config = AppTicketConfig.load(args.config)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] 配置加载失败: {exc}")
        return 2

    # 定时等待
    # 期间会在预热时完成 driver 配置
    # 提前 [1s, 2s) 进入正式抢票流程
    try:
        _wait_until_utc(config.start_at_time, config.warmup_sec, config.server_url)
    except Exception as exc:
        print(f"[WARN] 定时等待发生异常: {exc}")
        return 2

    # 设备执行抢票
    try:
        session_label = _derive_session_label(config, 0)
        logger = _make_session_logger(session_label)
        print(f"[INFO] 开始执行 {session_label}")
        runner = DamaiAppTicketRunner(config=config, logger=logger)
        success = runner.run(max(args.retries, 1))
        report = runner.get_last_report()
        _print_summary(success, report, session_label=session_label)
        run = {"session": session_label, "success": success, "config": config, "report": report}
    except Exception as exc:
        print(f"[ERROR] 抢票期间发生异常: {exc}。")
        return 2

    # 报告输出
    if config.need_log:
        export_target = _export_report(Path(args.export_report), run)
        print(f"[SUMMARY] 汇总报告已导出: {export_target}")

    # 返回值
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())