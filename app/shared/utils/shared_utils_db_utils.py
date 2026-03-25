import sys

from app.shared import database as _database

sys.modules[__name__] = _database
