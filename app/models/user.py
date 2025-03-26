# app/models/user.py
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Table
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.database import Base
from typing import List, Optional
import uuid

# Association table for many-to-many relationship between users and scenarios
user_scenarios = Table(
    "user_scenarios",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("scenario_id", Integer, ForeignKey("forecast_scenarios.id", ondelete="CASCADE"), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # OAuth related fields
    auth_provider = Column(String, nullable=True)  # 'google', 'github', 'linkedin', or 'local'
    provider_user_id = Column(String, nullable=True)
    
    # User's scenarios (many-to-many relationship)
    scenarios = relationship(
        "ForecastScenario", 
        secondary=user_scenarios, 
        backref="users",
        lazy="joined"  # This will load scenarios eagerly with the user
    )
    
    def get_default_scenario(self):
        """Get the user's default scenario or the first scenario if no default exists."""
        for scenario in self.scenarios:
            if scenario.is_default:
                return scenario
        return self.scenarios[0] if self.scenarios else None
    
    def has_access_to_scenario(self, scenario_id: int) -> bool:
        """Check if user has access to a specific scenario."""
        return any(s.id == scenario_id for s in self.scenarios)