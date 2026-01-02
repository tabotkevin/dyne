import pytest

from dyne import App
from dyne.config import Config


class DevConfig:
    DEBUG = True
    PORT = 8000
    DATABASE_URL = "sqlite:///dev.db"
    secret_key = "should_not_load"


def test_attribute_access():
    config = Config()
    config["FOO"] = "bar"
    assert config.FOO == "bar"


def test_from_object():
    config = Config()
    config.from_object(DevConfig)

    assert config.DEBUG is True
    assert config.PORT == 8000
    assert config.DATABASE_URL == "sqlite:///dev.db"

    # Lowercase should not be accessible via attribute
    with pytest.raises(AttributeError):
        _ = config.secret_key


def test_environ_override_priority(monkeypatch):
    """
    Test the 'Hierarchy of Truth':
    OS Environment MUST override internal dictionary values.
    """
    config = Config()
    config.from_object(DevConfig)
    assert config.DATABASE_URL == "sqlite:///dev.db"

    # Mock an OS environment variable
    monkeypatch.setenv("DATABASE_URL", "postgresql://user@localhost/prod")

    # Verify override
    assert config.DATABASE_URL == "postgresql://user@localhost/prod"


def test_type_casting_int():
    config = Config()
    config["MAX_CONNECTIONS"] = "100"

    val = config.get("MAX_CONNECTIONS", cast=int)
    assert val == 100
    assert isinstance(val, int)


def test_type_casting_bool():
    config = Config()

    config["ENABLED"] = "true"
    assert config.get("ENABLED", cast=bool) is True
    config["ENABLED"] = "1"
    assert config.get("ENABLED", cast=bool) is True

    config["ENABLED"] = "false"
    assert config.get("ENABLED", cast=bool) is False
    config["ENABLED"] = "0"
    assert config.get("ENABLED", cast=bool) is False


def test_env_prefix(monkeypatch):
    monkeypatch.setenv("DYNE_PORT", "9000")
    monkeypatch.setenv("PORT", "8000")

    config = Config(env_prefix="DYNE_")

    # Should pick up the prefixed version
    assert config.get("PORT", cast=int) == 9000


def test_missing_key_errors():
    config = Config()

    with pytest.raises(AttributeError):
        _ = config.NON_EXISTENT

    # .get() without default should raise KeyError
    with pytest.raises(KeyError):
        config.get("NON_EXISTENT")


def test_from_env_file(tmp_path):
    d = tmp_path / "subdir"
    d.mkdir()
    env_file = d / ".env"
    env_file.write_text("API_KEY=12345\nDEBUG=false")

    config = Config(env_file=env_file)

    assert config.API_KEY == "12345"
    assert config.get("DEBUG", cast=bool) is False


def test_automatic_dotenv_discovery(tmp_path, monkeypatch):
    """
    Verify that Dyne automatically finds and loads a .env file
    in the current working directory when no file is specified.
    """
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()
    env_file = project_dir / ".env"
    env_file.write_text("DB_NAME=auto_discovered_db\nDEBUG=true")

    monkeypatch.chdir(project_dir)

    app = App()

    assert app.config.DB_NAME == "auto_discovered_db"
    assert app.config.get("DEBUG", cast=bool) is True


def test_explicit_file_overrides_default_discovery(tmp_path, monkeypatch):
    """
    Verify that if a user provides an explicit env_file,
    the default .env in CWD is ignored.
    """
    project_dir = tmp_path / "my_project"
    project_dir.mkdir()

    # Default file
    (project_dir / ".env").write_text("KEY=default")

    # Custom file
    custom_file = project_dir / ".env.prod"
    custom_file.write_text("KEY=production")

    monkeypatch.chdir(project_dir)

    app = App(env_file=".env.prod")

    # Should load from .env.prod, NOT .env
    assert app.config.KEY == "production"


def test_custom_environ_injection():
    custom_env = {"APP_KEY": "secret-from-mock-env"}
    config = Config(environ=custom_env)

    assert config.get("APP_KEY") == "secret-from-mock-env"

    # Verify it doesn't leak/read from actual os.environ if not in custom_env
    with pytest.raises(KeyError):
        config.get("PATH")  # Standard OS var should be missing here


def test_encoding_support(tmp_path):
    env_file = tmp_path / ".env"
    content = 'UTF_VAR="I am encoded"'

    env_file.write_text(content, encoding="utf-16")

    config = Config(env_file=env_file, encoding="utf-16")
    assert config.UTF_VAR == "I am encoded"


def test_from_object_lowercase_ignored():

    class MixedConfig:
        UPPER = "load me"
        lower = "ignore me"

    config = Config()
    config.from_object(MixedConfig)

    assert config.UPPER == "load me"
    with pytest.raises(AttributeError):
        _ = config.lower


def test_missing_env_file_warning():
    with pytest.warns(UserWarning, match="Config file 'missing.env' not found"):
        Config(env_file="missing.env")


def test_default_to_os_environ(monkeypatch):
    """
    Ensure that even without a file or object or .env,
    Config reads directly from os.environ.
    """
    monkeypatch.setenv("PORT", "9000")

    config = Config()

    assert config.PORT == "9000"
    assert config.get("PORT", cast=int) == 9000


def test_empty_config_error():
    config = Config()

    with pytest.raises(AttributeError):
        _ = config.THIS_DOES_NOT_EXIST


def test_app_initialization_passes_params():
    app = App(env_prefix="TEST_")

    assert app.config._env_prefix == "TEST_"


def test_config_access_in_routes(monkeypatch):
    monkeypatch.setenv("APP_NAME", "DyneTestApp")

    app = App()

    @app.route("/config-check")
    async def get_config(req, resp):
        app_name = req.app.config.APP_NAME
        resp.media = {"value": app_name}

    assert app.config.APP_NAME == "DyneTestApp"


def test_app_environ_injection():
    custom_environ = {"DATABASE_URL": "sqlite:///:memory:"}
    app = App(environ=custom_environ)

    assert app.config.DATABASE_URL == "sqlite:///:memory:"


def test_attribute_error_on_app_config():
    app = App()

    with pytest.raises(AttributeError) as excinfo:
        _ = app.config.NON_EXISTENT_KEY

    assert "Config has no attribute 'NON_EXISTENT_KEY'" in str(excinfo.value)
