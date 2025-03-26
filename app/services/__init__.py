# app/services/__init__.py
# Import services as needed
from app.services.financial import (
    get_scenario_by_id,
    get_default_scenario,
    get_parameters_from_scenario,
    recalculate_scenario,
    calculate_projections,
    get_yearly_summary,
    DEFAULT_PARAMETERS
)