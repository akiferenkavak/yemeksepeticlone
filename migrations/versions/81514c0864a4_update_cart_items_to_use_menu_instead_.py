"""update cart items to use menu instead of menu_item

Revision ID: 81514c0864a4
Revises: 0f4479c7efe7
Create Date: 2025-05-11 16:07:42.782191

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '81514c0864a4'
down_revision = '0f4479c7efe7'
branch_labels = None
depends_on = None


def upgrade():
    # Rename menu_item_id column to menu_id in cart_item table
    with op.batch_alter_table('cart_item', schema=None) as batch_op:
        batch_op.alter_column('menu_item_id', new_column_name='menu_id')
    
    # Rename menu_item_id column to menu_id in order_item table
    with op.batch_alter_table('order_item', schema=None) as batch_op:
        batch_op.alter_column('menu_item_id', new_column_name='menu_id')

def downgrade():
    # Reverse the changes
    with op.batch_alter_table('cart_item', schema=None) as batch_op:
        batch_op.alter_column('menu_id', new_column_name='menu_item_id')
    
    with op.batch_alter_table('order_item', schema=None) as batch_op:
        batch_op.alter_column('menu_id', new_column_name='menu_item_id')
