@echo off
echo Starting Backend Server...
cd backend
uvicorn app:app --host 127.0.0.1 --port 8080
