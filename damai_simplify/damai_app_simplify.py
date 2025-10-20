import argparse
import sys

from pathlib import Path

from damai_simplify.config import AppTicketConfig, ConfigValidationError


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Damai app ticket grabbing (Appium)")
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="配置文件路径，默认使用 damai_appium/config.jsonc",
    )
    return parser.parse_args()





def main() -> int:
    args = _parse_args()
    try:
        configs = AppTicketConfig.load_all(args.config)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}")
        return 2
    except ConfigValidationError as exc:
        print(f"[ERROR] {exc.message}")
        for item in exc.errors:
            print(f"        - {item}")
        return 2
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] 配置加载失败: {exc}")
        return 2

    # 定时等待至开票前 1s



    # 设备执行抢票


    # 报告输出

    # If scheduled start is specified, wait until the target time before executing.
    if getattr(args, "start_at", None):
        try:
            target_utc = _parse_start_at_text(args.start_at)
            first_server = configs[0].server_url if configs else None
            _wait_until_utc(target_utc, getattr(args, "warmup_sec", 0), first_server)
        except Exception as exc:  # noqa: BLE001
            print(f"[WARN] 定时等待发生异常: {exc}，将立即执行。")

    runs: List[Dict[str, Any]] = []
    total = len(configs)
    print(f"[INFO] 发现 {total} 个待执行会话。")

    overall_success = True
    for index, config in enumerate(configs, start=1):
        session_label = _derive_session_label(config, index)
        logger = _make_session_logger(session_label)
        print(f"[INFO] 开始执行 {session_label}")
        runner = DamaiAppTicketRunner(config=config, logger=logger)
        success = runner.run(max(args.retries, 1))
        report = runner.get_last_report()
        _print_summary(success, report, session_label=session_label)
        if not success:
            overall_success = False
        runs.append({"session": session_label, "success": success, "config": config, "report": report})

    if args.export_report:
        if not runs:
            print("[SUMMARY] No report to export.")
        else:
            export_target = _export_reports(Path(args.export_report), runs)
            print(f"[SUMMARY] 汇总报告已导出: {export_target}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    sys.exit(main())
