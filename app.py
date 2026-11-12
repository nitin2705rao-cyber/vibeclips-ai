
import os
import uuid
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="VibeClips AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://nitin2705rao-cyber.github.io"
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

UPLOAD_DIR = Path("/tmp/vibeclips_uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.get("/")
def home():
    return {
        "app": "VibeClips AI",
        "status": "running"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.post("/api/upload")
async def upload_video(file: UploadFile = File(...)):
    allowed = {
        ".mp4", ".mov", ".webm", ".mkv"
    }

    extension = Path(file.filename or "").suffix.lower()

    if extension not in allowed:
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

                if size > 250 * 1024 * 1024:
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
    
