"""empty message

Revision ID: 7a2a37be64
Revises: 55c54d020d8
Create Date: 2015-11-16 19:35:35.344058

"""

# revision identifiers, used by Alembic.
revision = '7a2a37be64'
down_revision = '55c54d020d8'

from alembic import op
import sqlalchemy as sa


def upgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('post',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('url', sa.Text(), nullable=False),
    sa.Column('download_url', sa.Text(), nullable=False),
    sa.Column('post_date', sa.Date(), nullable=False),
    sa.Column('title', sa.Text(), nullable=False),
    sa.Column('description', sa.Text(), nullable=True),
    sa.Column('tumblr_url', sa.Text(), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('download_url')
    )
    op.create_index(op.f('ix_post_url'), 'post', ['url'], unique=True)
    op.create_table('post_authors',
    sa.Column('post_id', sa.Integer(), nullable=False),
    sa.Column('author_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['author_id'], ['author.id'], ),
    sa.ForeignKeyConstraint(['post_id'], ['post.id'], ),
    sa.PrimaryKeyConstraint('post_id', 'author_id')
    )
    op.add_column('author', sa.Column('first_post', sa.Date(), nullable=True))
    op.drop_column('author', 'first_issue')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column('author', sa.Column('first_issue', sa.DATE(), autoincrement=False, nullable=True))
    op.drop_column('author', 'first_post')
    op.drop_table('post_authors')
    op.drop_index(op.f('ix_post_url'), table_name='post')
    op.drop_table('post')
    ### end Alembic commands ###
