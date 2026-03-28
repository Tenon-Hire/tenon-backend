"""Application module for utils perf utils workflows."""

import sys

from app.shared import perf as _perf

sys.modules[__name__] = _perf
