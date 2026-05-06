# Project Instructions

This file provides Codex-specific instructions for `Encry_LLM_HealthReport`.

## Overview

This project is a privacy-preserving multimodal health monitoring demo using CKKS homomorphic encryption and LLM-driven inference/report generation.

## Environment

- Always use the project virtual environment.
- If `venv` does not exist and the task requires it, create it with `python -m venv venv`.
- Activate with `source venv/bin/activate` on Linux/macOS.
- Install dependencies with `pip install -r backend/requirements.txt` when needed.

## File Rules

- Put intermediate or one-off test scripts in `temp/`.
- Do not add extra Markdown files beyond `README.md` unless the user explicitly asks.
- Brainstorming specs and implementation plans are allowed under `docs/superpowers/specs/` and `docs/superpowers/plans/` when the user approves the design or asks to write a plan.
- Do not add one-click startup scripts unless the user explicitly asks.

## Port Rules

- Do not use port `8080`.
- Preferred backend ports are `8082`, `8083`, `8084`, and similar alternatives.
- Preferred frontend port is `8001`.
- Check port availability before starting services.
- If the backend port changes, update the frontend `API_BASE` configuration as needed.

## Common Commands

- Create venv:
  - `python -m venv venv`
- Install dependencies:
  - `pip install -r backend/requirements.txt`
- Start backend:
  - `cd backend && uvicorn app:app --host 127.0.0.1 --port 8082`
- Start simplified backend:
  - `cd backend && uvicorn simple_app:app --host 127.0.0.1 --port 8082`
- Start frontend:
  - `cd frontend && python -m http.server 8001`

## Change Rules

- Prefer minimal, direct fixes.
- Do not refactor unrelated code.
- Do not commit automatically.
