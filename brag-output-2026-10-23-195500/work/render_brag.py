import os
import subprocess
import time
from playwright.sync_api import sync_playwright

def render_video():
    base_dir = r"d:\hack\brag-output-2026-10-23-195500"
    work_dir = os.path.join(base_dir, "work")
    frames_dir = os.path.join(work_dir, "frames")
    os.makedirs(frames_dir, exist_ok=True)

    html_file = os.path.join(work_dir, "index.html")
    soundtrack = os.path.join(work_dir, "soundtrack.wav")
    final_mp4 = os.path.join(base_dir, "brag.mp4")
    poster_jpg = os.path.join(base_dir, "brag.jpg")

    fps = 30
    duration = 20.0
    total_frames = int(duration * fps)

    print(f"Step 1: Capturing {total_frames} frames from headless Chromium...", flush=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
        
        file_url = "file:///" + html_file.replace("\\", "/")
        page.goto(file_url, wait_until="networkidle")
        time.sleep(1.0) # Ensure fonts and CSS are settled

        for frame_idx in range(total_frames):
            t = frame_idx / fps
            page.evaluate(f"window.seek({t})")
            frame_path = os.path.join(frames_dir, f"frame_{frame_idx:04d}.png")
            page.screenshot(path=frame_path, type="png")

            if (frame_idx + 1) % 60 == 0 or frame_idx == total_frames - 1:
                pct = int(((frame_idx + 1) / total_frames) * 100)
                print(f"Captured {frame_idx + 1}/{total_frames} frames ({pct}%)...", flush=True)

        browser.close()

    print("Step 2: Encoding video with FFmpeg...", flush=True)
    frames_pattern = os.path.join(frames_dir, "frame_%04d.png")
    raw_mp4 = os.path.join(work_dir, "raw.mp4")

    encode_cmd = [
        "ffmpeg", "-y",
        "-r", str(fps),
        "-i", frames_pattern,
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
    subprocess.run(encode_cmd, check=True)

    print("Step 3: Extracting poster frame (settled hook at t=1.2s)...", flush=True)
    poster_source = os.path.join(frames_dir, f"frame_{int(1.2 * fps):04d}.png")
    subprocess.run([
        "ffmpeg", "-y",
        "-i", poster_source,
        "-q:v", "2",
        poster_jpg
    ], check=True)

    print("Step 4: Baking poster as frame 0 into brag.mp4...", flush=True)
    bake_cmd = [
        "ffmpeg", "-y",
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

    print(f"SUCCESS: Rendered {final_mp4} (20.0s) and {poster_jpg}", flush=True)

if __name__ == "__main__":
    render_video()
