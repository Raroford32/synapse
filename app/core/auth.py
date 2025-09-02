"""Authentication dependencies"""
from typing import Optional
from fastapi import Depends, HTTPException, Header

from app.core.config import settings


async def require_api_key(authorization: Optional[str] = Header(None)) -> None:
    """Require Bearer API key for protected endpoints.

    Accepts header in the form: Authorization: Bearer <API_KEY>
    """
    if settings.ENVIRONMENT == "development" and settings.API_KEY.startswith("default-"):
        # In development, allow default key without strict checking
        return

    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    try:
        scheme, token = authorization.split(" ", 1)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid Authorization header format")

    if scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authorization scheme must be Bearer")

    if token != settings.API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return

