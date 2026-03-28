"""Application module for utils db utils workflows."""

import sys

from app.shared import database as _database

sys.modules[__name__] = _database
