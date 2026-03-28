"""Constants for schema drift reconciliation."""

DEFAULT_TEMPLATE_KEY = "python-fastapi"
RECORDING_STATUS_CHECK_NAME = "ck_recording_assets_status"
RECORDING_STATUS_CHECK_EXPR = (
    "status IN ("
    "'uploading','uploaded','processing','ready','failed','deleted','purged'"
    ")"
)
