"""add account settings

Revision ID: 6e4c2a91d8f7
Revises: f32c40eab45c
Create Date: 2026-09-12 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa


revision = "6e4c2a91d8f7"
down_revision = "f32c40eab45c"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("theme_mode", sa.String(length=10), nullable=False, server_default="dark")
        )
        batch_op.add_column(
            sa.Column("accent_colour", sa.String(length=10), nullable=False, server_default="red")
        )
        batch_op.add_column(
            sa.Column("max_level_charisma", sa.Boolean(), nullable=False, server_default="0")
        )


def downgrade():
    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.drop_column("max_level_charisma")
        batch_op.drop_column("accent_colour")
        batch_op.drop_column("theme_mode")
