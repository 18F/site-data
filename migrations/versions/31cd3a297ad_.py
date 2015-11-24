"""empty message

Revision ID: 31cd3a297ad
Revises: 332bfcda4af
Create Date: 2015-11-24 20:11:39.264238

"""

# revision identifiers, used by Alembic.
revision = '31cd3a297ad'
down_revision = '332bfcda4af'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.drop_column('event', 'commit_id')
    op.add_column('event', sa.Column('commit_id', sa.String(), nullable=True))
    pass


def downgrade():
    op.drop_column('event', 'commit_id')
    op.add_column('event', sa.Column('commit_id', sa.Integer(), nullable=True))
    pass
