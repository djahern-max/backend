# app/auth/service.py
from typing import Optional, Union
from sqlalchemy.orm import Session
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from datetime import datetime, timedelta
from sqlalchemy import func  # Added for case-insensitive query
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenData, UserCreate, UserInDB, OAuthUserInfo
from app.auth.utils import (
    verify_password, 
    get_password_hash,
    SECRET_KEY,
    ALGORITHM,
    create_access_token, 
    create_refresh_token
)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Decode JWT token and return the current user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Case-insensitive query for username
    user = db.query(User).filter(func.lower(User.username) == func.lower(token_data.username)).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Check if the current user is active."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_user)
) -> User:
    """Check if the current user is a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

def authenticate_user(
    db: Session, 
    username: str, 
    password: str
) -> Optional[User]:
    """Authenticate a user."""
    # Case-insensitive query for username
    user = db.query(User).filter(func.lower(User.username) == func.lower(username)).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user

def create_user(
    db: Session, 
    user_data: UserCreate
) -> User:
    """Create a new user."""
    # Case-insensitive check if the user already exists
    existing_user = db.query(User).filter(
        (func.lower(User.username) == func.lower(user_data.username)) | 
        (func.lower(User.email) == func.lower(user_data.email))
    ).first()
    
    if existing_user:
        if func.lower(existing_user.username) == func.lower(user_data.username):
            raise HTTPException(status_code=400, detail="Username already registered")
        else:
            raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create new user - keep original case for display but search will be case-insensitive
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,  # Keep original case for display purposes
        email=user_data.email,
        hashed_password=hashed_password,
        auth_provider="local"
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

def create_tokens_for_user(user: User) -> dict:
    """Create access and refresh tokens for a user."""
    access_token_expires = timedelta(minutes=30)
    refresh_token_expires = timedelta(days=7)
    
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(
        data={"sub": user.username},
        expires_delta=refresh_token_expires
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

def find_or_create_oauth_user(
    db: Session, 
    user_info: OAuthUserInfo
) -> User:
    """Find or create a user from OAuth information."""
    # Check if user exists with this provider ID
    user = db.query(User).filter(
        User.auth_provider == user_info.provider,
        User.provider_user_id == user_info.provider_user_id
    ).first()
    
    if user:
        return user
        
    # Check if user exists with this email - case insensitive
    user = db.query(User).filter(func.lower(User.email) == func.lower(user_info.email)).first()
    
    if user:
        # Update existing user with OAuth info
        user.auth_provider = user_info.provider
        user.provider_user_id = user_info.provider_user_id
        db.commit()
        db.refresh(user)
        return user
    
    # Create new user
    username = user_info.username or f"{user_info.provider}_{user_info.provider_user_id}"
    # Ensure username is unique - case insensitive
    count = 1
    base_username = username
    while db.query(User).filter(func.lower(User.username) == func.lower(username)).first():
        username = f"{base_username}_{count}"
        count += 1
    
    db_user = User(
        username=username,
        email=user_info.email,
        auth_provider=user_info.provider,
        provider_user_id=user_info.provider_user_id
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return db_user

# Function to create a demo user for demonstrations
def create_demo_user(db: Session):
    """Create a demo user with simple credentials for demonstration purposes."""
    # Check if demo user already exists - case insensitive
    existing_user = db.query(User).filter(func.lower(User.username) == "abc").first()
    if existing_user:
        print("Demo user already exists")
        return existing_user
    
    # Create the demo user
    demo_user = User(
        username="abc",
        email="demo@example.com",
        hashed_password=get_password_hash("123"),
        is_active=True,
        auth_provider="local"
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    print("Demo user created successfully")
    return demo_user