# app/schemas/financial.py
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ScenarioBase(BaseModel):
    name: str
    description: Optional[str] = None
    
class ScenarioCreate(ScenarioBase):
    pass

class ScenarioUpdate(ScenarioBase):
    name: Optional[str] = None
    is_default: Optional[bool] = None
    
class Scenario(ScenarioBase):
    id: int
    created_at: datetime
    updated_at: datetime
    is_default: bool
    
    class Config:
        orm_mode = True
        
class ParameterUpdate(BaseModel):
    start_date: Optional[str] = None
    initial_clients: Optional[int] = None
    initial_developers: Optional[int] = None
    initial_affiliates: Optional[int] = None
    client_growth_rates: Optional[List[float]] = None
    developer_growth_rates: Optional[List[float]] = None
    affiliate_growth_rates: Optional[List[float]] = None
    subscription_price: Optional[float] = None
    affiliate_commission: Optional[float] = None
    free_months: Optional[int] = None
    conversion_rate: Optional[float] = None
    cto_start_month: Optional[int] = None
    ceo_start_month: Optional[int] = None
    ceo_salary: Optional[float] = None
    sales_start_month: Optional[int] = None
    sales_hiring_interval: Optional[int] = None
    max_sales_staff: Optional[int] = None
    jr_dev_start_month: Optional[int] = None
    admin_start_month: Optional[int] = None
    cto_salary: Optional[float] = None
    sales_base_salary: Optional[float] = None
    sales_commission: Optional[float] = None
    jr_dev_salary: Optional[float] = None
    admin_salary: Optional[float] = None
    marketing_percentage: Optional[float] = None
    infrastructure_cost_per_user: Optional[float] = None
    other_expenses_percentage: Optional[float] = None