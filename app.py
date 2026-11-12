
from fastapi import FastAPI

app = FastAPI(
    title="VibeClips AI",
    description="AI video clipping backend"
)

@app.get("/")
def home():
    return {
        "app": "VibeClips AI",
        "status": "running",
        "message": "Welcome to VibeClips AI"
    }

@app.get("/health")
def health():
    return {"status": "healthy"}
  
