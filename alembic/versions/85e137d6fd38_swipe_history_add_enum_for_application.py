"""swipe history add enum for application

Revision ID: 85e137d6fd38
Revises: 092d8e6d1d00
Create Date: 2025-06-05 08:26:32.100431

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '85e137d6fd38'
down_revision: Union[str, None] = '092d8e6d1d00'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # op.alter_column('applications', 'action',
    #            existing_type=postgresql.ENUM('LIKE', 'DISLIKE', name='swipeaction'),
    #            server_default=None,
    #            existing_nullable=False)
    op.execute("ALTER TYPE applicationstatus ADD VALUE 'NA'")
    
    # Add NA to mltaskstatus enum
    op.execute("ALTER TYPE mltaskstatus ADD VALUE 'NA'")

    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    # op.alter_column('applications', 'action',
    #            existing_type=postgresql.ENUM('LIKE', 'DISLIKE', name='swipeaction'),
    #            server_default=sa.text("'LIKE'::swipeaction"),
    #            existing_nullable=False)
    pass
    # ### end Alembic commands ###
