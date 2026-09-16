"""add scav-case item eligibility

Revision ID: 3f5a8c2d91e4
Revises: 6e4c2a91d8f7
Create Date: 2026-09-15 15:40:00.000000
"""

from alembic import op
import sqlalchemy as sa
from pathlib import Path


revision = "3f5a8c2d91e4"
down_revision = "6e4c2a91d8f7"
branch_labels = None
depends_on = None



def upgrade():
    with op.batch_alter_table("tarkov_item", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "scav_case_eligible",
                sa.Boolean(),
                nullable=False,
                server_default="1",
            )
        )
        batch_op.create_index(
            batch_op.f("ix_tarkov_item_scav_case_eligible"),
            ["scav_case_eligible"],
            unique=False,
        )

    connection = op.get_bind()
    # Generated preset IDs are positional and have already been observed being
    # reused for unrelated items. Non-standard IDs cannot be priced reliably.
    connection.execute(
        sa.text(
            """
            UPDATE tarkov_item
               SET scav_case_eligible = 0
             WHERE tarkov_id LIKE '707265736574%'
                OR length(tarkov_id) != 24
                OR tarkov_id GLOB '*[^0-9A-Fa-f]*'
            """
        )
    )

    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "data"
        / "scav_case_ineligible_ids_20260915.txt"
    )
    reviewed_ids = tuple(
        item_id.strip()
        for item_id in manifest_path.read_text().splitlines()
        if item_id.strip()
    )
    reviewed_update = sa.text(
        """
        UPDATE tarkov_item
           SET scav_case_eligible = 0
         WHERE tarkov_id IN :item_ids
        """
    ).bindparams(sa.bindparam("item_ids", expanding=True))
    connection.execute(reviewed_update, {"item_ids": reviewed_ids})

    # The X-17 has no stable native default preset ID and is a known base-item
    # exception that can be returned by a scav case.
    connection.execute(
        sa.text(
            """
            UPDATE tarkov_item
               SET scav_case_eligible = 1
             WHERE tarkov_id = '676176d362e0497044079f4c'
            """
        )
    )

def downgrade():
    with op.batch_alter_table("tarkov_item", schema=None) as batch_op:
        batch_op.drop_index(batch_op.f("ix_tarkov_item_scav_case_eligible"))
        batch_op.drop_column("scav_case_eligible")
