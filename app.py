
import os
import re
import uuid
import subprocess
from pathlib import Path

import imageio_ffmpeg

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

app = FastAPI(title="VibeClips AI")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nitin2705rao-cyber.github.io"
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Storage
UPLOAD_DIR = Path("/tmp/vibeclips_uploads")
CLIPS_DIR = Path("/tmp/vibeclips_clips")

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
CLIPS_DIR.mkdir(parents=True, exist_ok=True)

MAX_SIZE = 250 * 1024 * 1024

ALLOWED_FORMATS = {".mp4", ".mov", ".webm", ".mkv"}


@app.get("/")
def home():
    return {
        "app": "VibeClips AI",
        "status": "running"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# Upload video
@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):

    extension = Path(file.filename or "").suffix.lower()

    if extension not in ALLOWED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail="Unsupported video format"
        )

    upload_id = str(uuid.uuid4())
    destination = UPLOAD_DIR / f"{upload_id}{extension}"

    size = 0

    try:
        with destination.open("wb") as output:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                size += len(chunk)

                if size > MAX_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="Video must be under 250 MB"
                    )

                output.write(chunk)

    except Exception:
        destination.unlink(missing_ok=True)
        raise

    finally:
        await file.close()

    return {
        "success": True,
        "upload_id": upload_id,
        "filename": file.filename,
        "size_bytes": size,
        "message": "Video uploaded successfully"
    }


# Generate video clips
@app.post("/api/create-clips")
def create_clips(
    upload_id: str = Form(...),
    clip_seconds: int = Form(30),
    max_clips: int = Form(5)
):

    try:
        upload_id = str(uuid.UUID(upload_id))
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid upload ID"
        )

    if not 5 <= clip_seconds <= 120:
        raise HTTPException(
            status_code=400,
            detail="Clip duration must be 5 to 120 seconds"
        )

    if not 1 <= max_clips <= 10:
        raise HTTPException(
            status_code=400,
            detail="Maximum clips must be between 1 and 10"
        )

    source_files = list(UPLOAD_DIR.glob(f"{upload_id}.*"))

    if not source_files:
        raise HTTPException(
            status_code=404,
            detail="Uploaded video not found. Please upload again."
        )

    source = source_files[0]

    try:
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="FFmpeg is not available"
        )

    output_dir = CLIPS_DIR / upload_id
    output_dir.mkdir(parents=True, exist_ok=True)

    clips = []

    for index in range(max_clips):

        start_time = index * clip_seconds
        clip_name = f"clip_{index + 1:02d}.mp4"
        clip_path = output_dir / clip_name

        command = [
            ffmpeg,
            "-y",
            "-ss", str(start_time),
            "-i", str(source),
            "-t", str(clip_seconds),
            "-map", "0:v:0",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "23",
            "-c:a", "aac",
            "-movflags", "+faststart",
            str(clip_path)
        ]

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=300
            )
        except subprocess.TimeoutExpired:
            clip_path.unlink(missing_ok=True)
            break

        if result.returncode != 0 or not clip_path.exists():
            clip_path.unlink(missing_ok=True)
            break

        if clip_path.stat().st_size < 1024:
            clip_path.unlink(missing_ok=True)
            break

        clips.append({
            "filename": clip_name,
            "download_url": f"/api/download/{upload_id}/{clip_name}"
        })

    if not clips:
        raise HTTPException(
            status_code=422,
            detail="No clips could be generated from this video"
        )

    return {
        "success": True,
        "upload_id": upload_id,
        "clips_created": len(clips),
        "clips": clips,
        "message": "Video clips generated successfully"
    }


# Download generated clip
@app.get("/api/download/{upload_id}/{clip_name}")
def download_clip(upload_id: str, clip_name: str):

    try:
        upload_id = str(uuid.UUID(upload_id))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid upload ID")

    if not re.fullmatch(r"clip_\d{2}\.mp4", clip_name):
        raise HTTPException(status_code=400, detail="Invalid filename")

    clip_path = CLIPS_DIR / upload_id / clip_name

    if not clip_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Clip not found"
        )

    return FileResponse(
        path=clip_path,
        filename=clip_name,
        media_type="video/mp4"
    )
