"""Add checkpoints

Revision ID: b5dd5e65e203
Revises: c68cf17c912c
Create Date: 2019-07-12 06:45:51.327689

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b5dd5e65e203'
down_revision = 'c68cf17c912c'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('checkpoint',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=False),
    sa.Column('date_time', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['event.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.add_column('odds', sa.Column('checkpoint_id', sa.Integer(), nullable=True))
    op.add_column('odds', sa.Column('place', sa.Float(), nullable=True))
    op.add_column('odds', sa.Column('win', sa.Float(), nullable=True))
    op.create_foreign_key(None, 'odds', 'checkpoint', ['checkpoint_id'], ['id'])
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint(None, 'odds', type_='foreignkey')
    op.drop_column('odds', 'win')
    op.drop_column('odds', 'place')
    op.drop_column('odds', 'checkpoint_id')
    op.drop_table('checkpoint')
    # ### end Alembic commands ###
