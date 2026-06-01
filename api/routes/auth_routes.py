"""
Auth API Routes - Chrome profile selection for LinkedIn authentication.
"""
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.driver_manager import DriverManager
from config import LINKEDIN_EMAIL

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


class ProfileSelectRequest(BaseModel):
    data_dir: str
    profile_dir: str
    profile_name: Optional[str] = None


@router.get("/profiles")
async def list_profiles():
    """Detect all Chrome profiles installed on this machine."""
    data_dir = DriverManager.get_data_dir()
    profiles = DriverManager.detect_profiles()
    active = DriverManager.get_active_profile_config()

    return {
        "data_dir": data_dir,
        "profiles": profiles,
        "active_profile_dir": active["prof_dir"] if active else None,
    }


@router.get("/status")
async def auth_status():
    """Return current authentication method."""
    active = DriverManager.get_active_profile_config()
    if active:
        return {
            "method": "browser_profile",
            "profile_name": active["name"],
            "profile_dir": active["prof_dir"],
            "data_dir": active["data_dir"],
        }
    has_credentials = bool(LINKEDIN_EMAIL)
    return {
        "method": "credentials" if has_credentials else "none",
        "has_credentials": has_credentials,
        "email": LINKEDIN_EMAIL if has_credentials else None,
    }


@router.post("/profile")
async def select_profile(request: ProfileSelectRequest):
    """Save a Chrome profile to use for LinkedIn (skips credential login)."""
    import os
    profile_path = os.path.join(request.data_dir, request.profile_dir)
    if not os.path.isdir(profile_path):
        raise HTTPException(status_code=400, detail=f"Profile path not found: {profile_path}")

    DriverManager.save_profile_choice(
        profile_dir=request.profile_dir,
        profile_name=request.profile_name,
        data_dir=request.data_dir,
    )
    name = request.profile_name or request.profile_dir
    return {"success": True, "message": f"Profile '{name}' selected — Chrome will use this profile for all scraping jobs"}


@router.delete("/profile")
async def clear_profile():
    """Clear saved profile — falls back to credential login."""
    DriverManager.clear_profile_choice()
    return {"success": True, "message": "Profile cleared — will use credentials from .env"}
