#!/bin/bash
# Render Web Service entry point
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port $PORT --log-level warning
