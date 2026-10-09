from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, field_validator

from .agent import run_agent


app = FastAPI(
    title="RA NEXUS",
    description="RA Tech Autonomous AI Assistant",
    version="0.1.0"
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
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


@app.get("/")
def home():
    return {
        "name": "RA NEXUS",
        "version": "0.1.0",
        "status": "online"
    }


@app.post("/chat")
def chat(request: ChatRequest):
    return run_agent(request.message)