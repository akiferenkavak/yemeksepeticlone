"""add review system

Revision ID: 04b25e455679
Revises: 81514c0864a4
Create Date: 2025-05-11 19:15:01.195621

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '04b25e455679'
down_revision = '81514c0864a4'
branch_labels = None
depends_on = None


def upgrade():
    # Sorunlu kısmı kaldırın:
    # with op.batch_alter_table('cart_item', schema=None) as batch_op:
    #     ... sorunlu kod ...
    
    # Sadece yeni tabloları oluşturun:
    op.create_table('restaurant_review',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('restaurant_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comment', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['restaurant_id'], ['restaurant.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table('menu_item_review',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('menu_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['menu_id'], ['menu.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade():
    # Remove tables
    op.drop_table('menu_item_review')
    op.drop_table('restaurant_review')