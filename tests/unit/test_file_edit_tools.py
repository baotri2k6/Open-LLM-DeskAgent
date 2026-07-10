from __future__ import annotations

from tools.file_edit import create_file, str_replace_file
from tools.view_file import view_file


def test_str_replace_file_edits_one_block_in_large_file(tmp_path):
    path = tmp_path / "large.py"
    lines = [f"line_{idx}" for idx in range(250)]
    lines.append("target = 'old'")
    lines.extend(f"line_{idx}" for idx in range(250, 500))
    path.write_text("\n".join(lines), encoding="utf-8")

    result = str_replace_file(str(path), "target = 'old'", "target = 'new'")

    assert result["success"] is True
    updated = path.read_text(encoding="utf-8").splitlines()
    assert updated[250] == "target = 'new'"
    assert updated[:250] == lines[:250]
    assert updated[251:] == lines[251:]


def test_str_replace_file_fails_when_old_str_is_ambiguous(tmp_path):
    path = tmp_path / "ambiguous.py"
    original = "value = 1\nkeep = True\nvalue = 1\n"
    path.write_text(original, encoding="utf-8")

    result = str_replace_file(str(path), "value = 1", "value = 2")

    assert result["success"] is False
    assert result["occurrences"] == 2
    assert path.read_text(encoding="utf-8") == original


def test_create_file_fails_if_file_exists(tmp_path):
    path = tmp_path / "exists.txt"
    path.write_text("original", encoding="utf-8")

    result = create_file(str(path), "new")

    assert result["success"] is False
    assert path.read_text(encoding="utf-8") == "original"


def test_view_file_returns_line_numbers(tmp_path):
    path = tmp_path / "sample.txt"
    path.write_text("alpha\nbeta\ngamma\n", encoding="utf-8")

    result = view_file(str(path), start_line=2, end_line=3)

    assert result["success"] is True
    assert "    2 | beta" in result["text"]
    assert "    3 | gamma" in result["text"]
