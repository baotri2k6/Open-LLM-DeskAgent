"""Registry of background services and their health status."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Any


HealthCheck = Callable[[], bool | dict[str, Any]]


@dataclass
class ServiceStatus:
    name: str
    status: str = "unknown"
    last_checked: float = 0.0
    error: str = ""
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "last_checked": self.last_checked,
            "error": self.error,
            "details": self.details,
        }


class ServiceRegistry:
    """Tracks service health for the settings status panel and /health."""

    def __init__(self) -> None:
        self._checks: dict[str, HealthCheck] = {}
        self._statuses: dict[str, ServiceStatus] = {}

    def register(self, name: str, check: HealthCheck | None = None, details: dict[str, Any] | None = None) -> None:
        if check:
            self._checks[name] = check
        self._statuses.setdefault(name, ServiceStatus(name=name, details=details or {}))

    def update(self, name: str, status: str, error: str = "", details: dict[str, Any] | None = None) -> None:
        current = self._statuses.setdefault(name, ServiceStatus(name=name))
        current.status = status
        current.error = error
        current.last_checked = time.time()
        if details is not None:
            current.details = details

    def check(self, name: str) -> ServiceStatus:
        current = self._statuses.setdefault(name, ServiceStatus(name=name))
        check = self._checks.get(name)
        if not check:
            current.last_checked = time.time()
            return current

        try:
            result = check()
            if isinstance(result, dict):
                ok = bool(result.get("ok", result.get("success", False)))
                details = {k: v for k, v in result.items() if k not in {"ok", "success", "error"}}
                self.update(name, "online" if ok else "offline", str(result.get("error", "")), details)
            else:
                self.update(name, "online" if result else "offline")
        except Exception as exc:
            self.update(name, "error", str(exc))
        return self._statuses[name]

    def check_all(self) -> dict[str, dict[str, Any]]:
        for name in list(self._checks):
            self.check(name)
        return self.snapshot()

    def snapshot(self) -> dict[str, dict[str, Any]]:
        return {name: status.to_dict() for name, status in sorted(self._statuses.items())}


service_registry = ServiceRegistry()
