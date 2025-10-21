from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from appium import webdriver
from appium.options.common.base import AppiumOptions
from appium.webdriver.common.appiumby import AppiumBy
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait

from .config import AppTicketConfig


Logger = Callable[[str, str, Dict[str, Any]], None]
StopSignal = Callable[[], bool]
DriverFactory = Callable[[str, Dict[str, Any]], Any]


class LogLevel(str, Enum):
    STEP = "step"
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class RunnerPhase(str, Enum):
    INIT = "init"
    CONNECTING = "connecting"
    APPLYING_SETTINGS = "applying_settings"
    SELECTING_CITY = "selecting_city"
    TAPPING_PURCHASE = "tapping_purchase"
    SELECTING_PRICE = "selecting_price"
    SELECTING_QUANTITY = "selecting_quantity"
    CONFIRMING_PURCHASE = "confirming_purchase"
    SELECTING_USERS = "selecting_users"
    SUBMITTING_ORDER = "submitting_order"
    COMPLETED = "completed"
    STOPPED = "stopped"
    FAILED = "failed"


class TicketRunnerError(RuntimeError):
    """Base exception for ticket runner failures."""


class TicketRunnerStopped(TicketRunnerError):
    """Raised when the runner is stopped externally."""


class FailureReason(str, Enum):
    USER_STOP = "user_stop"
    APPIUM_CONNECTION = "appium_connection_failed"
    FLOW_FAILURE = "flow_failure"
    UNEXPECTED = "unexpected_error"
    MAX_RETRIES = "max_retries_reached"


@dataclass
class TicketRunLogEntry:
    timestamp: float
    level: LogLevel
    message: str
    phase: RunnerPhase
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        iso_time = datetime.fromtimestamp(self.timestamp).isoformat(timespec="milliseconds")
        return {
            "timestamp": self.timestamp,
            "timestamp_iso": iso_time,
            "level": self.level.value,
            "message": self.message,
            "phase": self.phase.value,
            "context": self.context,
        }


@dataclass
class TicketRunMetrics:
    start_time: float
    end_time: float
    attempts: int
    success: bool
    final_phase: RunnerPhase
    failure_reason: Optional[str]
    failure_code: Optional[FailureReason]

    def to_dict(self) -> Dict[str, Any]:
        duration = max(self.end_time - self.start_time, 0.0)
        return {
            "start_time": self.start_time,
            "start_time_iso": datetime.fromtimestamp(self.start_time).isoformat(timespec="milliseconds"),
            "end_time": self.end_time,
            "end_time_iso": datetime.fromtimestamp(self.end_time).isoformat(timespec="milliseconds"),
            "duration_seconds": round(duration, 3),
            "attempts": self.attempts,
            "retries": max(self.attempts - 1, 0),
            "success": self.success,
            "final_phase": self.final_phase.value,
            "failure_reason": self.failure_reason,
            "failure_code": self.failure_code.value if self.failure_code else None,
        }


@dataclass
class TicketRunReport:
    metrics: TicketRunMetrics
    logs: List[TicketRunLogEntry]
    phase_history: List[RunnerPhase]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "metrics": self.metrics.to_dict(),
            "phase_history": [phase.value for phase in self.phase_history],
            "logs": [entry.to_dict() for entry in self.logs],
        }

    def dump_json(self, path: Union[str, Path], *, indent: int = 2) -> Path:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as fp:
            json.dump(self.to_dict(), fp, ensure_ascii=False, indent=indent)
        return target


def _default_logger(level: str, message: str, context: Optional[Dict[str, Any]] = None) -> None:
    context = context or {}
    extra = " ".join(f"{key}={value}" for key, value in context.items())
    if extra:
        print(f"[{level.upper()}] {message} | {extra}")
    else:
        print(f"[{level.upper()}] {message}")


@dataclass
class DamaiAppTicketRunner:
    """Encapsulates the Damai Appium ticket grabbing workflow."""

    config: AppTicketConfig
    logger: Logger = _default_logger
    stop_signal: StopSignal = lambda: False
    driver_factory: Optional[DriverFactory] = None
    current_phase: RunnerPhase = field(init=False)
    phase_history: List[RunnerPhase] = field(init=False)
    last_report: Optional[TicketRunReport] = field(init=False, default=None)

    _log_entries: List[TicketRunLogEntry] = field(init=False, default_factory=list)
    _run_start_time: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        if self.logger is None:
            self.logger = _default_logger
        if self.stop_signal is None:
            self.stop_signal = lambda: False
        self._driver = None
        self._wait: Optional[WebDriverWait] = None
        self.current_phase = RunnerPhase.INIT
        self.phase_history = [RunnerPhase.INIT]
        self._log_entries = []
        self._run_start_time = 0.0
        self.last_report = None

    # ------------------------------------------------------------------
    # State helpers
    # ------------------------------------------------------------------
    def _transition_to(self, phase: RunnerPhase) -> None:
        if phase == self.current_phase:
            return
        self.current_phase = phase
        self.phase_history.append(phase)

    def _mark_failure(self) -> None:
        if self.current_phase != RunnerPhase.FAILED:
            self._transition_to(RunnerPhase.FAILED)

    def _mark_stopped(self) -> None:
        if self.current_phase != RunnerPhase.STOPPED:
            self._transition_to(RunnerPhase.STOPPED)

    def _ensure_driver(self):
        if self._driver is None:
            raise TicketRunnerError("Appium driver 尚未初始化")
        return self._driver
