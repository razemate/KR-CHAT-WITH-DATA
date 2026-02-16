import os
import jwt
from typing import List, Optional
from pydantic import BaseModel
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

ENVIRONMENT = os.getenv("ENVIRONMENT", "production").lower()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALGORITHM = "HS256"

if not JWT_SECRET:
    if ENVIRONMENT == "development":
        JWT_SECRET = "dev-secret-only"
    else:
        raise RuntimeError("JWT_SECRET environment variable is required in production")


class UserClaims(BaseModel):
    id: str
    email: str
    groups: List[str] = ["user"]


security = HTTPBearer()


def verify_token(token: str) -> UserClaims:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return UserClaims(**payload)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")
    except Exception:
        raise HTTPException(status_code=401, detail="Authentication error")


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> UserClaims:
    token = credentials.credentials
    return verify_token(token)
