"""Unit tests for _MossTTS provider in speech/tts/tts_service.py."""

from __future__ import annotations

import pytest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from config.config import config
from speech.tts.tts_service import _MossTTS


@pytest.mark.anyio
async def test_moss_tts_api_mode(tmp_path) -> None:
    # 1. Setup temporary configurations
    config.set("tts.moss_mode", "api")
    config.set("tts.moss_voice", "Junhao")
    config.set("tts.moss_api_url", "http://localhost:18083/api/generate")

    # 2. Mock urllib.request.urlopen
    mock_response = MagicMock()
    mock_response.__enter__.return_value = mock_response
    mock_response.read.return_value = b"mocked audio wav binary data"
    
    with patch("urllib.request.urlopen", return_value=mock_response) as mock_urlopen:
        # Patch cache directory to tmp_path
        with patch("speech.tts.tts_service.TTS_CACHE", tmp_path):
            tts = _MossTTS()
            res = await tts.synthesize("Hello world")
            
            # Assert success and properties
            assert res["success"] is True
            assert "audio_path" in res
            assert res["cached"] is False
            
            # Assert file contents
            audio_file = Path(res["audio_path"])
            assert audio_file.exists()
            assert audio_file.read_bytes() == b"mocked audio wav binary data"
            
            # Verify HTTP request was sent to the correct endpoint
            mock_urlopen.assert_called_once()
            args, kwargs = mock_urlopen.call_args
            req = args[0]
            assert req.full_url == "http://localhost:18083/api/generate"
            assert req.method == "POST"


@pytest.mark.anyio
async def test_moss_tts_cli_mode(tmp_path) -> None:
    # 1. Setup temporary configurations for CLI voice cloning
    config.set("tts.moss_mode", "cli")
    config.set("tts.moss_dir", str(tmp_path / "moss_dir"))
    config.set("tts.moss_ref_audio_path", str(tmp_path / "reference.wav"))
    config.set("tts.moss_prompt_text", "reference prompt text")

    # Make sure MOSS-TTS directory and reference file exist in mock env
    (tmp_path / "moss_dir").mkdir(parents=True, exist_ok=True)
    (tmp_path / "reference.wav").touch()

    # 2. Mock subprocess.run to simulate success and write output file
    def mock_run_cmd(*args, **kwargs):
        # The command specifies out_path, let's locate it and write mock data to it
        cmd_args = args[0]
        out_path_idx = cmd_args.index("--output_path") + 1
        out_path = Path(cmd_args[out_path_idx])
        out_path.write_bytes(b"mocked cli audio wav binary data")
        
        mock_result = MagicMock()
        mock_result.stdout = "Inference completed successfully"
        return mock_result

    with patch("subprocess.run", side_effect=mock_run_cmd) as mock_run:
        with patch("speech.tts.tts_service.TTS_CACHE", tmp_path):
            tts = _MossTTS()
            res = await tts.synthesize("Hello world from CLI")
            
            # Assert success and properties
            assert res["success"] is True
            assert "audio_path" in res
            assert res["cached"] is False
            
            audio_file = Path(res["audio_path"])
            assert audio_file.exists()
            assert audio_file.read_bytes() == b"mocked cli audio wav binary data"
            
            # Verify CLI was run with the correct arguments
            mock_run.assert_called_once()
            call_cmd = mock_run.call_args[0][0]
            assert "infer_onnx.py" in call_cmd[1]
            assert "--text" in call_cmd
            assert "Hello world from CLI" in call_cmd
            assert "--prompt-audio-path" in call_cmd
            assert "--prompt-text" in call_cmd
