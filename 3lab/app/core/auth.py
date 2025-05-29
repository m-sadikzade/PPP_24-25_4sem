from fastapi import HTTPException, Request, status, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError

SECRET_KEY = "secret-key"          # в бою храните в .env
ALGO       = "HS256"

# Схема безопасности для Swagger-UI
bearer_scheme = HTTPBearer(auto_error=False)


def verify_jwt(token: str):
    """Возвращает payload или None."""
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGO])
    except JWTError:
        return None


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
):
    """
    Универсальная зависимость: достаёт токен из заголовка
    или из параметра credentials (если Swagger добавил его).
    """
    token = None
    if credentials is not None:
        token = credentials.credentials
    else:
        auth = request.headers.get("Authorization")
        if auth and auth.startswith("Bearer "):
            token = auth.split()[1]

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid or missing token")

    user = verify_jwt(token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail="Invalid token")
    return user
