RA NEXUS

An AI Agent for Turning Questions into Actions

RA NEXUS is an AI assistant prototype built by RA Tech for the PromptWars × Error Zero 2026 hackathon. It combines a knowledge search system, a safe calculator, and system status tools in a clean web dashboard.

Features

* Knowledge Search — Search a local JSON knowledge base for campus information and laboratory equipment
* Safe Calculator — Evaluate supported mathematical expressions using a restricted arithmetic evaluator
* System Status — Check whether RA NEXUS is online and view its available tools
* Interactive Dashboard — Dark-themed interface with Tools, Knowledge, and Activity views
* Input Validation — Validate user messages using FastAPI and Pydantic
* Local Knowledge Base — Store and retrieve information from a JSON file

Technology Stack

* Python
* FastAPI
* Pydantic
* HTML, CSS, and JavaScript
* JSON
* Git and GitHub

Project Structure

RA-NEXUS/
├── backend/
│   ├── main.py
│   ├── agent.py
│   ├── tools.py
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
├── data/
│   └── knowledge.json
├── README.md
└── .gitignore

Getting Started

Requirements

* Python 3.9 or compatible version
* pip
* Git

1. Clone the repository

git clone https://github.com/Rohibuilds/promptwars-x-error-zero-2026.git
cd promptwars-x-error-zero-2026

2. Create and activate a virtual environment

python3 -m venv .venv
source .venv/bin/activate

3. Install dependencies

pip install -r backend/requirements.txt

4. Start the backend

From the project root, run:

uvicorn backend.main:app --reload

The backend will be available at:

* API health endpoint: http://127.0.0.1:8000/
* Interactive API documentation: http://127.0.0.1:8000/docs

5. Start the frontend

Open a second Terminal window, navigate to the project directory, and run:

python3 -m http.server 5500 --directory frontend

Open the dashboard at:

http://127.0.0.1:5500/

API Usage

Chat endpoint

POST /chat

Example request:

{
  "message": "Where is the electronics laboratory located?"
}

Example calculator request:

{
  "message": "Calculate 25 plus 17"
}

The backend returns a structured response based on the selected tool.

Current Scope

RA NEXUS currently uses rule-based intent routing and local tools. It is a working assistant prototype, not yet a general-purpose large language model agent. Its capabilities are limited to the intents and information implemented in the project.

Security

* User messages are validated for empty input and maximum length
* Calculator expressions are evaluated using a restricted arithmetic evaluator
* Cross-origin requests are restricted to the local development frontend
* Production deployment requires appropriate CORS configuration, secure hosting, and additional security review

Vision

RA NEXUS aims to connect knowledge, intelligent tools, and real-world interfaces to solve practical problems through accessible AI-assisted workflows.

Hackathon

Event: PromptWars × Error Zero 2026
Project: RA NEXUS
Built by: RA Tech

This repository contains the prototype and its supporting source code. Features described as future goals should not be considered implemented unless they are present in the current codebase.