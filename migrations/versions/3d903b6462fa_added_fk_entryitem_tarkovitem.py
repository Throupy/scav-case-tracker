"""added FK ScavCaseItem -> TarkovItem

Revision ID: 3d903b6462fa
Revises: 
Create Date: 2025-01-30 21:11:59.708086

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d903b6462fa'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('entry_item', schema=None) as batch_op:
        batch_op.create_foreign_key("fk_ScavCaseItem_tarkovitem", 'tarkov_item', ['tarkov_id'], ['tarkov_id'])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('entry_item', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')

    # ### end Alembic commands ###
