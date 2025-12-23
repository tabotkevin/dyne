def _annotate(f, **kwargs):
    """Utilized to store essential route details for later inclusion in the
    OpenAPI documentation of the route."""

    if not hasattr(f, "_spec"):
        f._spec = {}
    for key, value in kwargs.items():
        f._spec[key] = value


def authenticate(backend, **kwargs):
    def decorator(f):
        roles = kwargs.get("role")
        if not isinstance(roles, list):  # pragma: no cover
            roles = [roles] if roles is not None else []
        _annotate(f, backend=backend, roles=roles)
        return backend.login_required(**kwargs)(f)

    return decorator
