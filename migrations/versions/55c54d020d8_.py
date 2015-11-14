"""empty message

Revision ID: 55c54d020d8
Revises: 162e9eaa38a
Create Date: 2015-11-14 20:27:50.000407

"""

# revision identifiers, used by Alembic.
revision = '55c54d020d8'
down_revision = '162e9eaa38a'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('author', sa.Column('first_issue', sa.Date(), nullable=True))
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('author', 'first_issue')
    ### end Alembic commands ###
