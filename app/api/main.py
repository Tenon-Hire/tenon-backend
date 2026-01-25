from app.api.app_builder import create_app
from app.api.app_meta import _env_name, _parse_csv
from app.api.lifespan import lifespan
from app.infra.db import init_db_if_needed

app = create_app()

__all__ = ["app", "create_app", "lifespan", "_parse_csv", "_env_name", "init_db_if_needed"]
