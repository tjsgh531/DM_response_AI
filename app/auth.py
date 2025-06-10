# app/auth.py
from fastapi import APIRouter, Request
from urllib.parse import urlencode
import os
import requests
from datetime import datetime, timedelta

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

@router.get("/oauth2callback")
def oauth2callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        return {"error": "Missing code parameter"}

    token_url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    response = requests.post(token_url, data=data)
    if response.status_code != 200:
        return {"error": "Failed to get token", "details": response.text}

    token_info = response.json()

    # 👉 토큰을 session 등에 저장하거나 DB에 넣어야 하지만, 여기선 단순 테스트니까
    with open("access_token.txt", "w") as f:
        f.write(token_info["access_token"])

    return {"token": token_info}

def create_calendar_event(access_token: str):
    url = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }

    start_time = datetime.utcnow() + timedelta(hours=1)
    end_time = start_time + timedelta(hours=1)

    event = {
        "summary": "고객 예약",
        "description": "Instagram DM을 통해 예약된 일정입니다.",
        "start": {"dateTime": start_time.isoformat() + "Z"},
        "end": {"dateTime": end_time.isoformat() + "Z"},
    }

    response = requests.post(url, headers=headers, json=event)
    print("📅 캘린더 응답:", response.status_code, response.text)
    return response.status_code, response.json()

@router.get("/reservation_test")
def reservation_test():
    try:
        with open("access_token.txt", "r") as f:
            access_token = f.read().strip()
    except FileNotFoundError:
        return {"error": "access_token.txt not found. 먼저 /oauth2callback 을 통해 토큰을 받아오세요."}

    status, result = create_calendar_event(access_token)
    return {"status": status, "result": result}
