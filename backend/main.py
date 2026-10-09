from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .agent import run_agent

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(
    title="RA NEXUS",
    description="RA Tech Autonomous AI Assistant",
    version="0.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def validate_message(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Message cannot be empty")
        return value


@app.get("/health")
def health():
    return {
        "name": "RA NEXUS",
        "version": "0.1.0",
        "status": "online"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    return run_agent(request.message)


app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")