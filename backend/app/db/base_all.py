"""Import this module (not app.db.base) wherever the full mapped schema needs to be
registered on Base.metadata — Alembic autogenerate and test bootstrapping.
"""

from app.db.base import Base
from app.models import *  # noqa: F401,F403
