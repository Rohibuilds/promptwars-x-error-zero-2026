from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .agent import run_agent


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
    message: str


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