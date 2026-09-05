"""001_initial_domain_schema

Revision ID: 001_initial
Revises: 
Create Date: 2025-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # merchants
    if 'merchants' not in existing_tables:
        op.create_table(
            'merchants',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('name', sa.String(length=255), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('max_recovery_attempts', sa.Integer(), nullable=False, server_default='3'),
            sa.Column('max_customer_contacts', sa.Integer(), nullable=False, server_default='2'),
            sa.Column('min_confidence_threshold', sa.Float(), nullable=False, server_default='0.65'),
            sa.Column('auto_execute_below_amount', sa.BigInteger(), nullable=False, server_default='50000'),
            sa.Column('requires_approval_above', sa.BigInteger(), nullable=False, server_default='500000'),
            sa.PrimaryKeyConstraint('id')
        )

    # customers
    if 'customers' not in existing_tables:
        op.create_table(
            'customers',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('merchant_id', sa.String(length=64), nullable=False),
            sa.Column('email', sa.String(length=255), nullable=True),
            sa.Column('phone', sa.String(length=32), nullable=True),
            sa.Column('opted_out', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('total_payments', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('successful_payments', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('failed_payments', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('average_order_value', sa.Float(), nullable=True),
            sa.Column('last_payment_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('successful_methods', sa.String(length=255), nullable=True),
            sa.Column('dataset_split', sa.String(length=16), nullable=False, server_default='train'),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_customers_merchant_id', 'customers', ['merchant_id'])

    # orders
    if 'orders' not in existing_tables:
        op.create_table(
            'orders',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('merchant_id', sa.String(length=64), nullable=False),
            sa.Column('customer_id', sa.String(length=64), nullable=False),
            sa.Column('amount', sa.BigInteger(), nullable=False),
            sa.Column('currency', sa.String(length=8), nullable=False, server_default='INR'),
            sa.Column('category', sa.String(length=64), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('razorpay_order_id', sa.String(length=64), nullable=True),
            sa.Column('dataset_split', sa.String(length=16), nullable=False, server_default='train'),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
            sa.ForeignKeyConstraint(['merchant_id'], ['merchants.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('razorpay_order_id')
        )
        op.create_index('idx_orders_customer_id', 'orders', ['customer_id'])
        op.create_index('idx_orders_merchant_id', 'orders', ['merchant_id'])
        op.create_index('idx_orders_created_at', 'orders', ['created_at'])

    # payments
    if 'payments' not in existing_tables:
        op.create_table(
            'payments',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('order_id', sa.String(length=64), nullable=True),
            sa.Column('customer_id', sa.String(length=64), nullable=False),
            sa.Column('merchant_id', sa.String(length=64), nullable=False),
            sa.Column('amount', sa.BigInteger(), nullable=False),
            sa.Column('currency', sa.String(length=8), nullable=False, server_default='INR'),
            sa.Column('method', sa.String(length=32), nullable=True),
            sa.Column('status', sa.String(length=32), nullable=False),
            sa.Column('error_source', sa.String(length=64), nullable=True),
            sa.Column('error_step', sa.String(length=64), nullable=True),
            sa.Column('error_reason', sa.String(length=128), nullable=True),
            sa.Column('error_code', sa.String(length=64), nullable=True),
            sa.Column('error_description', sa.Text(), nullable=True),
            sa.Column('razorpay_payment_id', sa.String(length=64), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('captured_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
            sa.Column('dataset_split', sa.String(length=16), nullable=False, server_default='train'),
            sa.ForeignKeyConstraint(['customer_id'], ['customers.id']),
            sa.ForeignKeyConstraint(['order_id'], ['orders.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('razorpay_payment_id')
        )
        op.create_index('idx_payments_customer_id', 'payments', ['customer_id'])
        op.create_index('idx_payments_order_id', 'payments', ['order_id'])
        op.create_index('idx_payments_merchant_id', 'payments', ['merchant_id'])
        op.create_index('idx_payments_status', 'payments', ['status'])
        op.create_index('idx_payments_created_at', 'payments', ['created_at'])

    # recovery_opportunities
    if 'recovery_opportunities' not in existing_tables:
        op.create_table(
            'recovery_opportunities',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('payment_id', sa.String(length=64), nullable=False),
            sa.Column('merchant_id', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=32), nullable=False, server_default='open'),
            sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('amount_at_risk', sa.BigInteger(), nullable=False),
            sa.Column('recovered_amount', sa.BigInteger(), nullable=True),
            sa.Column('dataset_split', sa.String(length=16), nullable=False, server_default='train'),
            sa.ForeignKeyConstraint(['payment_id'], ['payments.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('payment_id')
        )
        op.create_index('idx_opportunities_merchant_id', 'recovery_opportunities', ['merchant_id'])
        op.create_index('idx_opportunities_status', 'recovery_opportunities', ['status'])
        op.create_index('idx_opportunities_detected_at', 'recovery_opportunities', ['detected_at'])

    # agent_decisions
    if 'agent_decisions' not in existing_tables:
        op.create_table(
            'agent_decisions',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('opportunity_id', sa.String(length=64), nullable=False),
            sa.Column('candidate_actions_json', sa.Text(), nullable=True),
            sa.Column('selected_action', sa.String(length=64), nullable=True),
            sa.Column('confidence', sa.Float(), nullable=True),
            sa.Column('expected_recovery_value', sa.Float(), nullable=True),
            sa.Column('guardrail_passed', sa.Boolean(), nullable=False, server_default='1'),
            sa.Column('guardrail_block_reason', sa.Text(), nullable=True),
            sa.Column('requires_approval', sa.Boolean(), nullable=False, server_default='0'),
            sa.Column('approval_status', sa.String(length=32), nullable=True),
            sa.Column('approved_by', sa.String(length=128), nullable=True),
            sa.Column('diagnosis_summary', sa.Text(), nullable=True),
            sa.Column('diagnosis_failure_category', sa.String(length=64), nullable=True),
            sa.Column('diagnosis_confidence', sa.String(length=32), nullable=True),
            sa.Column('rationale', sa.Text(), nullable=True),
            sa.Column('decided_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['opportunity_id'], ['recovery_opportunities.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_decisions_opportunity_id', 'agent_decisions', ['opportunity_id'])

    # recovery_actions
    if 'recovery_actions' not in existing_tables:
        op.create_table(
            'recovery_actions',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('opportunity_id', sa.String(length=64), nullable=False),
            sa.Column('decision_id', sa.String(length=64), nullable=True),
            sa.Column('strategy', sa.String(length=64), nullable=False),
            sa.Column('status', sa.String(length=32), nullable=False, server_default='pending'),
            sa.Column('external_reference_id', sa.String(length=128), nullable=True),
            sa.Column('external_reference_url', sa.Text(), nullable=True),
            sa.Column('parameters_json', sa.Text(), nullable=True),
            sa.Column('idempotency_key', sa.String(length=128), nullable=True),
            sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['decision_id'], ['agent_decisions.id']),
            sa.ForeignKeyConstraint(['opportunity_id'], ['recovery_opportunities.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('idempotency_key')
        )
        op.create_index('idx_actions_opportunity_id', 'recovery_actions', ['opportunity_id'])

    # recovery_outcomes
    if 'recovery_outcomes' not in existing_tables:
        op.create_table(
            'recovery_outcomes',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('action_id', sa.String(length=64), nullable=False),
            sa.Column('success', sa.Boolean(), nullable=False),
            sa.Column('recovered_amount', sa.BigInteger(), nullable=True),
            sa.Column('time_to_recovery_seconds', sa.Integer(), nullable=True),
            sa.Column('confirming_event_id', sa.String(length=128), nullable=True),
            sa.Column('confirming_payment_id', sa.String(length=64), nullable=True),
            sa.Column('observed_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['action_id'], ['recovery_actions.id']),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('action_id')
        )
        op.create_index('idx_outcomes_action_id', 'recovery_outcomes', ['action_id'])

    # audit_events
    if 'audit_events' not in existing_tables:
        op.create_table(
            'audit_events',
            sa.Column('id', sa.String(length=64), nullable=False),
            sa.Column('entity_type', sa.String(length=64), nullable=False),
            sa.Column('entity_id', sa.String(length=64), nullable=False),
            sa.Column('event_type', sa.String(length=128), nullable=False),
            sa.Column('detail', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('idx_audit_entity_id', 'audit_events', ['entity_id'])
        op.create_index('idx_audit_created_at', 'audit_events', ['created_at'])


def downgrade() -> None:
    op.drop_table('audit_events')
    op.drop_table('recovery_outcomes')
    op.drop_table('recovery_actions')
    op.drop_table('agent_decisions')
    op.drop_table('recovery_opportunities')
    op.drop_table('payments')
    op.drop_table('orders')
    op.drop_table('customers')
    op.drop_table('merchants')
