from __future__ import annotations

import pytest

from tests.media.services.media_privacy_service_utils import *


def test_require_media_consent_rejects_missing_values():
    with pytest.raises(HTTPException) as missing_version:
        require_media_consent(
            SimpleNamespace(consent_version=None, consent_timestamp=datetime.now(UTC))
        )
    assert missing_version.value.status_code == 409

    with pytest.raises(HTTPException) as missing_timestamp:
        require_media_consent(
            SimpleNamespace(consent_version="mvp1", consent_timestamp=None)
        )
    assert missing_timestamp.value.status_code == 409
