# app/auth.py
from fastapi import APIRouter, Request
from urllib.parse import urlencode
import os
import requests

router = APIRouter()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = os.getenv("REDIRECT_URI")
SCOPES = "https://www.googleapis.com/auth/calendar"

@router.get("/authorize")
def authorize():
    query = urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
        "access_type": "offline",
        "prompt": "consent"
    })
    return {"url": f"https://accounts.google.com/o/oauth2/v2/auth?{query}"}
