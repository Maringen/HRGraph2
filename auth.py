from datetime import datetime, timedelta
from typing import Optional
import jwt
from fastapi import HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import hashlib
import secrets
from config import OPENAI_API_KEY, ANTHROPIC_API_KEY

security = HTTPBearer(auto_error=False)


class AuthManager:
    def __init__(self):
        self.api_key = os.getenv("HR_API_KEY")
        if not self.api_key:
            self.api_key = self._generate_default_key()
            print(f"Generated default API key: {self.api_key}")
            print("Set HR_API_KEY environment variable to override")

    def _generate_default_key(self) -> str:
        return secrets.token_urlsafe(32)

    def verify_api_key(
        self, credentials: Optional[HTTPAuthorizationCredentials] = None
    ):
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if credentials.credentials != self.api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return True

    def create_session_token(self, user_context: dict = None) -> str:
        payload = {
            "sub": "hr_user",
            "exp": datetime.utcnow() + timedelta(hours=24),
            "iat": datetime.utcnow(),
            "user_context": user_context or {},
        }
        return jwt.encode(payload, self.api_key, algorithm="HS256")

    def verify_session_token(self, token: str) -> dict:
        try:
            payload = jwt.decode(token, self.api_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
            )


auth_manager = AuthManager()


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = security,
):
    auth_manager.verify_api_key(credentials)
    return {"authenticated": True, "api_key_valid": True}


def require_auth(endpoint):
    async def wrapper(*args, **kwargs):
        if not hasattr(endpoint, "__wrapped"):
            endpoint.__wrapped = True

        original_signature = getattr(endpoint, "__signature__", None)

        async def protected_endpoint(*args, **kwargs):
            try:
                return await endpoint(*args, **kwargs)
            except HTTPException:
                raise

        return protected_endpoint

    return wrapper
