import inspect
from enum import Enum, auto
from functools import wraps
from http import HTTPStatus
from typing import Awaitable, Callable, Optional
from urllib.parse import quote, urlparse

from itsdangerous import BadSignature, TimestampSigner
from starlette.middleware.sessions import SessionMiddleware

from dyne.models import Request, Response

Callback = Callable[[str], Awaitable[object]]
Hook = Callable[[Request, Response, object], Awaitable[None]]


class AuthFailureReason(Enum):
    UNAUTHENTICATED = auto()
    UNAUTHORIZED = auto()


class LoginManager:
    USER_ID_KEY = "_user_id"

    def __init__(
        self,
        app=None,
        *,
        login_url: str | None = None,
        remember_me_cookie_name: str = "remember_me",
        remember_me_duration: int = 60 * 60 * 24 * 30,
        user_id_attribute="id",
    ):
        self.login_url = login_url
        self.remember_me_cookie_name = remember_me_cookie_name
        self.remember_me_duration = remember_me_duration
        self.user_id_attribute = user_id_attribute

        self._user_loader: Optional[Callback] = None
        self._role_loader: Optional[Callback] = None
        self._on_login: list[Hook] = []
        self._on_logout: list[Hook] = []
        self._on_failure = self.default_failure

        if app:
            self.init_app(app)

    def init_app(self, app):
        cfg = app.config
        self.secret_key = cfg.require("SECRET_KEY")

        app.state.login_manager = self

        if not app.has_middleware(SessionMiddleware):
            app.add_middleware(SessionMiddleware, secret_key=self.secret_key)

        app.add_middleware(LoginMiddleware, manager=self)

    def user_loader(self, fn: Callback):
        self._user_loader = fn
        return fn

    def get_user_roles(self, fn):
        self._role_loader = fn
        return fn

    def on_login(self, fn: Hook):
        self._on_login.append(fn)
        return fn

    def on_logout(self, fn: Hook):
        self._on_logout.append(fn)
        return fn

    def on_failure(self, fn):
        self._on_failure = fn
        return fn

    async def default_failure(
        self,
        req: Request,
        resp: Response,
        reason: AuthFailureReason,
    ):
        if reason is AuthFailureReason.UNAUTHENTICATED:
            if self.login_url:
                safe_next = quote(req.url.path)

                req.params["next"] = safe_next

                sep = "&" if "?" in self.login_url else "?"
                next_url = f"{self.login_url}{sep}next={safe_next}"

                self._apply_redirect(req, resp, self.login_url, next_url=next_url)
                return resp

            resp.status_code = HTTPStatus.UNAUTHORIZED
            resp.text = "Authentication required"
            return resp

        resp.status_code = HTTPStatus.FORBIDDEN
        resp.text = "You do not have permission to access this resource"
        return resp

    def _unsign_cookie(self, req, name):
        value = req.cookies.get(name)
        if value is None:
            return None

        signer = TimestampSigner(str(self.secret_key), salt=name)
        try:
            return signer.unsign(value, max_age=self.remember_me_duration).decode(
                "utf-8"
            )

        except BadSignature:
            return None

    async def _load_current_user(self, req: Request):
        user = getattr(req.state, "user", None)

        if user is not None:
            return user

        if not self._user_loader:
            req.state.user = None
            return None

        user_id = None

        session = getattr(req, "session", None)
        if session is not None:
            user_id = session.get(self.USER_ID_KEY)

        if not user_id:
            user_id = self._unsign_cookie(req, self.remember_me_cookie_name)

        if not user_id:
            req.state.user = None
            return None

        try:
            user = await self._user_loader(user_id)
        except Exception as e:  # noqa: F841
            user = None

        if user:
            if session is not None:
                session[self.USER_ID_KEY] = user_id
            req.state.user = user
        else:
            req.state.user = None

        return user

    def _is_safe_url(self, target: str, host: str) -> bool:
        if not target:
            return False

        if target.startswith("//"):
            return False

        ref_url = urlparse(target)
        return not ref_url.netloc or ref_url.netloc == host

    def _apply_redirect(
        self,
        req: Request,
        resp: Response,
        default_url: str,
        *,
        next_url: str | None = None,
    ):
        target_url = next_url or req.params.get("next")

        if not target_url or not self._is_safe_url(target_url, req.url.netloc):
            target_url = default_url

        resp.redirect(target_url, set_text=True, status_code=HTTPStatus.FOUND)

    async def login(
        self,
        req: Request,
        resp: Response,
        user,
        *,
        remember_me: bool = False,
        redirect_url: str = "/",
    ):
        attr = self.user_id_attribute
        user_id = getattr(user, attr, None) or (
            user.get(attr) if isinstance(user, dict) else None
        )

        if user_id is None:
            raise TypeError(f"User must have a '{attr}' attribute or key")

        user_id = str(user_id)
        req.session[self.USER_ID_KEY] = user_id
        req.state.user = user

        if remember_me:
            signer = TimestampSigner(
                str(self.secret_key), salt=self.remember_me_cookie_name
            )
            signed_user_id = signer.sign(user_id.encode("utf-8")).decode("utf-8")

            resp.set_cookie(
                self.remember_me_cookie_name,
                signed_user_id,
                path="/",
                max_age=self.remember_me_duration,
                httponly=True,
                samesite="lax",
                secure=req.url.scheme == "https",
            )

        for hook in self._on_login:
            await hook(req, resp, user)

        self._apply_redirect(req, resp, redirect_url)

    async def logout(self, req: Request, resp: Response):
        user = getattr(req.state, "user", None)

        session = getattr(req, "session", None)
        if session:
            req.session.pop(self.USER_ID_KEY, None)

        req.state.user = None

        resp.delete_cookie(
            self.remember_me_cookie_name,
            path="/",
            httponly=True,
            secure=req.url.scheme == "https",
        )

        if user:
            for hook in self._on_logout:
                await hook(req, resp, user)

    async def _authorize(self, required_role, user) -> bool:
        """
        Authorize a user against required roles.

        `required_role` semantics:
        - None → allow access
        - "admin" → user must have "admin"
        - ["admin", "editor"] → OR semantics
        - [["admin", "editor"]] → AND semantics
        """

        if required_role is None:
            return True

        if self._role_loader is None:  # pragma: no cover
            raise RuntimeError(
                "Role-based access requested but no @get_user_roles registered"
            )

        # Normalize user roles
        provided = await self._role_loader(user)

        if provided is None:
            provided_roles = set()
        elif isinstance(provided, str):
            provided_roles = {provided}
        elif isinstance(provided, (list, tuple, set)):
            provided_roles = set(provided)
        else:
            raise TypeError(
                "get_user_roles_callback must return None, str, or an iterable of roles"
            )

        # Normalize required roles into OR-groups of AND-sets
        if not isinstance(required_role, (list, tuple)):
            required_groups = [{required_role}]
        else:
            required_groups = [
                {r} if isinstance(r, str) else set(r) for r in required_role
            ]

        # Authorization check: OR over groups, AND within group
        for group in required_groups:
            if group.issubset(provided_roles):
                return True

        return False

    def login_required(self, _func=None, *, role: str | list | None = None):
        def decorator(fn):
            if not inspect.iscoroutinefunction(fn):
                raise TypeError("@login_required requires an async function")

            @wraps(fn)
            async def wrapper(*args, **kwargs):

                req = next((a for a in args if isinstance(a, Request)), None)
                resp = next((a for a in args if isinstance(a, Response)), None)

                if not req or not resp:
                    raise RuntimeError(
                        "@login_required requires Request and Response objects"
                    )

                user = await self._load_current_user(req)

                if not user:
                    return await self._on_failure(
                        req, resp, AuthFailureReason.UNAUTHENTICATED
                    )

                if role and not await self._authorize(role, user):
                    return await self._on_failure(
                        req, resp, AuthFailureReason.UNAUTHORIZED
                    )

                return await fn(*args, **kwargs)

            return wrapper

        if _func is None:
            return decorator

        return decorator(_func)


class LoginMiddleware:
    def __init__(self, app, manager: LoginManager):
        self.app = app
        self.manager = manager

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        req = Request(scope, receive)

        scope.setdefault("state", {})

        user = await self.manager._load_current_user(req)

        scope["state"]["user"] = user

        await self.app(scope, receive, send)
