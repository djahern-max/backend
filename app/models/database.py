# app/models/database.py
from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Boolean, ARRAY
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()

class ForecastScenario(Base):
    """Model for storing different forecast scenarios"""
    __tablename__ = "forecast_scenarios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    description = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_default = Column(Boolean, default=False)
    
    # Relationship with Parameters table
    parameters = relationship("Parameters", back_populates="scenario", uselist=False, cascade="all, delete-orphan")
    
    # Relationship with MonthlyData table
    monthly_data = relationship("MonthlyData", back_populates="scenario", cascade="all, delete-orphan")
    
    # Relationship with YearlySummary table
    yearly_summaries = relationship("YearlySummary", back_populates="scenario", cascade="all, delete-orphan")


class Parameters(Base):
    """Model for storing forecast parameters for each scenario"""
    __tablename__ = "parameters"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("forecast_scenarios.id", ondelete="CASCADE"))
    
    # Initial values
    start_date = Column(String)
    initial_clients = Column(Integer)
    initial_developers = Column(Integer)
    initial_affiliates = Column(Integer)
    
    # Monthly growth rates - store as JSON arrays
    client_growth_rates = Column(JSON)  # [0.10, 0.12, 0.15, 0.12, 0.10]
    developer_growth_rates = Column(JSON)  # [0.05, 0.07, 0.10, 0.08, 0.06]
    affiliate_growth_rates = Column(JSON)  # [0.08, 0.10, 0.12, 0.10, 0.08]
    
    # Pricing
    subscription_price = Column(Float)
    affiliate_commission = Column(Float)
    free_months = Column(Integer)
    conversion_rate = Column(Float)
    
    # Staff planning
    cto_start_month = Column(Integer)
    ceo_start_month = Column(Integer)
    sales_start_month = Column(Integer)
    sales_hiring_interval = Column(Integer)
    max_sales_staff = Column(Integer)
    jr_dev_start_month = Column(Integer)
    admin_start_month = Column(Integer)
    
    # Staffing costs
    cto_salary = Column(Float)
    ceo_salary = Column(Float)
    sales_base_salary = Column(Float)
    sales_commission = Column(Float)
    jr_dev_salary = Column(Float)
    admin_salary = Column(Float)
    
    # Other expenses
    marketing_percentage = Column(Float)
    infrastructure_cost_per_user = Column(Float)
    other_expenses_percentage = Column(Float)
    
    # Relationship
    scenario = relationship("ForecastScenario", back_populates="parameters")


class MonthlyData(Base):
    """Model for storing monthly forecast data for each scenario"""
    __tablename__ = "monthly_data"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("forecast_scenarios.id", ondelete="CASCADE"))
    
    year = Column(Integer)
    month = Column(Integer)
    month_number = Column(Integer)
    date = Column(String)
    
    # Financial data
    income = Column(Float)
    expenses = Column(Float)
    ebitda = Column(Float)
    
    # Users data
    client_count = Column(Integer)
    new_clients = Column(Integer)
    paying_clients = Column(Integer)
    developer_count = Column(Integer)
    affiliate_count = Column(Integer)
    
    # Staff data
    sales_staff = Column(Integer)
    jr_devs = Column(Integer)
    admin_staff = Column(Integer)
    cto_count = Column(Integer)
    ceo_count = Column(Integer)
    total_staff = Column(Integer)
    
    # Detailed costs
    cto_cost = Column(Float)
    ceo_cost = Column(Float)
    sales_cost = Column(Float)
    jr_dev_cost = Column(Float)
    admin_cost = Column(Float)
    infrastructure_cost = Column(Float)
    marketing_cost = Column(Float)
    affiliate_cost = Column(Float)
    other_expenses = Column(Float)
    
    # Relationship
    scenario = relationship("ForecastScenario", back_populates="monthly_data")


class YearlySummary(Base):
    """Model for storing yearly summary data for each scenario"""
    __tablename__ = "yearly_summaries"

    id = Column(Integer, primary_key=True, index=True)
    scenario_id = Column(Integer, ForeignKey("forecast_scenarios.id", ondelete="CASCADE"))
    
    year = Column(Integer)
    income = Column(Float)
    expenses = Column(Float)
    ebitda = Column(Float)
    
    # End of year data
    client_count = Column(Integer)
    paying_clients = Column(Integer)
    developer_count = Column(Integer)
    affiliate_count = Column(Integer)
    sales_staff = Column(Integer)
    jr_devs = Column(Integer)
    admin_staff = Column(Integer)
    cto_count = Column(Integer)
    ceo_count = Column(Integer)
    total_staff = Column(Integer)
    
    # Relationship
    scenario = relationship("ForecastScenario", back_populates="yearly_summaries")