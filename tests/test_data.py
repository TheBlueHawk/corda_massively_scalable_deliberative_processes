from pydantic import ValidationError
import pytest

from msdp_api.core.config import get_settings


def test_config_requires_required_environment_values(monkeypatch):
    get_settings.cache_clear()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_SUPERGROUP_ID", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("X_ADMIN_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_USERNAME", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        get_settings()
    assert "DATABASE_URL" in str(exc_info.value)
