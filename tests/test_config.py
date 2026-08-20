from task_cli.config import get_settings


def test_default_settings():

    settings = get_settings()

    assert settings.database_url
