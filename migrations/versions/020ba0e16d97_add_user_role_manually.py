"""add user role manually

Revision ID: 020ba0e16d97
Revises: 133bb785b0bf
Create Date: 2026-03-23 02:02:04.574364

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '020ba0e16d97'
down_revision = '133bb785b0bf'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE TYPE user_role AS ENUM ('user', 'admin')")
    op.add_column('users', sa.Column('role', sa.Enum('user', 'admin', name='user_role'), nullable=False, server_default='user'))


def downgrade():
    op.drop_column('users', 'role')
    op.execute("DROP TYPE user_role")
