try:
    from alchemical.aio import Alchemical as AIOAlchemical
    from alchemical.aio import Model as Model
except ImportError as exc:
    raise RuntimeError(
        "Alchemical is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[sqlalchemy]\n"
    ) from exc


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

        app.add_middleware(
            AlchemicalMiddleware,
            db=self,
            autocommit=autocommit,
        )


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
