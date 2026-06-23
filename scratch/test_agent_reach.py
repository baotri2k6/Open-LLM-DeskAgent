import sys
from pathlib import Path

# Force UTF-8 output for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Add python-services directory to path
services_path = str(Path(__file__).parent.parent / "python-services")
if services_path not in sys.path:
    sys.path.append(services_path)

from tools.mxh_tools import (
    search_twitter,
    read_reddit_post,
    get_youtube_transcript,
    search_bilibili,
    read_webpage_jina
)

def run_test(name, func, *args, **kwargs):
    print(f"\n=================== TESTING: {name} ===================")
    try:
        res = func(*args, **kwargs)
        print("Success status:", res.get("success"))
        if res.get("success"):
            print("Output keys:", list(res.keys()))
            # Print a snippet of results
            for k, v in res.items():
                if k != "success":
                    v_str = str(v)
                    print(f"  {k}: {v_str[:300]}..." if len(v_str) > 300 else f"  {k}: {v_str}")
        else:
            print("Error message:", res.get("error"))
    except Exception as e:
        print("Test failed with exception:", e)

if __name__ == "__main__":
    # 1. Test Jina Reader (active by default, no API/keys needed)
    run_test("read_webpage_jina", read_webpage_jina, "https://example.com")
    
    # 2. Test Reddit RSS reader fallback (active by default)
    run_test("read_reddit_post", read_reddit_post, "python", limit=3)
    
    # 3. Test Bilibili Web API fallback (active by default)
    run_test("search_bilibili", search_bilibili, "live2d", limit=3)
    
    # 4. Test YouTube transcript downloader (requires yt-dlp, may fallback or succeed if subs available)
    # Using a popular video that definitely has English/auto subtitles
    run_test("get_youtube_transcript", get_youtube_transcript, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # 5. Test Twitter CLI / OpenCLI (usually needs login/cookie, check how it handles failure)
    run_test("search_twitter", search_twitter, "python", limit=3)
