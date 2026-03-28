"""Application module for utils logging utils workflows."""

import sys

from app.shared import logging as _logging

sys.modules[__name__] = _logging
