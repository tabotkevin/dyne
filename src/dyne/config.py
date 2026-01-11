import os
import warnings
from importlib import import_module
from pathlib import Path
from typing import Any, Callable, MutableMapping, Optional, TypeVar, Union

T = TypeVar("T")


class Config(dict):
    def __init__(
        self,
        env_file: str | Path | None = None,
        environ: MutableMapping[str, str] = os.environ,
        env_prefix: str = "",
        encoding: str = "utf-8",
    ) -> None:
        super().__init__()
        self._environ = environ
        self._env_prefix = env_prefix
        self._encoding = encoding

        if env_file is not None:
            if not os.path.isfile(env_file):
                warnings.warn(f"Config file '{env_file}' not found.")
            else:
                self._read_file(env_file)
        else:
            default_env = os.path.join(os.getcwd(), ".env")
            if os.path.isfile(default_env):
                self._read_file(default_env)

    def _read_file(self, file_name: Union[str, Path]) -> None:
        with open(file_name, encoding=self._encoding) as input_file:
            for line in input_file:
                line = line.strip()
                if "=" in line and not line.startswith("#"):
                    key, value = line.split("=", 1)
                    self[key.strip()] = value.strip().strip("\"'")

    def from_object(self, obj: Any) -> None:
        if isinstance(obj, str):
            obj = import_module(obj)
        for key in dir(obj):
            if key.isupper():
                self[key] = getattr(obj, key)

    def get(
        self, key: str, cast: Callable[[Any], T] | None = None, default: Any = None
    ) -> Any:
        """
        The prioritized getter:
        1. Checks self._environ (OS environment)
        2. Checks internal dict (Values from .env or from_object)
        3. Returns default
        """
        full_key = self._env_prefix + key

        if full_key in self._environ:
            value = self._environ[full_key]
            return self._perform_cast(full_key, value, cast)

        if key in self:
            value = self[key]
            return self._perform_cast(key, value, cast)

        if default is not None:
            return self._perform_cast(key, default, cast)

        return default

    def require(self, key: str, cast: Callable[[Any], T] | None = None) -> Any:
        value = self.get(key, cast)
        if value is None:
            raise RuntimeError(f"Missing required config: {key}")
        return value

    def _perform_cast(
        self, key: str, value: Any, cast: Optional[Callable] = None
    ) -> Any:
        if cast is None or value is None:
            return value

        if cast is bool and isinstance(value, str):
            mapping = {"true": True, "1": True, "false": False, "0": False}
            value = value.lower()
            if value not in mapping:
                raise ValueError(
                    f"Config '{key}' has value '{value}'. Not a valid bool."
                )
            return mapping[value]

        try:
            return cast(value)
        except (TypeError, ValueError):
            raise ValueError(
                f"Config '{key}' has value '{value}'. Not a valid {cast.__name__}."
            )

    def __getattr__(self, key: str) -> Any:
        value = self.get(key)
        if value is None:
            raise AttributeError(f"Config has no attribute '{key}'")
        return value
