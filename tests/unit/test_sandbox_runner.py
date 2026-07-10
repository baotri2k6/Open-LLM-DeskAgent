from __future__ import annotations

import pytest

from execution.sandbox.sandbox_runner import SandboxPolicy, SandboxRunner


@pytest.mark.anyio
async def test_sandbox_blocks_dangerous_rm(tmp_path):
    runner = SandboxRunner(SandboxPolicy(root=tmp_path))

    result = await runner.run("rm -rf /", cwd=tmp_path)

    assert result["success"] is False
    assert result["blocked"] is True
    assert "dangerous" in result["error"]


@pytest.mark.anyio
async def test_sandbox_runs_allowed_command(tmp_path):
    runner = SandboxRunner(SandboxPolicy(root=tmp_path))

    result = await runner.run("python -c \"print('ok')\"", cwd=tmp_path)

    assert result["success"] is True
    assert result["stdout"].strip() == "ok"


@pytest.mark.anyio
async def test_sandbox_timeout_kills_command(tmp_path):
    runner = SandboxRunner(SandboxPolicy(root=tmp_path))

    result = await runner.run("python -c \"import time; time.sleep(2)\"", cwd=tmp_path, timeout=0.1)

    assert result["success"] is False
    assert result["timeout"] is True


@pytest.mark.anyio
async def test_sandbox_blocks_cwd_escape(tmp_path):
    runner = SandboxRunner(SandboxPolicy(root=tmp_path))

    result = await runner.run("python -c \"print('no')\"", cwd=tmp_path.parent)

    assert result["success"] is False
    assert "escapes sandbox root" in result["error"]
