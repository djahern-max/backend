"""Initial migration

Revision ID: 68f977f1e17c
Revises: 
Create Date: 2025-03-25 09:02:01.471227

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68f977f1e17c'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('forecast_scenarios',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(), nullable=True),
    sa.Column('description', sa.String(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.Column('is_default', sa.Boolean(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_forecast_scenarios_id'), 'forecast_scenarios', ['id'], unique=False)
    op.create_index(op.f('ix_forecast_scenarios_name'), 'forecast_scenarios', ['name'], unique=True)
    op.create_table('monthly_data',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scenario_id', sa.Integer(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('month', sa.Integer(), nullable=True),
    sa.Column('month_number', sa.Integer(), nullable=True),
    sa.Column('date', sa.String(), nullable=True),
    sa.Column('income', sa.Float(), nullable=True),
    sa.Column('expenses', sa.Float(), nullable=True),
    sa.Column('ebitda', sa.Float(), nullable=True),
    sa.Column('client_count', sa.Integer(), nullable=True),
    sa.Column('new_clients', sa.Integer(), nullable=True),
    sa.Column('paying_clients', sa.Integer(), nullable=True),
    sa.Column('developer_count', sa.Integer(), nullable=True),
    sa.Column('affiliate_count', sa.Integer(), nullable=True),
    sa.Column('sales_staff', sa.Integer(), nullable=True),
    sa.Column('jr_devs', sa.Integer(), nullable=True),
    sa.Column('admin_staff', sa.Integer(), nullable=True),
    sa.Column('cto_count', sa.Integer(), nullable=True),
    sa.Column('total_staff', sa.Integer(), nullable=True),
    sa.Column('cto_cost', sa.Float(), nullable=True),
    sa.Column('sales_cost', sa.Float(), nullable=True),
    sa.Column('jr_dev_cost', sa.Float(), nullable=True),
    sa.Column('admin_cost', sa.Float(), nullable=True),
    sa.Column('infrastructure_cost', sa.Float(), nullable=True),
    sa.Column('marketing_cost', sa.Float(), nullable=True),
    sa.Column('affiliate_cost', sa.Float(), nullable=True),
    sa.Column('other_expenses', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['scenario_id'], ['forecast_scenarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_monthly_data_id'), 'monthly_data', ['id'], unique=False)
    op.create_table('parameters',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scenario_id', sa.Integer(), nullable=True),
    sa.Column('start_date', sa.String(), nullable=True),
    sa.Column('initial_clients', sa.Integer(), nullable=True),
    sa.Column('initial_developers', sa.Integer(), nullable=True),
    sa.Column('initial_affiliates', sa.Integer(), nullable=True),
    sa.Column('client_growth_rates', sa.JSON(), nullable=True),
    sa.Column('developer_growth_rates', sa.JSON(), nullable=True),
    sa.Column('affiliate_growth_rates', sa.JSON(), nullable=True),
    sa.Column('subscription_price', sa.Float(), nullable=True),
    sa.Column('affiliate_commission', sa.Float(), nullable=True),
    sa.Column('free_months', sa.Integer(), nullable=True),
    sa.Column('conversion_rate', sa.Float(), nullable=True),
    sa.Column('cto_start_month', sa.Integer(), nullable=True),
    sa.Column('sales_start_month', sa.Integer(), nullable=True),
    sa.Column('sales_hiring_interval', sa.Integer(), nullable=True),
    sa.Column('max_sales_staff', sa.Integer(), nullable=True),
    sa.Column('jr_dev_start_month', sa.Integer(), nullable=True),
    sa.Column('admin_start_month', sa.Integer(), nullable=True),
    sa.Column('cto_salary', sa.Float(), nullable=True),
    sa.Column('sales_base_salary', sa.Float(), nullable=True),
    sa.Column('sales_commission', sa.Float(), nullable=True),
    sa.Column('jr_dev_salary', sa.Float(), nullable=True),
    sa.Column('admin_salary', sa.Float(), nullable=True),
    sa.Column('marketing_percentage', sa.Float(), nullable=True),
    sa.Column('infrastructure_cost_per_user', sa.Float(), nullable=True),
    sa.Column('other_expenses_percentage', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['scenario_id'], ['forecast_scenarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parameters_id'), 'parameters', ['id'], unique=False)
    op.create_table('yearly_summaries',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('scenario_id', sa.Integer(), nullable=True),
    sa.Column('year', sa.Integer(), nullable=True),
    sa.Column('income', sa.Float(), nullable=True),
    sa.Column('expenses', sa.Float(), nullable=True),
    sa.Column('ebitda', sa.Float(), nullable=True),
    sa.Column('client_count', sa.Integer(), nullable=True),
    sa.Column('paying_clients', sa.Integer(), nullable=True),
    sa.Column('developer_count', sa.Integer(), nullable=True),
    sa.Column('affiliate_count', sa.Integer(), nullable=True),
    sa.Column('sales_staff', sa.Integer(), nullable=True),
    sa.Column('jr_devs', sa.Integer(), nullable=True),
    sa.Column('admin_staff', sa.Integer(), nullable=True),
    sa.Column('cto_count', sa.Integer(), nullable=True),
    sa.Column('total_staff', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['scenario_id'], ['forecast_scenarios.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_yearly_summaries_id'), 'yearly_summaries', ['id'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_yearly_summaries_id'), table_name='yearly_summaries')
    op.drop_table('yearly_summaries')
    op.drop_index(op.f('ix_parameters_id'), table_name='parameters')
    op.drop_table('parameters')
    op.drop_index(op.f('ix_monthly_data_id'), table_name='monthly_data')
    op.drop_table('monthly_data')
    op.drop_index(op.f('ix_forecast_scenarios_name'), table_name='forecast_scenarios')
    op.drop_index(op.f('ix_forecast_scenarios_id'), table_name='forecast_scenarios')
    op.drop_table('forecast_scenarios')
    # ### end Alembic commands ###
