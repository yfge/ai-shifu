"""add active type

Revision ID: f2bda1a75fe9
Revises: bed6fe23f09b
Create Date: 2024-12-24 07:42:45.926757

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f2bda1a75fe9"
down_revision = "bed6fe23f09b"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("active", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "active_join_type",
                sa.Integer(),
                nullable=False,
                comment="Active join type",
            )
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("active", schema=None) as batch_op:
        batch_op.drop_column("active_join_type")

    # ### end Alembic commands ###