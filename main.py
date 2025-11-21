from fastapi import FastAPI  # Импортируем FastAPI для создания веб-приложения
from fastapi.responses import HTMLResponse  # Чтобы возвращать HTML как ответ
import os  # Для работы с переменными окружения
from fastapi import Request, HTTPException  # Request для получения данных запроса, HTTPException для ошибок
from fastapi.responses import RedirectResponse  # Для перенаправления пользователя на другой URL
from urllib.parse import urlencode  # Чтобы формировать корректные GET-параметры в URL
import httpx  # Асинхронные HTTP-запросы (будем запрашивать токены и данные профиля)
from jose import jwt  # Работа с JWT-токенами (можно декодировать токены Google)
from dotenv import load_dotenv  # Чтобы загрузить переменные окружения из .env
from pathlib import Path  # Работа с путями файлов

app = FastAPI()  # Создаем экземпляр FastAPI приложения

# Загрузка .env файла из корня проекта
env_path = Path(__file__).resolve().parent.parent.parent / ".env"  
load_dotenv(dotenv_path=env_path)

# Получение данных Google OAuth из переменных окружения
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")

# Проверка, что все необходимые переменные заданы
if not all([GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI]):
    raise RuntimeError("Missing required Google OAuth environment variables")

# Константы для Google OAuth
GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"  # URL для авторизации пользователя
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"  # URL для обмена кода на токен
GOOGLE_USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"  # URL для получения данных профиля

# Главная страница
@app.get("/", response_class=HTMLResponse)
async def home():
    # Возвращаем простую HTML страницу с ссылкой на авторизацию через Google
    return """
    <h2>Welcome to FastAPI Google OAuth2 Login</h2>
    <a href="/login">Login with Google</a>
    """

# Маршрут для начала логина через Google
@app.get("/login")
def login():
    # Параметры запроса для Google OAuth
    query_params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",  # Запрашиваем код авторизации
        "scope": "openid email profile",  # Доступ к имени, email и profile
        "access_type": "offline",  # Получение refresh_token для долгого доступа
        "prompt": "consent",  # Пользователь будет видеть форму согласия каждый раз
    }
    # Формируем URL с GET-параметрами
    url = f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(query_params)}"
    # Перенаправляем пользователя на Google для авторизации
    return RedirectResponse(url)

# Callback URL, куда Google перенаправит после авторизации
@app.get("/auth/callback")
async def auth_callback(request: Request):
    # Получаем код авторизации из параметров запроса
    code = request.query_params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not found")

    # Данные для обмена кода на access token
    data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    # Асинхронный HTTP запрос для получения токена
    async with httpx.AsyncClient() as client:
        token_response = await client.post(GOOGLE_TOKEN_ENDPOINT, data=data)
        token_data = token_response.json()
        access_token = token_data.get("access_token")  # Берем access_token

        if not access_token:
            raise HTTPException(status_code=400, detail="Failed to retrieve access token")

        # Используем токен для запроса информации о пользователе
        headers = {"Authorization": f"Bearer {access_token}"}
        userinfo_response = await client.get(GOOGLE_USERINFO_ENDPOINT, headers=headers)
        userinfo = userinfo_response.json()

        # Перенаправляем пользователя на страницу профиля, передавая данные в query params
        return RedirectResponse(
            f"/profile?name={userinfo['name']}&email={userinfo['email']}&picture={userinfo['picture']}"
        )

# Страница профиля пользователя
@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    # Получаем данные пользователя из query params
    user_info = request.query_params
    name = user_info.get("name")
    email = user_info.get("email")
    picture = user_info.get("picture")

    # Возвращаем HTML страницу с приветствием, фото и email
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
