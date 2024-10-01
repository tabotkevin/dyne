import hmac
import secrets
from base64 import b64decode
from functools import wraps
from hashlib import md5

from starlette.authentication import AuthenticationBackend, AuthenticationError


class Backend(AuthenticationBackend):
    def __init__(self, scheme=None, realm=None, header=None):
        self.scheme = scheme
        self.realm = realm or "Authentication Required"
        self.header = header or "Authorization"
        self.get_user_roles_callback = None

        async def default_auth_error(req, resp, status_code):
            resp.text = "Unauthorized Access"
            resp.status_code = status_code

        self.error_handler(default_auth_error)

    def get_user_roles(self, f):
        self.get_user_roles_callback = f
        return f

    async def auth_header(self, request):
        return f'{self.scheme} realm="{self.realm}"'

    def get_credentials(self, request):
        if self.header not in request.headers:
            raise AuthenticationError("No Authorization headers")

        auth = request.headers[self.header]
        try:
            scheme, credentials = auth.split(maxsplit=1)
            if scheme != self.scheme:
                raise AuthenticationError("Incorrect Authorization scheme")
            return credentials
        except ValueError:
            raise AuthenticationError("Bad Authorization headers")

    def error_handler(self, f):
        @wraps(f)
        async def decorated(req, res, *args, **kwargs):
            await f(req, res, *args, **kwargs)
            if res.status_code == 200:
                res.status_code = 401
            if "WWW-Authenticate" not in res.headers.keys():
                res.headers["WWW-Authenticate"] = await self.auth_header(req)
            return res

        self.auth_error_callback = decorated
        return decorated

    async def authorize(self, role, user):
        if role is None:
            return True
        if isinstance(role, (list, tuple)):
            roles = role
        else:
            roles = [role]
        if self.get_user_roles_callback is None:  # pragma: no cover
            raise ValueError("get_user_roles callback is not defined")
        user_roles = await self.get_user_roles_callback(user)
        if user_roles is None:
            user_roles = {}
        elif not isinstance(user_roles, (list, tuple)):
            user_roles = {user_roles}
        else:
            user_roles = set(user_roles)
        for role in roles:
            if isinstance(role, (list, tuple)):
                role = set(role)
                if role & user_roles == role:
                    return True
            elif role in user_roles:
                return True

    def login_required(self, f=None, role=None, optional=None):
        if f is not None and (
            role is not None or optional is not None
        ):  # pragma: no cover
            raise ValueError("role and optional are the only supported arguments")

        def decorator(f):
            @wraps(f)
            async def decorated(req, resp, *args, **kwargs):
                status_code = None
                try:
                    user = await self.authenticate(req)
                except AuthenticationError:
                    user = None
                if user is None:
                    status_code = 401
                    return await self.auth_error_callback(req, resp, status_code)
                elif not await self.authorize(role, user):
                    status_code = 403
                if not optional and status_code:
                    return await self.auth_error_callback(req, resp, status_code)
                req.state.user = user
                return await f(req, resp, *args, **kwargs)

            return decorated

        if f:
            return decorator(f)
        return decorator


class TokenAuth(Backend):
    def __init__(self, scheme="Bearer", realm=None, header=None):
        super(TokenAuth, self).__init__(scheme, realm, header=header)

        async def default_verify_token(token):
            return None

        self.verify_token(default_verify_token)

    def verify_token(self, f):
        self.verify_token_callback = f
        return f

    async def authenticate(self, request):
        token = self.get_credentials(request)
        user = await self.verify_token_callback(token)
        if not user:
            raise AuthenticationError("Invalid token")
        return user


class BasicAuth(Backend):
    def __init__(self, scheme="Basic", realm=None):
        super(BasicAuth, self).__init__(scheme, realm)

        async def default_verify_password(username, password):
            return None

        self.verify_password(default_verify_password)

    def verify_password(self, f):
        self.verify_password_callback = f
        return f

    async def authenticate(self, request):
        credentials = self.get_credentials(request)
        try:
            encoded_username, encoded_password = b64decode(credentials).split(b":", 1)
        except (ValueError, TypeError):
            raise AuthenticationError("Invalid basic auth credentials")
        try:
            username = encoded_username.decode("utf-8")
            password = encoded_password.decode("utf-8")
        except UnicodeDecodeError:
            username = encoded_username.decode("latin1")
            password = encoded_password.decode("latin1")

        user = await self.verify_password_callback(username, password)
        if not user:
            raise AuthenticationError("Invalid username or password")
        return user


class DigestAuth(Backend):
    def __init__(
        self, scheme="Digest", realm=None, use_ha1_pw=False, qop="auth", algorithm="MD5"
    ):
        super(DigestAuth, self).__init__(scheme, realm)
        self.use_ha1_pw = use_ha1_pw
        if isinstance(qop, str):
            self.qop = [v.strip() for v in qop.split(",")]
        else:
            self.qop = qop

        if algorithm not in ["MD5", "MD5-Sess"]:
            raise ValueError("Algorithm must be either MD5 or MD5-Sess")
        self.algorithm = algorithm

        def _randomize():
            return secrets.token_hex(16)

        async def default_get_password(username):
            return None

        async def default_generate_nonce(request):
            request.session["auth_nonce"] = _randomize()
            return request.session["auth_nonce"]

        async def default_verify_nonce(request, nonce):
            session_nonce = request.session.get("auth_nonce")
            if nonce is None or session_nonce is None:
                return False
            return hmac.compare_digest(nonce, session_nonce)

        async def default_generate_opaque(request):
            request.session["auth_opaque"] = _randomize()
            return request.session["auth_opaque"]

        async def default_verify_opaque(request, opaque):
            session_opaque = request.session.get("auth_opaque")
            if opaque is None or session_opaque is None:  # pragma: no cover
                return False
            return hmac.compare_digest(opaque, session_opaque)

        self.get_password(default_get_password)
        self.generate_nonce(default_generate_nonce)
        self.generate_opaque(default_generate_opaque)
        self.verify_nonce(default_verify_nonce)
        self.verify_opaque(default_verify_opaque)

    def get_password(self, f):
        self.get_password_callback = f
        return f

    def generate_nonce(self, f):
        self.generate_nonce_callback = f
        return f

    def verify_nonce(self, f):
        self.verify_nonce_callback = f
        return f

    def generate_opaque(self, f):
        self.generate_opaque_callback = f
        return f

    def verify_opaque(self, f):
        self.verify_opaque_callback = f
        return f

    async def get_nonce(self, request):
        return await self.generate_nonce_callback(request)

    async def get_opaque(self, request):
        return await self.generate_opaque_callback(request)

    async def auth_header(self, request):
        nonce = await self.get_nonce(request)
        opaque = await self.get_opaque(request)
        if not self.qop:
            return f'{self.scheme} realm="{self.realm}", nonce="{nonce}", opaque="{opaque}"'
        return f'{self.scheme} realm="{self.realm}", nonce="{nonce}", opaque="{opaque}", algorithm="{self.algorithm}", qop="{",".join(self.qop)}"'

    def _parse_credentials(self, credentials: str) -> dict:
        parts = credentials.split(", ")
        auth = {}
        for part in parts:
            key, value = part.split("=")
            auth[key.strip()] = value.strip('"')
        return auth

    async def authenticate(self, request):
        credentials = self.get_credentials(request)
        auth = self._parse_credentials(credentials)

        username = auth.get("username")
        nonce = auth.get("nonce")
        uri = auth.get("uri")
        response = auth.get("response")
        opaque = auth.get("opaque")
        qop = auth.get("qop")
        cnonce = auth.get("cnonce")
        nc = auth.get("nc")

        if not all((username, nonce, uri, response)):
            raise AuthenticationError("Invalid Authorization parameters")

        if not await self.verify_nonce_callback(
            request, nonce
        ) or not await self.verify_opaque_callback(request, opaque):
            raise AuthenticationError("Invalid opaque")

        if qop and qop not in self.qop:  # pragma: no cover
            raise AuthenticationError("Invalid qop")

        password = await self.get_password_callback(username)

        if self.use_ha1_pw:
            ha1 = password
        else:
            ha1 = md5(f"{username}:{self.realm}:{password}".encode("utf-8")).hexdigest()

        if self.algorithm == "MD5-Sess":
            ha1 = md5(f"{ha1}:{nonce}:{cnonce}".encode("utf-8")).hexdigest()

        ha2 = md5(f"{request.method.upper()}:{uri}".encode("utf-8")).hexdigest()

        if qop == "auth":
            a3 = f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}"

        else:
            a3 = f"{ha1}:{nonce}:{ha2}"

        expected_response = md5(a3.encode("utf-8")).hexdigest()
        if not hmac.compare_digest(expected_response, response):
            raise AuthenticationError("Invalid response")
        return username


class MultiAuth(object):
    def __init__(self, *backends):
        assert backends, "At least one backend must be provided."
        self.backends = backends

    def is_compatible(self, headers, backend):
        try:
            scheme, _ = headers.get(backend.header, "").split(None, 1)
        except ValueError:
            return False
        return scheme == backend.scheme

    def login_required(self, f=None, role=None, optional=None):
        if f is not None and (
            role is not None or optional is not None
        ):  # pragma: no cover
            raise ValueError("role and optional are the only supported arguments")

        def decorator(f):
            @wraps(f)
            async def decorated(request, response, *args, **kwargs):
                selected = self.backends[0]
                for backend in self.backends:
                    if self.is_compatible(request.headers, backend):
                        selected = backend
                        break
                return await selected.login_required(role=role, optional=optional)(f)(
                    request, response, *args, **kwargs
                )

            return decorated

        if f:
            return decorator(f)
        return decorator
