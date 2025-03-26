# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import Any
import os
from jose import jwt, JWTError
import httpx

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserCreate, User as UserSchema, Token, OAuthUserInfo
from app.auth.service import (
    authenticate_user, 
    create_user, 
    create_tokens_for_user,
    find_or_create_oauth_user,
    get_current_active_user
)
from app.auth.utils import SECRET_KEY, ALGORITHM

# Environment variables for OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.getenv("GITHUB_CLIENT_SECRET", "")
LINKEDIN_CLIENT_ID = os.getenv("LINKEDIN_CLIENT_ID", "")
LINKEDIN_CLIENT_SECRET = os.getenv("LINKEDIN_CLIENT_SECRET", "")
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

router = APIRouter(prefix="/api/auth", tags=["auth"])

@router.post("/register", response_model=UserSchema)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """Register a new user."""
    return create_user(db, user_data)

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
) -> Any:
    """Authenticate and login a user."""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return create_tokens_for_user(user)

@router.post("/refresh-token", response_model=Token)
async def refresh_token(
    request: Request,
    db: Session = Depends(get_db)
) -> Any:
    """Refresh an access token using a refresh token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Get the refresh token from the request
    authorization = request.headers.get("Authorization")
    if not authorization:
        raise credentials_exception
    
    scheme, token = authorization.split()
    if scheme.lower() != "bearer":
        raise credentials_exception
    
    try:
        # Decode the token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        is_refresh = payload.get("refresh", False)
        
        if not username or not is_refresh:
            raise credentials_exception
            
        # Get the user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            raise credentials_exception
        
        # Create new tokens
        return create_tokens_for_user(user)
        
    except JWTError:
        raise credentials_exception

@router.get("/me", response_model=UserSchema)
async def get_user_me(
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get information about the current logged-in user."""
    return current_user

# OAuth routes
@router.get("/login/google")
async def login_google() -> dict:
    """Get Google OAuth login URL."""
    redirect_uri = f"{API_BASE_URL}/api/auth/callback/google"
    return {
        "url": f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={GOOGLE_CLIENT_ID}&redirect_uri={redirect_uri}&scope=email profile&access_type=offline&prompt=consent"
    }

@router.get("/callback/google")
async def google_callback(
    code: str,
    db: Session = Depends(get_db)
) -> dict:
    """Handle the callback from Google OAuth."""
    # Exchange code for token
    token_url = "https://oauth2.googleapis.com/token"
    redirect_uri = f"{API_BASE_URL}/api/auth/callback/google"
    
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        # Get user info
        user_info_url = "https://www.googleapis.com/oauth2/v3/userinfo"
        user_response = await client.get(
            user_info_url,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        user_response.raise_for_status()
        google_user = user_response.json()
        
        # Create or find user
        oauth_user = OAuthUserInfo(
            email=google_user["email"],
            username=google_user.get("name", "").replace(" ", "_").lower(),
            provider="google",
            provider_user_id=google_user["sub"]
        )
        
        user = find_or_create_oauth_user(db, oauth_user)
        
        # Create tokens
        tokens = create_tokens_for_user(user)
        
        # Return tokens and frontend redirect
        frontend_redirect = f"{FRONTEND_URL}/auth-callback?token={tokens['access_token']}"
        return {"redirect": frontend_redirect}

@router.get("/login/github")
async def login_github() -> dict:
    """Get GitHub OAuth login URL."""
    redirect_uri = f"{API_BASE_URL}/api/auth/callback/github"
    return {
        "url": f"https://github.com/login/oauth/authorize?client_id={GITHUB_CLIENT_ID}&redirect_uri={redirect_uri}&scope=user:email"
    }

@router.get("/callback/github")
async def github_callback(
    code: str,
    db: Session = Depends(get_db)
) -> dict:
    """Handle the callback from GitHub OAuth."""
    # Exchange code for token
    token_url = "https://github.com/login/oauth/access_token"
    redirect_uri = f"{API_BASE_URL}/api/auth/callback/github"
    
    token_data = {
        "code": code,
        "client_id": GITHUB_CLIENT_ID,
        "client_secret": GITHUB_CLIENT_SECRET,
        "redirect_uri": redirect_uri
    }
    
    async with httpx.AsyncClient() as client:
        headers = {"Accept": "application/json"}
        token_response = await client.post(token_url, data=token_data, headers=headers)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        # Get user info
        user_info_url = "https://api.github.com/user"
        user_response = await client.get(
            user_info_url,
            headers={"Authorization": f"token {tokens['access_token']}"}
        )
        user_response.raise_for_status()
        github_user = user_response.json()
        
        # Get email (GitHub doesn't return email by default)
        emails_url = "https://api.github.com/user/emails"
        emails_response = await client.get(
            emails_url,
            headers={"Authorization": f"token {tokens['access_token']}"}
        )
        emails_response.raise_for_status()
        emails = emails_response.json()
        
        # Find primary email
        primary_email = next((email["email"] for email in emails if email["primary"]), emails[0]["email"])
        
        # Create or find user
        oauth_user = OAuthUserInfo(
            email=primary_email,
            username=github_user.get("login"),
            provider="github",
            provider_user_id=str(github_user["id"])
        )
        
        user = find_or_create_oauth_user(db, oauth_user)
        
        # Create tokens
        tokens = create_tokens_for_user(user)
        
        # Return tokens and frontend redirect
        frontend_redirect = f"{FRONTEND_URL}/auth-callback?token={tokens['access_token']}"
        return {"redirect": frontend_redirect}

@router.get("/login/linkedin")
async def login_linkedin() -> dict:
    """Get LinkedIn OAuth login URL."""
    redirect_uri = f"{API_BASE_URL}/api/auth/callback/linkedin"
    return {
        "url": f"https://www.linkedin.com/oauth/v2/authorization?response_type=code&client_id={LINKEDIN_CLIENT_ID}&redirect_uri={redirect_uri}&scope=r_liteprofile%20r_emailaddress"
    }

@router.get("/callback/linkedin")
async def linkedin_callback(
    code: str,
    db: Session = Depends(get_db)
) -> dict:
    """Handle the callback from LinkedIn OAuth."""
    # Exchange code for token
    token_url = "https://www.linkedin.com/oauth/v2/accessToken"
    redirect_uri = f"{API_BASE_URL}/api/auth/callback/linkedin"
    
    token_data = {
        "code": code,
        "client_id": LINKEDIN_CLIENT_ID,
        "client_secret": LINKEDIN_CLIENT_SECRET,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code"
    }
    
    async with httpx.AsyncClient() as client:
        token_response = await client.post(token_url, data=token_data)
        token_response.raise_for_status()
        tokens = token_response.json()
        
        # Get user profile
        profile_url = "https://api.linkedin.com/v2/me"
        profile_response = await client.get(
            profile_url,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        profile_response.raise_for_status()
        linkedin_user = profile_response.json()
        
        # Get email address
        email_url = "https://api.linkedin.com/v2/emailAddress?q=members&projection=(elements*(handle~))"
        email_response = await client.get(
            email_url,
            headers={"Authorization": f"Bearer {tokens['access_token']}"}
        )
        email_response.raise_for_status()
        email_data = email_response.json()
        email = email_data["elements"][0]["handle~"]["emailAddress"]
        
        # Create username from first and last name
        first_name = linkedin_user.get("localizedFirstName", "")
        last_name = linkedin_user.get("localizedLastName", "")
        username = f"{first_name}_{last_name}".lower().replace(" ", "_")
        
        # Create or find user
        oauth_user = OAuthUserInfo(
            email=email,
            username=username,
            provider="linkedin",
            provider_user_id=linkedin_user["id"]
        )
        
        user = find_or_create_oauth_user(db, oauth_user)
        
        # Create tokens
        tokens = create_tokens_for_user(user)
        
        # Return tokens and frontend redirect
        frontend_redirect = f"{FRONTEND_URL}/auth-callback?token={tokens['access_token']}"
        return {"redirect": frontend_redirect}