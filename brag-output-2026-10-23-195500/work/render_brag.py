import os
import subprocess
import time
import shutil
from playwright.sync_api import sync_playwright

def find_ffmpeg():
    # 1. Check winget install path
    winget_path = r"C:\Users\thesh\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-9.0.2-full_build\bin\ffmpeg.exe"
    if os.path.exists(winget_path):
        return winget_path
    
    # 2. Check PATH
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg
        
    raise FileNotFoundError("FFmpeg executable could not be found.")

def render_video():
    base_dir = r"d:\hack\brag-output-2026-10-23-195500"
    work_dir = os.path.join(base_dir, "work")

    html_file = os.path.join(work_dir, "index.html")
    soundtrack = os.path.join(work_dir, "soundtrack.wav")
    raw_mp4 = os.path.join(work_dir, "raw.mp4")
    final_mp4 = os.path.join(base_dir, "brag.mp4")
    poster_jpg = os.path.join(base_dir, "brag.jpg")

    ffmpeg_bin = find_ffmpeg()
    print(f"Using FFmpeg at: {ffmpeg_bin}", flush=True)

    fps = 30
    duration = 52.0
    total_frames = int(duration * fps)

    print(f"Step 1: Streaming {total_frames} frames ({duration}s @ {fps}fps) from Playwright to FFmpeg stdin...", flush=True)

    # Spawn FFmpeg with image2pipe to avoid saving intermediate frames to disk
    encode_cmd = [
        ffmpeg_bin, "-y",
        "-f", "image2pipe",
        "-vcodec", "mjpeg",
        "-r", str(fps),
        "-i", "-",
        "-i", soundtrack,
        "-c:v", "libx264",
        "-preset", "medium",
        "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        raw_mp4
    ]

    ffmpeg_log_path = os.path.join(work_dir, "ffmpeg.log")
    ffmpeg_log = open(ffmpeg_log_path, "w", encoding="utf-8", errors="replace")
    ffmpeg_proc = subprocess.Popen(encode_cmd, stdin=subprocess.PIPE, stderr=ffmpeg_log)

    poster_frame_idx = int(1.5 * fps)
    poster_captured = False

    start_time = time.time()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        
        file_url = "file:///" + html_file.replace("\\", "/")
        page.goto(file_url, wait_until="networkidle")
        time.sleep(1.0) # Ensure fonts and CSS are settled

        for frame_idx in range(total_frames):
            t = frame_idx / fps
            page.evaluate(f"window.seek({t})")
            
            # Capture as JPEG byte buffer
            frame_bytes = page.screenshot(type="jpeg", quality=92)
            ffmpeg_proc.stdin.write(frame_bytes)

            # Capture high-quality poster frame at t=1.5s
            if frame_idx == poster_frame_idx:
                page.screenshot(path=poster_jpg, type="jpeg", quality=95)
                poster_captured = True

            if (frame_idx + 1) % 60 == 0 or frame_idx == total_frames - 1:
                elapsed = time.time() - start_time
                pct = int(((frame_idx + 1) / total_frames) * 100)
                fps_render = (frame_idx + 1) / elapsed
                print(f"Rendered {frame_idx + 1}/{total_frames} frames ({pct}%) at {fps_render:.1f} fps...", flush=True)

        browser.close()

    print("Step 2: Finalizing raw video encode...", flush=True)
    ffmpeg_proc.stdin.close()
    ffmpeg_proc.wait()
    ffmpeg_log.close()

    if ffmpeg_proc.returncode != 0:
        with open(ffmpeg_log_path, "r", encoding="utf-8", errors="replace") as f:
            print("FFmpeg log:\n", f.read(), flush=True)
        raise RuntimeError(f"FFmpeg encoding failed with exit code {ffmpeg_proc.returncode}")

    if not poster_captured or not os.path.exists(poster_jpg):
        print("Fallback capturing poster...", flush=True)
        subprocess.run([ffmpeg_bin, "-y", "-ss", "1.5", "-i", raw_mp4, "-frames:v", "1", "-q:v", "2", poster_jpg], check=True)

    print("Step 3: Baking poster as frame 0 into brag.mp4...", flush=True)
    bake_cmd = [
        ffmpeg_bin, "-y",
        "-i", raw_mp4,
        "-i", poster_jpg,
        "-filter_complex", "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]",
        "-map", "[v]",
        "-map", "0:a?",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "slow",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        final_mp4
    ]
    subprocess.run(bake_cmd, check=True)

    final_size_mb = os.path.getsize(final_mp4) / (1024 * 1024)
    print(f"SUCCESS: Rendered {final_mp4} ({duration}s, {final_size_mb:.2f} MB) and poster {poster_jpg}", flush=True)

if __name__ == "__main__":
    render_video()
