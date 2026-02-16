import os
import jwt
from typing import List, Optional
from pydantic import BaseModel
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your-production-secret-change-me")
JWT_ALGORITHM = "HS256"

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
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication error: {str(e)}")

def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)) -> UserClaims:
    """
    FastAPI dependency to get the current authenticated user.
    """
    token = credentials.credentials
    return verify_token(token)
