"""Constrained subprocess runner for agent-initiated commands."""

from __future__ import annotations

import asyncio
import os
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from config.config import PROJECT_ROOT
from runtime.logger import get_logger

logger = get_logger("ai-companion.execution.sandbox")

DEFAULT_ALLOWED_BINARIES = {
    "git",
    "pytest",
    "python",
    "python3",
    "npm",
    "npx",
    "pnpm",
    "pnpx",
    "node",
    "echo",
    "ls",
    "dir",
}

DEFAULT_OUTPUT_LIMIT = 12000
DANGEROUS_PATTERNS = {
    "rm -rf /",
    "rm -fr /",
    "del /f /s /q c:\\",
    "format c:",
}


@dataclass(frozen=True)
class SandboxPolicy:
    root: Path = PROJECT_ROOT
    allowed_binaries: frozenset[str] = frozenset(DEFAULT_ALLOWED_BINARIES)
    output_limit: int = DEFAULT_OUTPUT_LIMIT


class SandboxRunner:
    """Run commands inside a fixed project root with timeout and auditing."""

    def __init__(self, policy: SandboxPolicy | None = None) -> None:
        self.policy = policy or SandboxPolicy()

    def _root(self) -> Path:
        return self.policy.root.resolve()

    def _resolve_cwd(self, cwd: str | Path | None = None) -> Path:
        root = self._root()
        resolved = Path(cwd or root).expanduser().resolve()
        if resolved != root and root not in resolved.parents:
            raise ValueError(f"cwd escapes sandbox root: {resolved}")
        if not resolved.exists():
            raise ValueError(f"cwd does not exist: {resolved}")
        return resolved

    @staticmethod
    def _normalize_binary(binary: str) -> str:
        name = Path(binary).name.lower()
        if sys.platform == "win32" and name.endswith(".exe"):
            name = name[:-4]
        return name

    @staticmethod
    def _split(command: str) -> list[str]:
        return shlex.split(command, posix=True)

    @staticmethod
    def _has_dangerous_pattern(command: str, tokens: Iterable[str]) -> str:
        lowered = " ".join(command.lower().split())
        for pattern in DANGEROUS_PATTERNS:
            if pattern in lowered:
                return f"blocked dangerous command pattern: {pattern}"

        token_list = list(tokens)
        for idx, token in enumerate(token_list):
            if token == "cd" and idx + 1 < len(token_list):
                target = token_list[idx + 1]
                if target == ".." or target.startswith("../") or target.startswith("..\\"):
                    return "blocked attempt to cd outside sandbox root"
        return ""

    def inspect(self, command: str) -> dict:
        """Return command safety metadata without executing it."""
        try:
            tokens = self._split(command.strip())
        except ValueError as exc:
            return {"success": False, "error": f"Cannot parse command: {exc}"}

        if not tokens:
            return {"success": False, "error": "Empty command"}

        danger = self._has_dangerous_pattern(command, tokens)
        if danger:
            return {"success": False, "error": danger, "blocked": True}

        binary = self._normalize_binary(tokens[0])
        allowed = binary in self.policy.allowed_binaries
        return {
            "success": True,
            "tokens": tokens,
            "binary": binary,
            "allowed": allowed,
            "requires_approval": not allowed,
        }

    @staticmethod
    def _trim_output(text: str, limit: int) -> tuple[str, bool]:
        if len(text) <= limit:
            return text, False
        suffix = f"\n...[output truncated to {limit} characters]..."
        keep = max(limit - len(suffix), 0)
        return text[:keep] + suffix, True

    async def run(
        self,
        command: str,
        cwd: str | Path | None = None,
        timeout: float = 60.0,
        allow_unlisted: bool = False,
    ) -> dict:
        """Execute a command with shell disabled and bounded output."""
        command = command.strip()
        audit = {
            "command": command,
            "cwd": str(cwd or self._root()),
            "timeout": timeout,
            "allow_unlisted": allow_unlisted,
        }

        try:
            resolved_cwd = self._resolve_cwd(cwd)
            inspection = self.inspect(command)
            if not inspection.get("success"):
                logger.warning("[SANDBOX] blocked command=%r reason=%s", command, inspection.get("error"))
                return {"success": False, "error": inspection.get("error", "Command blocked"), "blocked": True}

            if inspection.get("requires_approval") and not allow_unlisted:
                logger.warning(
                    "[SANDBOX] blocked unlisted binary command=%r binary=%s",
                    command,
                    inspection.get("binary"),
                )
                return {
                    "success": False,
                    "error": f"Binary '{inspection.get('binary')}' is not whitelisted",
                    "requires_approval": True,
                    "blocked": True,
                }

            logger.info("[SANDBOX] running %s", audit)
            env = os.environ.copy()
            proc = await asyncio.create_subprocess_exec(
                *inspection["tokens"],
                cwd=str(resolved_cwd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.communicate()
                logger.warning("[SANDBOX] timeout command=%r timeout=%s", command, timeout)
                return {
                    "success": False,
                    "returncode": -9,
                    "stdout": "",
                    "stderr": "",
                    "error": f"Command timed out after {timeout} seconds",
                    "timeout": True,
                }

            stdout = stdout_b.decode("utf-8", errors="replace")
            stderr = stderr_b.decode("utf-8", errors="replace")
            stdout, stdout_truncated = self._trim_output(stdout, self.policy.output_limit)
            stderr, stderr_truncated = self._trim_output(stderr, self.policy.output_limit)
            success = proc.returncode == 0

            logger.info(
                "[SANDBOX] completed command=%r returncode=%s success=%s",
                command,
                proc.returncode,
                success,
            )
            return {
                "success": success,
                "returncode": proc.returncode,
                "stdout": stdout,
                "stderr": stderr,
                "stdout_truncated": stdout_truncated,
                "stderr_truncated": stderr_truncated,
                "cwd": str(resolved_cwd),
                "binary": inspection.get("binary"),
            }
        except Exception as exc:
            logger.error("[SANDBOX] failed command=%r error=%s", command, exc)
            return {"success": False, "error": str(exc)}


sandbox_runner = SandboxRunner()
