# app/schemas/__init__.py
# Import schemas as needed
from app.schemas.auth import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserInDB,
    User,
    Token,
    TokenData,
    OAuthUserInfo
)

from app.schemas.financial import (
    ScenarioBase,
    ScenarioCreate,
    ScenarioUpdate,
    Scenario,
    ParameterUpdate
)