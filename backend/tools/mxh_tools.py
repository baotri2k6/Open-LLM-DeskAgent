"""MXH tools — Twitter, Reddit, YouTube, Bilibili, and Jina Reader using agent-reach or direct APIs."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
import urllib.parse
import re
from pathlib import Path


def search_twitter(query: str, limit: int = 5) -> dict:
    """Tìm kiếm thảo luận trên Twitter/X bằng twitter-cli hoặc opencli."""
    try:
        # Thử bằng twitter-cli đầu tiên
        proc = subprocess.run(
            ["twitter", "search", query, "-n", str(limit)],
            capture_output=True,
            text=True,
            shell=True,
            timeout=30
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return {"success": True, "results": proc.stdout.strip()}
            
        # Thử fallback qua opencli
        proc_open = subprocess.run(
            ["opencli", "twitter", "search", query, "-n", str(limit), "-f", "yaml"],
            capture_output=True,
            text=True,
            shell=True,
            timeout=30
        )
        if proc_open.returncode == 0 and proc_open.stdout.strip():
            return {"success": True, "results": proc_open.stdout.strip()}
            
        return {
            "success": False,
            "error": "Twitter CLI chưa được cấu hình hoặc chưa đăng nhập. Bạn có thể cài đặt bằng lệnh `pipx install twitter-cli` hoặc cài đặt OpenCLI extension."
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def read_reddit_post(subreddit: str, limit: int = 5) -> dict:
    """Đọc các bài viết mới/hot trên Reddit bằng cách gọi API JSON công khai hoặc rdt-cli."""
    try:
        url = f"https://www.reddit.com/r/{subreddit}/hot.json?limit={limit}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            posts = []
            for item in data.get("data", {}).get("children", []):
                post_data = item.get("data", {})
                posts.append({
                    "title": post_data.get("title"),
                    "author": post_data.get("author"),
                    "url": post_data.get("url"),
                    "selftext": post_data.get("selftext", "")[:400]
                })
            return {"success": True, "posts": posts}
    except Exception as exc:
        # Fallback thử rdt cli
        try:
            proc = subprocess.run(
                ["rdt", "search", subreddit, "--limit", str(limit)],
                capture_output=True,
                text=True,
                shell=True,
                timeout=30
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return {"success": True, "results": proc.stdout.strip()}
        except Exception:
            pass
            
        error_msg = f"Không thể lấy dữ liệu Reddit: {str(exc)}."
        if "403" in str(exc):
            error_msg += " Reddit yêu cầu đăng nhập và chặn các yêu cầu ẩn danh. Bạn cần cài đặt OpenCLI extension hoặc cài đặt rdt-cli (chạy `pip install git+https://github.com/public-clis/rdt-cli.git`) và chạy `rdt login` để thiết lập session cookie."
        return {"success": False, "error": error_msg}


def get_youtube_transcript(video_url: str) -> dict:
    """Tải transcript/phụ đề của video YouTube bằng yt-dlp."""
    try:
        # Trích xuất video ID
        video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11})", video_url)
        if not video_id_match:
            return {"success": False, "error": "URL YouTube không hợp lệ."}
        video_id = video_id_match.group(1)
        
        # Thử tải phụ đề bằng yt-dlp
        output_tmpl = f"/tmp/{video_id}"
        proc = subprocess.run(
            ["yt-dlp", "--write-sub", "--write-auto-sub", "--skip-download", "-o", output_tmpl, video_url],
            capture_output=True,
            text=True,
            shell=True,
            timeout=45
        )
        
        # Tìm file phụ đề được tạo ra trong /tmp
        tmp_dir = Path("/tmp")
        if not tmp_dir.exists():
            tmp_dir = Path(os.environ.get("TEMP", "."))
            
        sub_files = list(tmp_dir.glob(f"{video_id}.*"))
        if sub_files:
            sub_path = sub_files[0]
            text = sub_path.read_text(encoding="utf-8", errors="replace")
            # Cleanup
            sub_path.unlink()
            
            # Làm sạch phụ đề (remove WebVTT timestamps)
            clean_text = re.sub(r"\d{2}:\d{2}:\d{2}\.\d{3}.*?\n", "", text)
            clean_text = re.sub(r"<.*?>", "", clean_text)
            lines = [line.strip() for line in clean_text.split("\n") if line.strip() and "WEBVTT" not in line]
            unique_lines = []
            for line in lines:
                if not unique_lines or unique_lines[-1] != line:
                    unique_lines.append(line)
            
            return {"success": True, "text": " ".join(unique_lines)[:8000]}
            
        return {
            "success": False, 
            "error": "Không tìm thấy phụ đề cho video này. Có thể video không có phụ đề tiếng Anh/Việt tự động."
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def search_bilibili(query: str, limit: int = 5) -> dict:
    """Tìm kiếm video Bilibili bằng bili-cli hoặc trực tiếp Bilibili Web API."""
    try:
        # Thử bằng Bilibili Web API trực tiếp (Zero-dependency search API fallback)
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.bilibili.com/x/web-interface/search/all/v2?keyword={encoded_query}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                "Referer": "https://www.bilibili.com"
            }
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == 0:
                results = []
                video_data = data.get("data", {}).get("result", [])
                # Tìm mảng video
                for r in video_data:
                    if r.get("result_type") == "video":
                        for v in r.get("data", [])[:limit]:
                            results.append({
                                "title": re.sub(r"<.*?>", "", v.get("title")),
                                "author": v.get("author"),
                                "arcurl": v.get("arcurl"),
                                "description": v.get("description")
                            })
                return {"success": True, "videos": results}
    except Exception as exc:
        pass
        
    # Fallback thử bili search CLI
    try:
        proc = subprocess.run(
            ["bili", "search", query, "--type", "video", "-n", str(limit)],
            capture_output=True,
            text=True,
            shell=True,
            timeout=30
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return {"success": True, "results": proc.stdout.strip()}
    except Exception:
        pass
        
    return {"success": False, "error": "Không thể kết nối đến Bilibili API hoặc bili-cli chưa được cài đặt."}


def read_webpage_jina(url: str) -> dict:
    """Đọc nội dung bất kỳ trang web nào bằng Jina Reader API (Zero-dependency & Free)."""
    try:
        jina_url = f"https://r.jina.ai/{url}"
        req = urllib.request.Request(
            jina_url,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            content = resp.read().decode("utf-8")
            return {"success": True, "content": content[:8000], "truncated": len(content) > 8000}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
