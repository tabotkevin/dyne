import inspect
from contextvars import ContextVar
from functools import wraps
from typing import Any, Callable, Optional, Sequence, Type, TypeVar

from dyne.models import Request

try:
    from sqlalchemy import select

    from alchemical.aio import Alchemical as AIOAlchemical
    from alchemical.aio import Model as Model
except ImportError as exc:
    raise RuntimeError(
        "Alchemical is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[sqlalchemy]\n"
    ) from exc


T = TypeVar("T", bound="CRUDMixin")


_current_session_ctx = ContextVar("alchemical_session", default=None)


class CRUDMixin:
    """Async Active Record helpers for Alchemical models."""

    _session_provider: Callable[[], object] | None = None

    @classmethod
    def _get_session(cls):
        if cls._session_provider is None:
            raise RuntimeError("CRUDMixin session provider not configured")
        session = cls._session_provider()
        if session is None:
            raise RuntimeError("No active database session")
        return session

    async def save(self: T) -> T:
        session = self._get_session()
        session.add(self)
        await session.flush()

        return self

    async def patch(self: T, **kwargs) -> T:
        for key, value in kwargs.items():
            if not hasattr(self, key):
                raise AttributeError(
                    f"{self.__class__.__name__} has no attribute '{key}'"
                )
            setattr(self, key, value)
        return await self.save()

    async def destroy(self) -> None:
        session = self._get_session()
        await session.delete(self)
        await session.flush()

    @classmethod
    async def create(cls: Type[T], **kwargs) -> T:
        instance = cls(**kwargs)
        return await instance.save()

    @classmethod
    async def get(cls: Type[T], pk) -> Optional[T]:
        session = cls._get_session()
        return await session.get(cls, pk)

    @classmethod
    async def find(cls: Type[T], **kwargs) -> Optional[T]:
        session = cls._get_session()
        result = await session.scalars(select(cls).filter_by(**kwargs))
        return result.first()

    @classmethod
    async def all(cls: Type[T]) -> Sequence[T]:
        session = cls._get_session()
        result = await session.scalars(select(cls))
        return result.all()


class Alchemical(AIOAlchemical):
    def __init__(self, app=None, **kwargs):
        super().__init__(**kwargs)

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        cfg = app.config

        url = cfg.require("ALCHEMICAL_DATABASE_URL")
        binds = cfg.get("ALCHEMICAL_BINDS")
        engine_options = cfg.get("ALCHEMICAL_ENGINE_OPTIONS", default={}, cast=dict)
        autocommit = cfg.get("ALCHEMICAL_AUTOCOMMIT", default=False, cast=bool)

        self.initialize(
            url=url,
            binds=binds,
            engine_options=engine_options,
        )

        app.state.db = self

        CRUDMixin._session_provider = lambda: _current_session_ctx.get()

        app.add_middleware(
            AlchemicalMiddleware,
            db=self,
            autocommit=autocommit,
        )

    def transaction(self, f):
        if not inspect.iscoroutinefunction(f):
            raise TypeError(
                f"@transaction requires an async function, got {type(f).__name__}"
            )

        @wraps(f)
        async def wrapper(*args, **kwargs) -> Any:
            req = kwargs.get("req")
            if not isinstance(req, Request):
                for arg in args:
                    if isinstance(arg, Request):
                        req = arg
                        break

            if not req:
                raise RuntimeError(
                    f"Decorator @transaction on '{f.__name__}' could not find the request object. "
                    "Ensure 'req' is passed to the function or is the first argument."
                )

            session = await req.db

            if session.in_transaction():
                return await f(*args, **kwargs)

            async with session.begin():
                return await f(*args, **kwargs)

        return wrapper


class AlchemicalMiddleware:
    def __init__(self, app, db, autocommit=False):
        self.app = app
        self.db = db
        self.autocommit = autocommit

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        session = None

        async def get_session():
            nonlocal session
            if session is None:
                session = self.db.Session()
                _current_session_ctx.set(session)
            return session

        scope.setdefault("state", {})
        scope["state"]["db"] = get_session

        try:
            await self.app(scope, receive, send)
        except Exception:
            if session:
                await session.rollback()
            raise
        finally:
            if session:
                if self.autocommit:
                    await session.commit()
                await session.close()
