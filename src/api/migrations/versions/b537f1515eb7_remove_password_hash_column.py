"""remove password_hash column

Revision ID: b537f1515eb7
Revises: 31f18de7e03e
Create Date: 2025-08-16 07:43:13.894763

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b537f1515eb7"
down_revision = "31f18de7e03e"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("user_info", schema=None) as batch_op:
        batch_op.drop_column("password_hash")


def downgrade():
    with op.batch_alter_table("user_info", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "password_hash",
                sa.String(length=255),
                nullable=False,
                comment="Hashed password",
            )
        )
