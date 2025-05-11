"""add category to menu items

Revision ID: manual_add_category
Revises: 04b25e455679
Create Date: 2025-05-11 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'manual_add_category'
down_revision = '04b25e455679'
branch_labels = None
depends_on = None

def upgrade():
    # Use direct SQL for SQLite since it has limitations with ALTER TABLE
    op.execute('ALTER TABLE menu ADD COLUMN category VARCHAR(50) NOT NULL DEFAULT "Diğer"')

def downgrade():
    # SQLite doesn't support dropping columns without recreating the table
    # This is a simplified downgrade that just leaves the column in place
    pass