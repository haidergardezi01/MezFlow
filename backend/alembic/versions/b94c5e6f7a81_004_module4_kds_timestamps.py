"""004_module4_kds_timestamps

Revision ID: b94c5e6f7a81
Revises: a83b4c91d20e
Create Date: 2026-10-22 18:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'b94c5e6f7a81'
down_revision: Union[str, None] = 'a83b4c91d20e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add KDS lifecycle timestamps to orders
    op.add_column('orders', sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('preparing_started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('ready_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('dispatched_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('orders', sa.Column('target_prep_minutes', sa.Integer(), server_default='15', nullable=True))

    # 2. Add prepared_at timestamp to order_items
    op.add_column('order_items', sa.Column('prepared_at', sa.DateTime(timezone=True), nullable=True))

    # 3. Create order_status_history table
    op.create_table(
        'order_status_history',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', UUID(as_uuid=True), sa.ForeignKey('orders.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('changed_by_user_id', UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('previous_status', sa.String(30), nullable=False),
        sa.Column('new_status', sa.String(30), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index(
        'ix_order_status_history_order_id_created_at',
        'order_status_history',
        ['order_id', 'created_at']
    )


def downgrade() -> None:
    op.drop_index('ix_order_status_history_order_id_created_at', table_name='order_status_history')
    op.drop_table('order_status_history')
    op.drop_column('order_items', 'prepared_at')
    op.drop_column('orders', 'target_prep_minutes')
    op.drop_column('orders', 'dispatched_at')
    op.drop_column('orders', 'ready_at')
    op.drop_column('orders', 'preparing_started_at')
    op.drop_column('orders', 'confirmed_at')
