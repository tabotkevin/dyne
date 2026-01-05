from http import HTTPStatus

import httpx

from dyne.ext.auth import authenticate
from dyne.ext.auth.backends import BasicAuth, DigestAuth, MultiAuth, TokenAuth

users = dict(john="password", admin="password123")
roles = {"john": "user", "admin": ["user", "admin"]}

# Setup Authentication backends
basic_auth = BasicAuth()
token_auth = TokenAuth()
digest_auth = DigestAuth()
multi_auth = MultiAuth(digest_auth, token_auth, basic_auth)


@basic_auth.verify_password
async def verify_password(username, password):
    if username in users and users.get(username) == password:
        return username
    return None


@basic_auth.error_handler
async def basic_error_handler(req, resp, status_code=HTTPStatus.UNAUTHORIZED):
    resp.text = "Basic Custom Error"
    resp.status_code = status_code


@token_auth.verify_token
async def verify_token(token):
    if token == "valid_token":
        return "admin"
    return None


@token_auth.error_handler
async def token_error_handler(req, resp, status_code=HTTPStatus.UNAUTHORIZED):
    resp.text = "Token Custom Error"
    resp.status_code = status_code


@digest_auth.get_password
async def get_password(username):
    return users.get(username)


@digest_auth.error_handler
async def digest_error_handler(req, resp, status_code=HTTPStatus.UNAUTHORIZED):
    resp.text = "Digest Custom Error"
    resp.status_code = status_code


# Set roles for Basic Auth
@basic_auth.get_user_roles
async def get_user_roles(user):
    return roles.get(user)


# Basic Auth tests
def test_basic_auth(app):

    @app.route("/{greeting}")
    @authenticate(basic_auth)
    async def basic_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

    # Test success
    response = app.client.get("http://;/Hello", auth=("john", "password"))
    assert response.status_code == HTTPStatus.OK
    assert response.text == "Hello, john!"

    # Test failure
    response = app.client.get("http://;/Hello", auth=("john", "wrong_password"))
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.text == "Basic Custom Error"


# Token Auth tests
def test_token_auth(app):

    @app.route("/{greeting}")
    @authenticate(token_auth)
    async def token_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

    # Test success
    headers = {"Authorization": "Bearer valid_token"}
    response = app.client.get("http://;/Hi", headers=headers)
    assert response.status_code == HTTPStatus.OK
    assert response.text == "Hi, admin!"

    # Test failure
    headers = {"Authorization": "Bearer invalid_token"}
    response = app.client.get("http://;/Hi", headers=headers)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.text == "Token Custom Error"


# Digest Auth tests
def test_digest_auth(app):
    @app.route("/{greeting}")
    @authenticate(digest_auth)
    async def digest_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

    # Test success
    response = app.client.get(
        "http://;/Hola", auth=httpx.DigestAuth("john", "password")
    )
    assert response.status_code == HTTPStatus.OK
    assert response.text == "Hola, john!"

    # Test failure
    response = app.client.get(
        "http://;/Hola", auth=httpx.DigestAuth("john", "wrong_password")
    )
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.text == "Digest Custom Error"


# Role-based authorization tests
def test_role_user(app):
    @app.route("/welcome")
    @authenticate(basic_auth, role="user")
    async def welcome(req, resp):
        resp.text = f"welcome back {req.state.user}!"

    @app.route("/admin")
    @authenticate(basic_auth, role="admin")
    async def admin(req, resp):
        resp.text = f"Hello {req.state.user}, you are an admin!"

    # Test success
    response = app.client.get("http://;/welcome", auth=("john", "password"))
    assert response.status_code == HTTPStatus.OK
    assert response.text == "welcome back john!"

    # Test user role failure
    response = app.client.get("http://;/admin", auth=("john", "password"))
    assert response.status_code == HTTPStatus.FORBIDDEN

    # Test admin role success
    response = app.client.get("http://;/admin", auth=("admin", "password123"))
    assert response.status_code == HTTPStatus.OK
    assert response.text == "Hello admin, you are an admin!"


# MultiAuth tests
def test_multi_auth_basic_success(app):
    @app.route("/multi/{greeting}")
    @authenticate(multi_auth)
    async def multi_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

    # Test Basic Auth success
    response = app.client.get("http://;/multi/Hi", auth=("john", "password"))
    assert response.status_code == HTTPStatus.OK
    assert response.text == "Hi, john!"

    # Test Token Auth success
    headers = {"Authorization": "Bearer valid_token"}
    response = app.client.get("http://;/multi/Hi", headers=headers)
    assert response.status_code == HTTPStatus.OK
    assert response.text == "Hi, admin!"

    # Test Digest success
    response = app.client.get(
        "http://;/multi/Hi", auth=httpx.DigestAuth("john", "password")
    )
    assert response.status_code == HTTPStatus.OK
    assert response.text == "Hi, john!"
