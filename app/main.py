# app/main.py
import os
import json
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pydantic import BaseModel, Field
from enum import Enum
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import database connection
from app.database import get_db, Base, engine, SessionLocal

# Import database models
from app.models.database import ForecastScenario, Parameters, MonthlyData, YearlySummary

# Initialize FastAPI app
app = FastAPI(title="RYZE.ai Financial Forecast API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure the database tables are created
Base.metadata.create_all(bind=engine)

# Default business model parameters
DEFAULT_PARAMETERS = {
    # Initial values
    "start_date": "2025-04-01",  # April 1, 2025
    "initial_clients": 100,
    "initial_developers": 50,
    "initial_affiliates": 20,
    
    # Monthly growth rates
    "client_growth_rates": [0.10, 0.12, 0.15, 0.12, 0.10],  # Monthly growth by year
    "developer_growth_rates": [0.05, 0.07, 0.10, 0.08, 0.06],
    "affiliate_growth_rates": [0.08, 0.10, 0.12, 0.10, 0.08],
    
    # Pricing
    "subscription_price": 25,  # $25/month subscription
    "affiliate_commission": 5,  # $5/month affiliate commission
    "free_months": 1,  # First month is free
    "conversion_rate": 0.75,  # Conversion rate after free period
    
    # Staff planning
    "cto_start_month": 6,
    "ceo_start_month": 6,
    "sales_start_month": 3,  # First sales person after 3 months
    "sales_hiring_interval": 3,  # New sales person every 3 months
    "max_sales_staff": 10,  # Cap at 10 sales people
    "jr_dev_start_month": 6,  # Junior developer after 6 months
    "admin_start_month": 6,  # Admin person after 6 months
    
    # Staffing costs
    "cto_salary": 12500,  # $150K/year = $12,500/month
    "sales_base_salary": 10000,  # $120K/year = $10,000/month
    "sales_commission": 0.05,  # 5% of sales generated
    "jr_dev_salary": 8333,  # $100K/year = $8,333/month
    "admin_salary": 8333,  # $100K/year = $8,333/month
    
    # Other expenses
    "marketing_percentage": 0.15,  # 15% of revenue for marketing
    "infrastructure_cost_per_user": 1.5,  # $1.50 per user for infrastructure
    "other_expenses_percentage": 0.10,  # 10% of revenue for other expenses
}

# Helper function to get the growth rate based on month
def get_growth_rate(month: int, rates: List[float]) -> float:
    year = min(month // 12, len(rates) - 1)
    return rates[year]

# Calculate financial projections based on parameters
def calculate_projections(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    start_date = datetime.strptime(params["start_date"], "%Y-%m-%d")
    months = 72

    # Initialize values
    clients = params["initial_clients"]
    paying_clients = 0
    developers = params["initial_developers"] 
    affiliates = params["initial_affiliates"]

    # Track clients by cohort for calculating paying clients
    client_cohorts = []  # List of (month_joined, count) tuples
    
    # Track sales staff hiring
    sales_staff_count = 0
    sales_staff_hire_months = []
    
    # Init other staff counts
    cto_count = 0
    jr_dev_count = 0
    admin_count = 0

    monthly_data = []

    for i in range(months):
        current_date = start_date + relativedelta(months=i)
        current_month = current_date.month
        current_year = current_date.year
        year_index = min(i // 12, len(params["client_growth_rates"]) - 1)
        
        # --- Staff Hiring Logic ---
        # CTO hiring
        if i >= params["cto_start_month"] and cto_count == 0:
            cto_count = 1
        
        # CEO hiring logic (add after CTO hiring logic)
        ceo_count = 0
        if i >= params["ceo_start_month"] and ceo_count == 0:
            ceo_count = 1
            
        # Sales staff hiring
        if i >= params["sales_start_month"] and i % params["sales_hiring_interval"] == params["sales_start_month"] % params["sales_hiring_interval"] and sales_staff_count < params["max_sales_staff"]:
            sales_staff_count += 1
            sales_staff_hire_months.append(i)
            
        # Junior Developer hiring
        if i >= params["jr_dev_start_month"] and jr_dev_count == 0:
            jr_dev_count = 1
            
        # Admin staff hiring
        if i >= params["admin_start_month"] and admin_count == 0:
            admin_count = 1
        
        # --- Growth Calculations ---
        # Client growth
        client_growth_rate = params["client_growth_rates"][year_index]
        developer_growth_rate = params["developer_growth_rates"][year_index]
        affiliate_growth_rate = params["affiliate_growth_rates"][year_index]
        
        # Base acquisition from marketing + product-led growth
        base_acquisition = max(5, int(clients * client_growth_rate * 0.2)) if i == 0 else max(10, int(clients * client_growth_rate * 0.2))
        
        # Sales-driven acquisition
        sales_acquisition = 0
        if sales_staff_count > 0:
            sales_acquisition = 20 * sales_staff_count * (1 + (i // 6) * 0.1)  # Each sales person brings 20 clients/month, improving 10% every 6 months
            
        # Affiliate-driven acquisition
        affiliate_acquisition = 0
        if affiliates > 0:
            affiliate_acquisition = int(affiliates * 0.5)  # Each affiliate brings 0.5 clients on average per month
            
        new_clients = base_acquisition + sales_acquisition + affiliate_acquisition
        new_devs = max(1, int(developers * developer_growth_rate)) if developers > 0 else 2
        new_affs = max(2, int(affiliates * affiliate_growth_rate)) if affiliates > 0 else 3
        
        # Store cohort for future conversion calculation
        if new_clients > 0:
            client_cohorts.append((i, new_clients))
            
        # Update totals
        clients += new_clients
        developers += new_devs
        affiliates += new_affs
        
        # Calculate paying clients
        paying_clients = 0
        for cohort_month, cohort_size in client_cohorts:
            months_since_joining = i - cohort_month
            
            # If past free period, apply conversion rate
            if months_since_joining >= params["free_months"]:
                # First month after free period - apply conversion
                if months_since_joining == params["free_months"]:
                    cohort_size = int(cohort_size * params["conversion_rate"])
                
                paying_clients += cohort_size
        
        # --- Revenue Calculations ---
        client_revenue = paying_clients * params["subscription_price"]
        developer_revenue = developers * params["subscription_price"]
        
        # Calculate affiliate commission
        affiliate_commission = affiliates * params["affiliate_commission"]
        
        # Total revenue
        revenue = client_revenue + developer_revenue
        
        # --- Expense Calculations ---
        # Staff salaries
        cto_cost = cto_count * params["cto_salary"]
        ceo_cost = ceo_count * params["ceo_salary"]
        jr_dev_cost = jr_dev_count * params["jr_dev_salary"]
        admin_cost = admin_count * params["admin_salary"]
        
        # Sales staff cost - base + commission
        sales_base_cost = sales_staff_count * params["sales_base_salary"]
        sales_commission_cost = sales_acquisition * params["subscription_price"] * params["sales_commission"]
        sales_total_cost = sales_base_cost + sales_commission_cost
        
        # Infrastructure costs
        infrastructure_cost = (clients + developers) * params["infrastructure_cost_per_user"]
        
        # Marketing costs
        marketing_cost = revenue * params["marketing_percentage"]
        
        # Affiliate program costs
        affiliate_program_cost = affiliate_commission
        
        # Other expenses
        other_expenses = revenue * params["other_expenses_percentage"]
        
        # Total expenses
        total_expenses = (
            cto_cost + 
            ceo_cost + 
            jr_dev_cost + 
            admin_cost + 
            sales_total_cost + 
            infrastructure_cost + 
            marketing_cost + 
            affiliate_program_cost + 
            other_expenses
        )
        
        # Net income (EBITDA)
        ebitda = revenue - total_expenses
        
        # Store monthly data
        monthly_data.append({
            "year": current_year,
            "month": current_month,
            "month_number": i,
            "date": current_date.strftime("%Y-%m-%d"),
            "income": round(revenue, 2),
            "expenses": round(total_expenses, 2),
            "ebitda": round(ebitda, 2),
            "client_count": clients,
            "new_clients": new_clients,
            "paying_clients": paying_clients,
            "developer_count": developers,
            "affiliate_count": affiliates,
            "sales_staff": sales_staff_count,
            "jr_devs": jr_dev_count,
            "admin_staff": admin_count,
            "cto_count": cto_count,
            "total_staff": sales_staff_count + jr_dev_count + admin_count + cto_count,
            "ceo_count": ceo_count,
            "ceo_cost": round(ceo_cost, 2),
            "total_staff": sales_staff_count + jr_dev_count + admin_count + cto_count + ceo_count,
            # Detailed costs
            "cto_cost": round(cto_cost, 2),
            "sales_cost": round(sales_total_cost, 2),
            "jr_dev_cost": round(jr_dev_cost, 2),
            "admin_cost": round(admin_cost, 2),
            "infrastructure_cost": round(infrastructure_cost, 2),
            "marketing_cost": round(marketing_cost, 2),
            "affiliate_cost": round(affiliate_program_cost, 2),
            "other_expenses": round(other_expenses, 2),

        })

    return monthly_data

# Aggregate monthly data to yearly summaries
def get_yearly_summary(monthly_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    yearly_summary = {}
    
    for month in monthly_data:
        year = month["year"]
        if year not in yearly_summary:
            yearly_summary[year] = {
                "year": year,
                "income": 0,
                "expenses": 0,
                "ebitda": 0,
                "end_of_year": None
            }
        
        yearly_summary[year]["income"] += month["income"]
        yearly_summary[year]["expenses"] += month["expenses"]
        yearly_summary[year]["ebitda"] += month["ebitda"]
        
        # Keep the December data (or last month of the year)
        if month["month"] == 12 or yearly_summary[year]["end_of_year"] is None:
            yearly_summary[year]["end_of_year"] = {
                "client_count": month["client_count"],
                "paying_clients": month["paying_clients"],
                "developer_count": month["developer_count"],
                "affiliate_count": month["affiliate_count"],
                "sales_staff": month["sales_staff"],
                "jr_devs": month["jr_devs"],
                "admin_staff": month["admin_staff"],
                "cto_count": month["cto_count"],
                "total_staff": month["total_staff"]
            }
    
    # Convert dict to list and round values
    result = []
    for year, data in yearly_summary.items():
        year_data = {
            "year": year,
            "income": round(data["income"], 2),
            "expenses": round(data["expenses"], 2),
            "ebitda": round(data["ebitda"], 2)
        }
        # Add staff data
        if data["end_of_year"]:
            year_data.update({
                "client_count": data["end_of_year"]["client_count"],
                "paying_clients": data["end_of_year"]["paying_clients"],
                "developer_count": data["end_of_year"]["developer_count"],
                "affiliate_count": data["end_of_year"]["affiliate_count"],
                "sales_staff": data["end_of_year"]["sales_staff"],
                "jr_devs": data["end_of_year"]["jr_devs"],
                "admin_staff": data["end_of_year"]["admin_staff"],
                "cto_count": data["end_of_year"]["cto_count"],
                "total_staff": data["end_of_year"]["total_staff"]
            })
        result.append(year_data)
    
    return sorted(result, key=lambda x: x["year"])

# Helper function to get scenario by ID
def get_scenario_by_id(db: Session, scenario_id: int):
    scenario = db.query(ForecastScenario).filter(ForecastScenario.id == scenario_id).first()
    if not scenario:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return scenario

# Helper function to get default scenario
def get_default_scenario(db: Session):
    default_scenario = db.query(ForecastScenario).filter(ForecastScenario.is_default == True).first()
    if not default_scenario:
        # Create a default scenario if none exists
        default_scenario = create_default_scenario(db)
    return default_scenario

# Helper function to create a default scenario
def create_default_scenario(db: Session):
    # Create default scenario
    default_scenario = ForecastScenario(
        name="Default Scenario",
        description="Default 5-year forecast scenario",
        is_default=True
    )
    db.add(default_scenario)
    db.commit()
    db.refresh(default_scenario)
    
    # Add default parameters
    default_params = Parameters(
        scenario_id=default_scenario.id,
        start_date=DEFAULT_PARAMETERS["start_date"],
        initial_clients=DEFAULT_PARAMETERS["initial_clients"],
        initial_developers=DEFAULT_PARAMETERS["initial_developers"],
        initial_affiliates=DEFAULT_PARAMETERS["initial_affiliates"],
        client_growth_rates=DEFAULT_PARAMETERS["client_growth_rates"],
        developer_growth_rates=DEFAULT_PARAMETERS["developer_growth_rates"],
        affiliate_growth_rates=DEFAULT_PARAMETERS["affiliate_growth_rates"],
        subscription_price=DEFAULT_PARAMETERS["subscription_price"],
        affiliate_commission=DEFAULT_PARAMETERS["affiliate_commission"],
        free_months=DEFAULT_PARAMETERS["free_months"],
        conversion_rate=DEFAULT_PARAMETERS["conversion_rate"],
        cto_start_month=DEFAULT_PARAMETERS["cto_start_month"],
        ceo_start_month=DEFAULT_PARAMETERS["ceo_start_month"],
        ceo_salary=DEFAULT_PARAMETERS["ceo_salary"],
        sales_start_month=DEFAULT_PARAMETERS["sales_start_month"],
        sales_hiring_interval=DEFAULT_PARAMETERS["sales_hiring_interval"],
        max_sales_staff=DEFAULT_PARAMETERS["max_sales_staff"],
        jr_dev_start_month=DEFAULT_PARAMETERS["jr_dev_start_month"],
        admin_start_month=DEFAULT_PARAMETERS["admin_start_month"],
        cto_salary=DEFAULT_PARAMETERS["cto_salary"],
        sales_base_salary=DEFAULT_PARAMETERS["sales_base_salary"],
        sales_commission=DEFAULT_PARAMETERS["sales_commission"],
        jr_dev_salary=DEFAULT_PARAMETERS["jr_dev_salary"],
        admin_salary=DEFAULT_PARAMETERS["admin_salary"],
        marketing_percentage=DEFAULT_PARAMETERS["marketing_percentage"],
        infrastructure_cost_per_user=DEFAULT_PARAMETERS["infrastructure_cost_per_user"],
        other_expenses_percentage=DEFAULT_PARAMETERS["other_expenses_percentage"]
    )
    db.add(default_params)
    
    # Generate monthly data
    monthly_data = calculate_projections(DEFAULT_PARAMETERS)
    for month_data in monthly_data:
        db_month = MonthlyData(
            scenario_id=default_scenario.id,
            year=month_data["year"],
            month=month_data["month"],
            month_number=month_data["month_number"],
            date=month_data["date"],
            income=month_data["income"],
            expenses=month_data["expenses"],
            ebitda=month_data["ebitda"],
            client_count=month_data["client_count"],
            new_clients=month_data["new_clients"],
            paying_clients=month_data["paying_clients"],
            developer_count=month_data["developer_count"],
            affiliate_count=month_data["affiliate_count"],
            sales_staff=month_data["sales_staff"],
            jr_devs=month_data["jr_devs"],
            admin_staff=month_data["admin_staff"],
            cto_count=month_data["cto_count"],
            total_staff=month_data["total_staff"],
            cto_cost=month_data["cto_cost"],
            sales_cost=month_data["sales_cost"],
            jr_dev_cost=month_data["jr_dev_cost"],
            admin_cost=month_data["admin_cost"],
            infrastructure_cost=month_data["infrastructure_cost"],
            marketing_cost=month_data["marketing_cost"],
            affiliate_cost=month_data["affiliate_cost"],
            other_expenses=month_data["other_expenses"]
        )
        db.add(db_month)
    
    # Generate yearly summary
    yearly_data = get_yearly_summary(monthly_data)
    for year_data in yearly_data:
        db_year = YearlySummary(
            scenario_id=default_scenario.id,
            year=year_data["year"],
            income=year_data["income"],
            expenses=year_data["expenses"],
            ebitda=year_data["ebitda"],
            client_count=year_data["client_count"],
            paying_clients=year_data["paying_clients"],
            developer_count=year_data["developer_count"],
            affiliate_count=year_data["affiliate_count"],
            sales_staff=year_data["sales_staff"],
            jr_devs=year_data["jr_devs"],
            admin_staff=year_data["admin_staff"],
            cto_count=year_data["cto_count"],
            total_staff=year_data["total_staff"]
        )
        db.add(db_year)
    
    db.commit()
    db.refresh(default_scenario)
    return default_scenario

# Helper function to get parameters from scenario
def get_parameters_from_scenario(scenario):
    if not scenario.parameters:
        return DEFAULT_PARAMETERS
    
    # Convert JSON strings to python objects if needed
    client_growth_rates = scenario.parameters.client_growth_rates
    developer_growth_rates = scenario.parameters.developer_growth_rates
    affiliate_growth_rates = scenario.parameters.affiliate_growth_rates
    
    if isinstance(client_growth_rates, str):
        client_growth_rates = json.loads(client_growth_rates)
    if isinstance(developer_growth_rates, str):
        developer_growth_rates = json.loads(developer_growth_rates)
    if isinstance(affiliate_growth_rates, str):
        affiliate_growth_rates = json.loads(affiliate_growth_rates)
    
    # Construct the parameters dictionary
    return {
        "start_date": scenario.parameters.start_date,
        "initial_clients": scenario.parameters.initial_clients,
        "initial_developers": scenario.parameters.initial_developers,
        "initial_affiliates": scenario.parameters.initial_affiliates,
        "client_growth_rates": client_growth_rates,
        "developer_growth_rates": developer_growth_rates,
        "affiliate_growth_rates": affiliate_growth_rates,
        "subscription_price": scenario.parameters.subscription_price,
        "affiliate_commission": scenario.parameters.affiliate_commission,
        "free_months": scenario.parameters.free_months,
        "conversion_rate": scenario.parameters.conversion_rate,
        "cto_start_month": scenario.parameters.cto_start_month,
        "sales_start_month": scenario.parameters.sales_start_month,
        "sales_hiring_interval": scenario.parameters.sales_hiring_interval,
        "max_sales_staff": scenario.parameters.max_sales_staff,
        "jr_dev_start_month": scenario.parameters.jr_dev_start_month,
        "admin_start_month": scenario.parameters.admin_start_month,
        "cto_salary": scenario.parameters.cto_salary,
        "sales_base_salary": scenario.parameters.sales_base_salary,
        "sales_commission": scenario.parameters.sales_commission,
        "jr_dev_salary": scenario.parameters.jr_dev_salary,
        "admin_salary": scenario.parameters.admin_salary,
        "marketing_percentage": scenario.parameters.marketing_percentage,
        "infrastructure_cost_per_user": scenario.parameters.infrastructure_cost_per_user,
        "other_expenses_percentage": scenario.parameters.other_expenses_percentage
    }

# Helper function to recalculate and update a scenario with new parameters
def recalculate_scenario(db: Session, scenario_id: int, params: Dict[str, Any]):
    # Get scenario
    scenario = get_scenario_by_id(db, scenario_id)
    
    # Update parameters
    if scenario.parameters:
        for key, value in params.items():
            if key in ["client_growth_rates", "developer_growth_rates", "affiliate_growth_rates"]:
                # Ensure proper JSON storage for array values
                setattr(scenario.parameters, key, value)
            elif hasattr(scenario.parameters, key):
                setattr(scenario.parameters, key, value)
    
    # Delete existing monthly data and yearly summaries
    db.query(MonthlyData).filter(MonthlyData.scenario_id == scenario_id).delete()
    db.query(YearlySummary).filter(YearlySummary.scenario_id == scenario_id).delete()
    
    # Generate new monthly data
    monthly_data = calculate_projections(params)
    for month_data in monthly_data:
        db_month = MonthlyData(
            scenario_id=scenario_id,
            year=month_data["year"],
            month=month_data["month"],
            month_number=month_data["month_number"],
            date=month_data["date"],
            income=month_data["income"],
            expenses=month_data["expenses"],
            ebitda=month_data["ebitda"],
            client_count=month_data["client_count"],
            new_clients=month_data["new_clients"],
            paying_clients=month_data["paying_clients"],
            developer_count=month_data["developer_count"],
            affiliate_count=month_data["affiliate_count"],
            sales_staff=month_data["sales_staff"],
            jr_devs=month_data["jr_devs"],
            admin_staff=month_data["admin_staff"],
            cto_count=month_data["cto_count"],
            total_staff=month_data["total_staff"],
            cto_cost=month_data["cto_cost"],
            sales_cost=month_data["sales_cost"],
            jr_dev_cost=month_data["jr_dev_cost"],
            admin_cost=month_data["admin_cost"],
            infrastructure_cost=month_data["infrastructure_cost"],
            marketing_cost=month_data["marketing_cost"],
            affiliate_cost=month_data["affiliate_cost"],
            other_expenses=month_data["other_expenses"]
        )
        db.add(db_month)
    
    # Generate yearly summary
    yearly_data = get_yearly_summary(monthly_data)
    for year_data in yearly_data:
        db_year = YearlySummary(
            scenario_id=scenario_id,
            year=year_data["year"],
            income=year_data["income"],
            expenses=year_data["expenses"],
            ebitda=year_data["ebitda"],
            client_count=year_data["client_count"],
            paying_clients=year_data["paying_clients"],
            developer_count=year_data["developer_count"],
            affiliate_count=year_data["affiliate_count"],
            sales_staff=year_data["sales_staff"],
            jr_devs=year_data["jr_devs"],
            admin_staff=year_data["admin_staff"],
            cto_count=year_data["cto_count"],
            total_staff=year_data["total_staff"]
        )
        db.add(db_year)
    
    db.commit()
    return yearly_data

# Pydantic models for API
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

# API Routes
@app.get("/api/scenarios", response_model=List[Scenario])
async def get_scenarios(db: Session = Depends(get_db)):
    """Get all forecast scenarios"""
    scenarios = db.query(ForecastScenario).all()
    return scenarios

@app.get("/api/scenarios/{scenario_id}", response_model=Scenario)
async def get_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Get a specific forecast scenario by ID"""
    scenario = get_scenario_by_id(db, scenario_id)
    return scenario

@app.post("/api/scenarios", response_model=Scenario)
async def create_scenario(scenario: ScenarioCreate, db: Session = Depends(get_db)):
    """Create a new forecast scenario"""
    # Create new scenario
    db_scenario = ForecastScenario(
        name=scenario.name,
        description=scenario.description,
        is_default=False
    )
    db.add(db_scenario)
    db.commit()
    db.refresh(db_scenario)
    
    # Copy parameters from default scenario
    default_scenario = get_default_scenario(db)
    default_params = get_parameters_from_scenario(default_scenario)
    
    # Create parameters
    params = Parameters(
        scenario_id=db_scenario.id,
        **{k: v for k, v in default_params.items()}
    )
    db.add(params)
    
    # Calculate and store projections
    recalculate_scenario(db, db_scenario.id, default_params)
    
    db.commit()
    db.refresh(db_scenario)
    return db_scenario

@app.put("/api/scenarios/{scenario_id}", response_model=Scenario)
async def update_scenario(
    scenario_id: int, 
    scenario_update: ScenarioUpdate, 
    db: Session = Depends(get_db)
):
    """Update a forecast scenario"""
    db_scenario = get_scenario_by_id(db, scenario_id)
    
    if scenario_update.name is not None:
        db_scenario.name = scenario_update.name
    
    if scenario_update.description is not None:
        db_scenario.description = scenario_update.description
    
    if scenario_update.is_default is not None and scenario_update.is_default:
        # If setting this scenario as default, remove default flag from other scenarios
        db.query(ForecastScenario).filter(ForecastScenario.id != scenario_id).update({
            ForecastScenario.is_default: False
        })
        db_scenario.is_default = True
    
    db.commit()
    db.refresh(db_scenario)
    return db_scenario

@app.delete("/api/scenarios/{scenario_id}")
async def delete_scenario(scenario_id: int, db: Session = Depends(get_db)):
    """Delete a forecast scenario"""
    db_scenario = get_scenario_by_id(db, scenario_id)
    
    # Prevent deleting the default scenario
    if db_scenario.is_default:
        raise HTTPException(status_code=400, detail="Cannot delete the default scenario")
    
    db.delete(db_scenario)
    db.commit()
    return {"status": "success", "message": f"Scenario '{db_scenario.name}' deleted"}

@app.get("/api/scenarios/{scenario_id}/parameters")
async def get_scenario_parameters(scenario_id: int, db: Session = Depends(get_db)):
    """Get parameters for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    parameters = get_parameters_from_scenario(scenario)
    return parameters

@app.post("/api/scenarios/{scenario_id}/parameters/update")
async def update_scenario_parameters(
    scenario_id: int, 
    params: dict, 
    db: Session = Depends(get_db)
):
    """Update parameters for a specific scenario and recalculate projections"""
    scenario = get_scenario_by_id(db, scenario_id)
    current_params = get_parameters_from_scenario(scenario)
    
    # Merge current parameters with updated ones
    updated_params = {**current_params, **params}
    
    # Recalculate scenario
# Recalculate scenario
    yearly_summary = recalculate_scenario(db, scenario_id, updated_params)
    
    return {
        "status": "success", 
        "message": "Parameters updated",
        "yearly_summary": yearly_summary
    }

@app.get("/api/scenarios/{scenario_id}/financials/yearly")
async def get_scenario_yearly_financials(scenario_id: int, db: Session = Depends(get_db)):
    """Get yearly financial data for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    yearly_data = db.query(YearlySummary).filter(
        YearlySummary.scenario_id == scenario_id
    ).order_by(YearlySummary.year).all()
    
    result = []
    for year in yearly_data:
        result.append({
            "year": year.year,
            "income": year.income,
            "expenses": year.expenses,
            "ebitda": year.ebitda,
            "client_count": year.client_count,
            "paying_clients": year.paying_clients,
            "developer_count": year.developer_count,
            "affiliate_count": year.affiliate_count,
            "sales_staff": year.sales_staff,
            "jr_devs": year.jr_devs,
            "admin_staff": year.admin_staff,
            "cto_count": year.cto_count,
            "ceo_count": year.ceo_count, 
            "total_staff": year.total_staff
        })
    
    return result

@app.get("/api/scenarios/{scenario_id}/financials/monthly")
async def get_scenario_monthly_financials(scenario_id: int, db: Session = Depends(get_db)):
    """Get monthly financial data for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    monthly_data = db.query(MonthlyData).filter(
        MonthlyData.scenario_id == scenario_id
    ).order_by(MonthlyData.month_number).all()
    
    result = []
    for month in monthly_data:
        result.append({
            "year": month.year,
            "month": month.month,
            "month_number": month.month_number,
            "date": month.date,
            "income": month.income,
            "expenses": month.expenses,
            "ebitda": month.ebitda,
            "client_count": month.client_count,
            "new_clients": month.new_clients,
            "paying_clients": month.paying_clients,
            "developer_count": month.developer_count,
            "affiliate_count": month.affiliate_count,
            "sales_staff": month.sales_staff,
            "jr_devs": month.jr_devs,
            "admin_staff": month.admin_staff,
            "cto_count": month.cto_count,
            "total_staff": month.total_staff,
            "cto_cost": month.cto_cost,
            "sales_cost": month.sales_cost,
            "jr_dev_cost": month.jr_dev_cost,
            "admin_cost": month.admin_cost,
            "infrastructure_cost": month.infrastructure_cost,
            "marketing_cost": month.marketing_cost,
            "affiliate_cost": month.affiliate_cost,
            "other_expenses": month.other_expenses
        })
    
    return result

@app.get("/api/scenarios/{scenario_id}/staff/yearly")
async def get_scenario_staff_summary(scenario_id: int, db: Session = Depends(get_db)):
    """Get yearly staff data for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    yearly_data = db.query(YearlySummary).filter(
        YearlySummary.scenario_id == scenario_id
    ).order_by(YearlySummary.year).all()
    
    result = []
    for year in yearly_data:
        result.append({
            "year": year.year,
            "client_count": year.client_count,
            "paying_clients": year.paying_clients,
            "developer_count": year.developer_count,
            "affiliate_count": year.affiliate_count,
            "sales_staff": year.sales_staff,
            "jr_devs": year.jr_devs,
            "admin_staff": year.admin_staff,
            "cto_count": year.cto_count,
            "total_staff": year.total_staff
        })
    
    return result

@app.get("/api/scenarios/{scenario_id}/expense-breakdown/monthly")
async def get_scenario_expense_breakdown(scenario_id: int, db: Session = Depends(get_db)):
    """Returns a detailed breakdown of expenses by category for each month for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    monthly_data = db.query(MonthlyData).filter(
        MonthlyData.scenario_id == scenario_id
    ).order_by(MonthlyData.month_number).all()
    
    result = []
    for month in monthly_data:
        result.append({
            "year": month.year,
            "month": month.month,
            "date": month.date,
            "cto_cost": month.cto_cost,
            "sales_cost": month.sales_cost,
            "jr_dev_cost": month.jr_dev_cost,
            "admin_cost": month.admin_cost,
            "infrastructure_cost": month.infrastructure_cost,
            "marketing_cost": month.marketing_cost,
            "affiliate_cost": month.affiliate_cost,
            "other_expenses": month.other_expenses,
            "total_expenses": month.expenses
        })
    
    return result

# Legacy API routes for backward compatibility
@app.get("/api/financials/yearly")
async def get_yearly_financials(db: Session = Depends(get_db)):
    """Get yearly financial data from the default scenario"""
    default_scenario = get_default_scenario(db)
    return await get_scenario_yearly_financials(default_scenario.id, db)

@app.get("/api/financials/monthly")
async def get_monthly_financials(db: Session = Depends(get_db)):
    """Get monthly financial data from the default scenario"""
    default_scenario = get_default_scenario(db)
    return await get_scenario_monthly_financials(default_scenario.id, db)

@app.get("/api/parameters")
async def get_parameters(db: Session = Depends(get_db)):
    """Get parameters from the default scenario"""
    default_scenario = get_default_scenario(db)
    return await get_scenario_parameters(default_scenario.id, db)

@app.post("/api/parameters/update")
async def update_parameters(params: dict, db: Session = Depends(get_db)):
    """Update parameters for the default scenario"""
    default_scenario = get_default_scenario(db)
    return await update_scenario_parameters(default_scenario.id, params, db)

@app.get("/api/staff/yearly")
async def get_staff_summary(db: Session = Depends(get_db)):
    """Get staff data from the default scenario"""
    default_scenario = get_default_scenario(db)
    return await get_scenario_staff_summary(default_scenario.id, db)

@app.get("/api/expense-breakdown/monthly")
async def get_expense_breakdown(db: Session = Depends(get_db)):
    """Get expense breakdown from the default scenario"""
    default_scenario = get_default_scenario(db)
    return await get_scenario_expense_breakdown(default_scenario.id, db)

@app.get("/")
async def root():
    return {"message": "Welcome to RYZE.ai Financial Forecast API"}