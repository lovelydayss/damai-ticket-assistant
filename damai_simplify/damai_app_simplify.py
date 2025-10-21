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

# 解析 python 参数
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Damai app ticket grabbing (Appium)")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="配置文件路径，默认使用 damai_simplify/config.jsonc",
    )
    return parser.parse_args()


# 构造标签
def _console_logger(level: str, message: str, context: Optional[Dict[str, object]] = None) -> None:
    if context is None:
        context = {}
    ctx_repr = " ".join(f"{k}={v}" for k, v in context.items())
    if ctx_repr:
        print(f"[{level.upper()}] {message} | {ctx_repr}")
    else:
        print(f"[{level.upper()}] {message}")


def _make_session_logger(session_label: str):
    def _logger(level: str, message: str, context: Optional[Dict[str, object]] = None) -> None:
        merged: Dict[str, Any] = {"session": session_label}
        if context:
            merged.update(context)
        _console_logger(level, message, merged)

    return _logger


def _derive_session_label(config: AppTicketConfig, index: int) -> str:
    device_caps = config.device_caps or {}
    parts: List[str] = []
    device_name = device_caps.get("deviceName")
    udid = device_caps.get("udid")
    if device_name:
        parts.append(str(device_name))
    if udid and udid not in parts:
        parts.append(str(udid))
    if not parts:
        parts.append(config.server_url)
    descriptor = "/".join(parts)
    return f"device-{index}:{descriptor}"


# 导出报告
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


def main() -> int:
    # 配置文件读取
    args = _parse_args()
    try:
        config = AppTicketConfig.load(args.config)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] 配置加载失败: {exc}")
        return 2

    # 设备执行抢票
    try:
        # 解析标签
        session_label = _derive_session_label(config, 1)
        logger = _make_session_logger(session_label)
        print(f"[INFO] 开始执行 {session_label}")

        # 主流程
        # 对于抢票来说，重试没有意义
        runner = DamaiAppTicketRunner(config=config, logger=logger)
        success = runner.run()
        report = runner.get_last_report()

        print(f"[INFO] 执行结束 {session_label}")

    except Exception as exc:
        print(f"[ERROR] 抢票期间发生异常: {exc}。")
        return 2

    # 报告输出
    if config.need_log:
        export_target = (_export_report(Path(args.export_report),
                           {"session": session_label, "success": success, "config": config, "report": report}))
        print(f"[SUMMARY] 汇总报告已导出: {export_target}")

    # 返回值
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())