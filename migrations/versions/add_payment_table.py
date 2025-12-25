"""add_payment_table

Revision ID: add_payment_table
Revises: change_username_to_email
Create Date: 2025-12-25 XX:XX:XX.XXXXXX

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_payment_table'
down_revision: Union[str, Sequence[str], None] = 'change_username_to_email'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add payment table and update parking_records."""
    # Payment tablosunu oluştur
    op.create_table('payments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('reference', sa.String(length=64), nullable=False),
        sa.Column('amount', sa.Float(), nullable=False),
        sa.Column('currency', sa.String(length=3), nullable=False),
        sa.Column('status', sa.Enum('PENDING', 'PAID', 'CANCELLED', name='paymentstatus'), nullable=False),
        sa.Column('parking_record_id', sa.Integer(), nullable=True),
        sa.Column('receiver_name', sa.String(length=255), nullable=False),
        sa.Column('iban', sa.String(length=34), nullable=False),
        sa.Column('merchant_code', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('paid_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_payments_id'), 'payments', ['id'], unique=False)
    op.create_index(op.f('ix_payments_reference'), 'payments', ['reference'], unique=True)
    op.create_index(op.f('ix_payments_status'), 'payments', ['status'], unique=False)
    op.create_index(op.f('ix_payments_parking_record_id'), 'payments', ['parking_record_id'], unique=False)
    
    # parking_records tablosuna payment_id sütunu ekle
    op.add_column('parking_records', sa.Column('payment_id', sa.Integer(), nullable=True))
    op.create_index(op.f('ix_parking_records_payment_id'), 'parking_records', ['payment_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema - remove payment table."""
    op.drop_index(op.f('ix_parking_records_payment_id'), table_name='parking_records')
    op.drop_column('parking_records', 'payment_id')
    op.drop_index(op.f('ix_payments_parking_record_id'), table_name='payments')
    op.drop_index(op.f('ix_payments_status'), table_name='payments')
    op.drop_index(op.f('ix_payments_reference'), table_name='payments')
    op.drop_index(op.f('ix_payments_id'), table_name='payments')
    op.drop_table('payments')
    # Enum'ı sil
    sa.Enum(name='paymentstatus').drop(op.get_bind(), checkfirst=True)


