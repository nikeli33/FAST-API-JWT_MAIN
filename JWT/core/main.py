from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import os
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from urllib.parse import urlencode
import httpx
from jose import jwt
from dotenv import load_dotenv
from pathlib import Path

app = FastAPI()

env_path = Path(__file__).resolve().parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
    raise RuntimeError("Missing required Google OAuth environment variables")

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <h2>Welcome to FastAPI Google OAuth2 Login</h2>
    <a href="/login">Login with Google</a>
    """

@app.get("/login")
def login():
    query_params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(query_params)}"
    return RedirectResponse(url)

@app.get("/auth/callback")
async def auth_callback(request: Request):
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_response = await client.post(GOOGLE_TOKEN_ENDPOINT, data=data)
        token_data = token_response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to retrieve access token")

        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = await client.get(GOOGLE_USERINFO_ENDPOINT, headers=headers)
        userinfo = userinfo_response.json()

        return RedirectResponse(
            f"/profile?name={userinfo['name']}&email={userinfo['email']}&picture={userinfo['picture']}"
        )

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    user_info = request.query_params
    name = user_info.get("name")
    email = user_info.get("email")
    picture = user_info.get("picture")

    return f"""
    <html>
        <head><title>User Profile</title></head>
        <body style='text-align:center; font-family:sans-serif;'>
            <h1>Welcome, {name}!</h1>
            <img src="{picture}" alt="Profile Picture" width="120"/><br>
            <p>Email: {email}</p>
        </body>
    </html>
    """
