from datetime import datetime
from http import HTTPStatus
from types import SimpleNamespace

import dyne
from dyne.exceptions import abort
from dyne.ext.auth import AuthFailureReason, LoginManager


class Config:
    SECRET_KEY = "Some very strong key"


app = dyne.App(debug=True)
app.config.from_object(Config)
auth = LoginManager(app, login_url="/login")

# --- Mock User Database ---
USERS = {
    "1": SimpleNamespace(id=1, username="admin", roles=["admin"]),
    "2": SimpleNamespace(id=2, username="editor", roles=["editor"]),
}


@auth.user_loader
async def load_user(user_id):
    return USERS.get(str(user_id))


@auth.get_user_roles
async def get_roles(user):
    return user.roles


@app.route("/login", methods=["GET", "POST"])
async def login(req, resp):
    if req.method == "post":
        data = await req.media()
        user_id = data.get("user_id")
        remember_me = data.get("remember_me")
        user = USERS.get(user_id)
        if user:
            await auth.login(
                req, resp, user, remember_me=remember_me, redirect_url="/dashboard"
            )
        else:
            abort(401, "Invalid Credentials")
    else:
        resp.text = "Please POST to /login with {'user_id': '1'}"


@app.route("/logout")
async def logout(req, resp):
    await auth.logout(req, resp)
    resp.text = "Logged out successfully"


@app.route("/profile")
@auth.login_required
async def profile(req, resp):
    user = req.state.user
    resp.media = {"message": f"Hello, {user.username}!"}


@app.route("/admin")
@auth.login_required(role="admin")
async def admin_only(req, resp):
    resp.text = "Welcome to the Secret Admin Panel"


@app.route("/restricted")
@auth.login_required(role=[["admin", "editor"]])  # Requires BOTH
async def double_auth(req, resp):
    resp.text = "You have both roles!"


@app.route("/dashboard")
@auth.login_required
async def dashboard(req, resp):
    resp.media = {"user": req.state.user.id}


@app.route("/settings")
@auth.login_required(role="editor")
async def settings(req, resp):
    resp.text = "Editor Settings"


@auth.on_login
async def handle_after_login(req, resp, user):
    user.last_login_at = datetime.utcnow()
    print(f"User {user} logged in at {user.last_login_at }")


@auth.on_logout
async def handle_after_logout(req, resp, user):
    print(f"User {user.username} (ID: {user.id}) logged out.")


@auth.on_failure
async def custom_auth_failure(req, resp, reason):

    if reason == AuthFailureReason.UNAUTHENTICATED:
        resp.status_code = HTTPStatus.UNAUTHORIZED
        resp.media = {"error": "Authentication required", "code": "AUTH_REQUIRED"}

    if reason == AuthFailureReason.UNAUTHORIZED:
        resp.status_code = HTTPStatus.FORBIDDEN
        resp.media = {
            "error": "Insufficient permissions",
            "required_roles": "admin",
        }

        resp.status_code = HTTPStatus.FORBIDDEN
        resp.text = "<h1>403 - Forbidden</h1><p>You do not have permission to view this page.</p>"
    await auth.default_failure(req, resp, reason)


# Should redirect to /login?next=/profile (Status 302/FOUND)
r = app.client.get("http://127.0.0.1:5042/profile", follow_redirects=False)

assert r.status_code == 302
assert r.headers["Location"] == "/login?next=/profile"

r = app.client.get("http://127.0.0.1:5042/login")
assert r.text == "Please POST to /login with {'user_id': '1'}"

r = app.client.post(
    "http://127.0.0.1:5042/login",
    json={"user_id": "1", "remember_me": True},
    follow_redirects=False,
)
assert r.status_code == 302
assert r.headers["Location"] == "/dashboard"

assert "remember_me" in app.client.cookies

# Access profile with the session cookie automatically sent
r = app.client.get("http://127.0.0.1:5042/profile", follow_redirects=True)

assert r.status_code == 200
assert r.json()["message"] == "Hello, admin!"

# Accessing admin as an Admin user (User ID 1)
r = app.client.get("http://127.0.0.1:5042/admin")
assert r.status_code == 200
assert "Secret Admin Panel" in r.text

# Login as a non-admin user (User ID 2)
app.client.post(
    "http://127.0.0.1:5042/login", json={"user_id": "2", "remember_me": True}
)

# Accessing admin as an Editor (Should be Forbidden)
r = app.client.get("http://127.0.0.1:5042/admin")
assert r.status_code == 403
assert "You do not have permission" in r.text

# Perform Logout
r = app.client.get("http://127.0.0.1:5042/logout")
assert r.status_code == 200
assert r.text == "Logged out successfully"

r = app.client.get("http://127.0.0.1:5042/profile", follow_redirects=False)

assert r.status_code == 302
assert r.headers["Location"] == "/login?next=/profile"

r_followed = app.client.get("http://127.0.0.1:5042/profile", follow_redirects=True)
assert r_followed.status_code == 200
assert "Please POST to /login" in r_followed.text
