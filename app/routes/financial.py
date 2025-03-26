# app/routes/financial.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
from datetime import datetime

from app.database import get_db
from app.models.database import ForecastScenario, Parameters, MonthlyData, YearlySummary
from app.models.user import User
from app.services.financial import (
    get_scenario_by_id,
    get_default_scenario,
    get_parameters_from_scenario,
    recalculate_scenario
)
from app.auth.utils import get_current_user  # Import the auth dependency

from app.schemas.financial import (
    ScenarioBase,
    ScenarioCreate,
    ScenarioUpdate,
    Scenario,
    ParameterUpdate
)

router = APIRouter(tags=["financials"])

@router.get("/api/scenarios", response_model=List[Scenario])
async def get_scenarios(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Get all forecast scenarios for the current user"""
    # Return only scenarios associated with the current user
    return current_user.scenarios

@router.get("/api/scenarios/{scenario_id}", response_model=Scenario)
async def get_scenario(
    scenario_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Get a specific forecast scenario by ID"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scenario"
        )
    
    return scenario

@router.post("/api/scenarios", response_model=Scenario)
async def create_scenario(
    scenario: ScenarioCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Create a new forecast scenario for the current user"""
    # Create new scenario
    db_scenario = ForecastScenario(
        name=scenario.name,
        description=scenario.description,
        is_default=False
    )
    db.add(db_scenario)
    db.flush()  # Flush to get the ID before committing
    
    # Associate with current user
    current_user.scenarios.append(db_scenario)
    
    db.commit()
    db.refresh(db_scenario)
    
    # Get a default scenario to copy parameters from
    # First try user's default scenario, then any scenario
    user_default = None
    for s in current_user.scenarios:
        if s.is_default:
            user_default = s
            break
    
    default_scenario = user_default or (current_user.scenarios[0] if current_user.scenarios else None)
    
    # If no existing scenarios, use system default or basic parameters
    if default_scenario:
        default_params = get_parameters_from_scenario(default_scenario)
    else:
        # Use system default
        system_default = get_default_scenario(db)
        default_params = get_parameters_from_scenario(system_default)
    
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

@router.put("/api/scenarios/{scenario_id}", response_model=Scenario)
async def update_scenario(
    scenario_id: int, 
    scenario_update: ScenarioUpdate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Update a forecast scenario"""
    db_scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if db_scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this scenario"
        )
    
    if scenario_update.name is not None:
        db_scenario.name = scenario_update.name
    
    if scenario_update.description is not None:
        db_scenario.description = scenario_update.description
    
    if scenario_update.is_default is not None and scenario_update.is_default:
        # If setting this scenario as default, remove default flag from other user scenarios only
        for s in current_user.scenarios:
            if s.id != scenario_id:
                s.is_default = False
        
        db_scenario.is_default = True
    
    db.commit()
    db.refresh(db_scenario)
    return db_scenario

@router.delete("/api/scenarios/{scenario_id}")
async def delete_scenario(
    scenario_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Delete a forecast scenario"""
    db_scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if db_scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this scenario"
        )
    
    # Check if it's the user's only scenario
    if len(current_user.scenarios) == 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your only scenario"
        )
    
    # If deleting the default scenario, set another as default
    if db_scenario.is_default and len(current_user.scenarios) > 1:
        # Find another scenario to set as default
        other_scenario = next(s for s in current_user.scenarios if s.id != scenario_id)
        other_scenario.is_default = True
    
    # Remove the association between user and scenario
    current_user.scenarios.remove(db_scenario)
    
    # Check if any other users have this scenario
    if not db_scenario.users:
        # No other users have this scenario, safe to delete it
        db.delete(db_scenario)
    
    db.commit()
    return {"status": "success", "message": f"Scenario '{db_scenario.name}' deleted"}

@router.put("/api/scenarios/{scenario_id}/set-default")
async def set_default_scenario(
    scenario_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Set a scenario as the default for the current user"""
    db_scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if db_scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this scenario"
        )
    
    # Remove default flag from other scenarios
    for s in current_user.scenarios:
        if s.id != scenario_id:
            s.is_default = False
    
    # Set this one as default
    db_scenario.is_default = True
    
    db.commit()
    db.refresh(db_scenario)
    return {"status": "success", "message": f"Scenario '{db_scenario.name}' set as default"}

@router.get("/api/scenarios/{scenario_id}/parameters")
async def get_scenario_parameters(
    scenario_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Get parameters for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scenario"
        )
    
    parameters = get_parameters_from_scenario(scenario)
    return parameters

@router.post("/api/scenarios/{scenario_id}/parameters/update")
async def update_scenario_parameters(
    scenario_id: int, 
    params: dict, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Update parameters for a specific scenario and recalculate projections"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to modify this scenario"
        )
    
    current_params = get_parameters_from_scenario(scenario)
    
    # Merge current parameters with updated ones
    updated_params = {**current_params, **params}
    
    # Recalculate scenario
    yearly_summary = recalculate_scenario(db, scenario_id, updated_params)
    
    return {
        "status": "success", 
        "message": "Parameters updated",
        "yearly_summary": yearly_summary
    }

@router.get("/api/scenarios/{scenario_id}/financials/yearly")
async def get_scenario_yearly_financials(
    scenario_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Get yearly financial data for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scenario"
        )
    
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
            "ceo_count": getattr(year, "ceo_count", 0),
            "total_staff": year.total_staff
        })
    
    return result

@router.get("/api/scenarios/{scenario_id}/financials/monthly")
async def get_scenario_monthly_financials(
    scenario_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Get monthly financial data for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scenario"
        )
    
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

@router.get("/api/scenarios/{scenario_id}/staff/yearly")
async def get_scenario_staff_summary(
    scenario_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Get yearly staff data for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scenario"
        )
    
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

@router.get("/api/scenarios/{scenario_id}/expense-breakdown/monthly")
async def get_scenario_expense_breakdown(
    scenario_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Returns a detailed breakdown of expenses by category for each month for a specific scenario"""
    scenario = get_scenario_by_id(db, scenario_id)
    
    # Check if user has access to this scenario
    if scenario not in current_user.scenarios:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this scenario"
        )
    
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

# Legacy API routes for backward compatibility - now user-specific
@router.get("/api/financials/yearly")
async def get_yearly_financials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Get yearly financial data from the user's default scenario"""
    # Find the user's default scenario
    default_scenario = None
    for scenario in current_user.scenarios:
        if scenario.is_default:
            default_scenario = scenario
            break
    
    # If no default, use the first scenario or create a new one
    if not default_scenario:
        if not current_user.scenarios:
            # User has no scenarios, create one
            scenario_data = ScenarioCreate(name="Default Scenario", description="Your default forecast scenario")
            default_scenario = await create_scenario(scenario_data, db, current_user)
        else:
            # Use the first available scenario
            default_scenario = current_user.scenarios[0]
            # Mark it as default
            default_scenario.is_default = True
            db.commit()
    
    return await get_scenario_yearly_financials(default_scenario.id, db, current_user)

@router.get("/api/financials/monthly")
async def get_monthly_financials(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Get monthly financial data from the user's default scenario"""
    # Find the user's default scenario (similar logic as above)
    default_scenario = None
    for scenario in current_user.scenarios:
        if scenario.is_default:
            default_scenario = scenario
            break
    
    if not default_scenario:
        if not current_user.scenarios:
            scenario_data = ScenarioCreate(name="Default Scenario", description="Your default forecast scenario")
            default_scenario = await create_scenario(scenario_data, db, current_user)
        else:
            default_scenario = current_user.scenarios[0]
            default_scenario.is_default = True
            db.commit()
    
    return await get_scenario_monthly_financials(default_scenario.id, db, current_user)

@router.get("/api/parameters")
async def get_parameters(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Get parameters from the user's default scenario"""
    # Find the user's default scenario (similar logic as above)
    default_scenario = None
    for scenario in current_user.scenarios:
        if scenario.is_default:
            default_scenario = scenario
            break
    
    if not default_scenario:
        if not current_user.scenarios:
            scenario_data = ScenarioCreate(name="Default Scenario", description="Your default forecast scenario")
            default_scenario = await create_scenario(scenario_data, db, current_user)
        else:
            default_scenario = current_user.scenarios[0]
            default_scenario.is_default = True
            db.commit()
    
    return await get_scenario_parameters(default_scenario.id, db, current_user)

@router.post("/api/parameters/update")
async def update_parameters(
    params: dict, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)  # Add auth dependency
):
    """Update parameters for the user's default scenario"""
    # Find the user's default scenario (similar logic as above)
    default_scenario = None
    for scenario in current_user.scenarios:
        if scenario.is_default:
            default_scenario = scenario
            break
    
    if not default_scenario:
        if not current_user.scenarios:
            scenario_data = ScenarioCreate(name="Default Scenario", description="Your default forecast scenario")
            default_scenario = await create_scenario(scenario_data, db, current_user)
        else:
            default_scenario = current_user.scenarios[0]
            default_scenario.is_default = True
            db.commit()
    
    return await update_scenario_parameters(default_scenario.id, params, db, current_user)