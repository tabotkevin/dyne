import hashlib
import hmac

import dyne
from dyne.ext.auth import BasicAuth, DigestAuth, MultiAuth, TokenAuth

api = dyne.API()

users = dict(john="password", admin="password123")

roles = {"john": "user", "admin": ["user", "admin"]}

# Basic Auth Example
basic_auth = BasicAuth()


@basic_auth.verify_password
async def verify_password(username, password):
    if username in users and users.get(username) == password:
        return username
    return None


@basic_auth.error_handler
async def error_handler(req, resp, status_code=401):
    resp.text = "Basic Custom Error"
    resp.status_code = status_code


@api.route("/{greeting}")
@api.authenticate(basic_auth)
async def basic_greet(req, resp, *, greeting):
    resp.text = f"{greeting}, {req.state.user}!"


# Example request
# http -a john:password get http://127.0.0.1:5042/Hello


# Token Auth Example
token_auth = TokenAuth()


@token_auth.verify_token
async def verify_token(token):
    if token == "valid_token":
        return "admin"
    return None


@token_auth.error_handler
async def token_error_handler(req, resp, status_code=401):
    resp.text = "Token Custom Error"
    resp.status_code = status_code


@api.route("/{greeting}")
@api.authenticate(token_auth)
async def token_greet(req, resp, *, greeting):
    resp.text = f"{greeting}, {req.state.user}!"


#  Example request
#  http get http://127.0.0.1:5042/Hi "Authorization: Bearer valid_token"


# Digest Auth Example

digest_auth = DigestAuth()


@digest_auth.get_password
async def get_password(username):
    return users.get(username)


@digest_auth.error_handler
async def digest_error_handler(req, resp, status_code=401):
    resp.text = "Digest Custom Error"
    resp.status_code = status_code


@api.route("/{greeting}")
@api.authenticate(digest_auth)
async def digest_greet(req, resp, *, greeting):
    resp.text = f"{greeting}, {req.state.user}!"


# In case your prefer using precomputed hashes for Digest Auth set `use_ha1_pw=True`
@digest_auth.get_password
async def get_ha1_pw(username):
    password = users.get(username)
    realm = (
        "Authentication Required"  # Realm same as the realm of the DigestAuth backend
    )
    return hashlib.md5(f"{username}:{realm}:{password}".encode("utf-8")).hexdigest()


#  Example request
#  http --auth-type=digest -a john:password get http://127.0.0.1:5042/Hola


# Use this for custom nonce and opaque generation and verification
my_nonce = "37e9292aecca04bd7e834e3e983f5d4"
my_opaque = "f8bf1725d7a942c6511cc7ed38c169fo"


@digest_auth.generate_nonce
async def gen_nonce(request):
    return my_nonce


@digest_auth.verify_nonce
async def ver_nonce(request, nonce):
    return hmac.compare_digest(my_nonce, nonce)


@digest_auth.generate_opaque
async def gen_opaque(request):
    return my_opaque


@digest_auth.verify_opaque
async def ver_opaque(request, opaque):
    return hmac.compare_digest(my_opaque, opaque)


# For Role base Authorization


# Set your `get_user_roles` function
@basic_auth.get_user_roles
async def get_user_roles(user):
    return roles.get(user)


@api.route("/welcome")
@api.authenticate(basic_auth, role="user")
async def welcome(req, resp):
    resp.text = f"welcome back {req.state.user}!"


@api.route("/admin")
@api.authenticate(basic_auth, role="admin")
async def admin(req, resp):
    resp.text = f"Hello {req.state.user}, you are an admin!"


# http -a john:password get http://127.0.0.1:5042/welcome (works only on the welcome endpoint)
# http -a admin:password123 get http://127.0.0.1:5042/admin (works on both endpoints)

# Multi Auth Example

multi_auth = MultiAuth(digest_auth, token_auth, basic_auth)


@api.route("/{greeting}")
@api.authenticate(multi_auth)
async def greet_world(req, resp, *, greeting):
    resp.text = f"{greeting}, world!"


if __name__ == "__main__":
    api.run()
