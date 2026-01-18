from sqlalchemy import String, select
from sqlalchemy.orm import Mapped, mapped_column

from dyne import App
from dyne.exceptions import abort
from dyne.ext.db.alchemical import Alchemical, Model


class User(Model):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True)


app = App(debug=True)


class Config:
    ALCHEMICAL_DATABASE_URL = "sqlite+aiosqlite:///:memory:"
    ALCHEMICAL_AUTOCOMMIT = True


app.config.from_object(Config)

db = Alchemical(app)


@app.on_event("startup")
async def setup_db():
    await db.create_all()


@app.route("/health")
async def health(req, resp):
    resp.media = {"status": "ok"}


@app.route("/users")
async def list_users(req, resp):
    session = await req.db
    result = await session.execute(select(User))
    users = result.scalars().all()

    resp.media = [{"id": u.id, "username": u.username} for u in users]


@app.route("/users", methods=["POST"])
async def create_user(req, resp):
    data = await req.media()

    if "username" not in data:
        abort(400, "username required")

    user = User(username=data["username"])

    session = await req.db
    session.add(user)
    await session.commit()

    resp.status_code = 201
    resp.media = {"username": user.username, "id": user.id}


@app.route("/users/fail", methods=["POST"])
async def create_user_fail(req, resp):
    session = await req.db
    user = User(username="will_rollback")

    session.add(user)

    # Force rollback
    raise RuntimeError("boom")


@app.route("/users/manual", methods=["POST"])
async def create_user_manual(req, resp):
    session = await req.db
    user = User(username="manual")

    session.add(user)
    await session.commit()

    resp.media = {"status": "committed"}


if __name__ == "__main__":
    app.run()

r = app.client.get("http://;/health")
print(r.json())

r = app.client.post("http://;/users", data={"username": "Tabot"})
print(r.json())

r = app.client.get("http://;/all_users")
print(r.json())

r = app.client.post("http://;/users/fail")
print(r.json())

r = app.client.post("http://;/users/manual", json={"username": "Tabot"})
print(r.json())
