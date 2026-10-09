RA NEXUS

An AI Agent for Turning Questions into Actions

RA NEXUS is an AI assistant prototype built by RA Tech for the PromptWars × Error Zero hackathon

Features

* Knowledge search using a local JSON knowledge base
* Safe calculator for supported mathematical expressions
* System status and available tools
* Dark themed dashboard with Tools Knowledge and Activity views
* FastAPI backend with input validation

Technology Stack

* Python
* FastAPI and Pydantic
* HTML CSS and JavaScript
* JSON

Setup

Requirements Python 3.9 or compatible version and pip

Create a virtual environment and activate it

python3 -m venv .venv
source .venv/bin/activate

Install dependencies

pip install -r backend/requirements.txt

Start the backend

uvicorn backend.main:app --reload

In a second Terminal start the frontend

python3 -m http.server 5500 --directory frontend

Open the website at http://127.0.0.1:5500/

API health endpoint http://127.0.0.1:8000/

Interactive API documentation http://127.0.0.1:8000/docs

API

POST /chat

Example request

{
  "message": "What equipment is available in the electronics laboratory?"
}

Current Scope

This prototype uses rule based routing and local tools and is not yet a general purpose language model assistant

Security

* Messages are validated for length and empty input
* Calculator expressions use a restricted arithmetic evaluator
* Cross origin requests are restricted to the local development frontend
* Review authentication and deployment security before exposing the application publicly

Vision

RA NEXUS aims to connect knowledge tools and real world interfaces to solve practical problems

Built by RA Tech