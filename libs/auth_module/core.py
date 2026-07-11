import httpx
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer(auto_error=False)

class GitHubAuthenticator:
    """
    A universal GitHub OAuth and JWT authentication module.
    It provides an APIRouter for the login and callback flows,
    and a dependency `get_current_user` for securing endpoints.
    """
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        jwt_secret: str,
        backend_callback_url: str,
        frontend_callback_url: str,
        jwt_algorithm: str = "HS256",
        jwt_expires_days: int = 7,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.jwt_secret = jwt_secret
        self.backend_callback_url = backend_callback_url
        self.frontend_callback_url = frontend_callback_url
        self.jwt_algorithm = jwt_algorithm
        self.jwt_expires_days = jwt_expires_days
        
        self.router = APIRouter()
        self._setup_routes()

    def _setup_routes(self):
        @self.router.get("/login")
        async def login():
            if not self.client_id:
                raise HTTPException(status_code=500, detail="OAuth client not configured")
            url = f"https://github.com/login/oauth/authorize?client_id={self.client_id}&redirect_uri={self.backend_callback_url}&scope=read:user"
            return RedirectResponse(url)

        @self.router.get("/callback")
        async def callback(code: str):
            token_url = "https://github.com/login/oauth/access_token"
            headers = {"Accept": "application/json"}
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code
            }
            async with httpx.AsyncClient() as http_client:
                token_resp = await http_client.post(token_url, json=data, headers=headers)
                token_data = token_resp.json()
                
                access_token = token_data.get("access_token")
                if not access_token:
                    raise HTTPException(status_code=400, detail="Failed to authenticate")
                    
                user_resp = await http_client.get("https://api.github.com/user", headers={"Authorization": f"Bearer {access_token}"})
                user_data = user_resp.json()
                
            expire = datetime.now(timezone.utc) + timedelta(days=self.jwt_expires_days)
            jwt_payload = {
                "sub": user_data.get("login"),
                "avatar_url": user_data.get("avatar_url"),
                "name": user_data.get("name"),
                "exp": expire
            }
            encoded_jwt = jwt.encode(jwt_payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            
            separator = "&" if "?" in self.frontend_callback_url else "?"
            return RedirectResponse(f"{self.frontend_callback_url}{separator}token={encoded_jwt}")

        @self.router.get("/me")
        async def get_me(user: dict = Depends(self.get_current_user)):
            return user

    async def get_current_user(self, credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
        """FastAPI dependency to retrieve and validate the current user from the JWT token."""
        if not credentials:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing authorization header")
        try:
            payload = jwt.decode(credentials.credentials, self.jwt_secret, algorithms=[self.jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
