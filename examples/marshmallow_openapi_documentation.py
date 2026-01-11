from marshmallow import Schema, fields
from sqlalchemy import Column, Float, Integer, String

import dyne
from dyne.exceptions import abort
from dyne.ext.auth import authenticate
from dyne.ext.auth.backends import BasicAuth
from dyne.ext.db.alchemical import Alchemical, Model
from dyne.ext.io.marshmallow import expect, input, output, webhook
from dyne.ext.io.marshmallow.fields import FileField
from dyne.ext.openapi import OpenAPI

description = """
API Documentation

This module provides an interface to interact with the user management API. It allows for operations such as retrieving user information, creating new users, updating existing users, and deleting users.

Base URL:
    https://api.example.com/v1

Authentication:
    All API requests require an API key. Include your API key in the Authorization header as follows:
    Authorization: Bearer YOUR_API_KEY

For further inquiries or support, please contact support@example.com.
"""


# An SQLAlchemy model
class Book(Model):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    price = Column(Float)
    title = Column(String)
    cover = Column(String, nullable=True)


class Config:
    ALCHEMICAL_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


app = dyne.App()
app.config.from_object(Config)

db = Alchemical(app)
api = OpenAPI(app, description=description)


@app.on_event("startup")
async def setup_db():
    await db.create_all()


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
    resp.text = "Invalid credentials"
    resp.status_code = status_code


@basic_auth.get_user_roles
async def get_user_roles(user):
    return roles.get(user)


class BookSchema(Schema):
    id = fields.Integer(dump_only=True)
    price = fields.Float()
    title = fields.Str()
    cover = fields.Str()


class BookCreateSchema(Schema):
    price = fields.Float()
    title = fields.Str()
    image = FileField(allowed_extensions=["png", "jpg"], max_size=5 * 1024 * 1024)


class PriceUpdateSchema(Schema):
    price = fields.Float()


class InvalidTokenSchema(Schema):
    error = fields.String(
        dump_default="token_expired",
        metadata={"description": "The error code"},
    )
    message = fields.String(
        required=True,
        metadata={"description": "Details about the token failure"},
    )


class InsufficientPermissionsSchema(Schema):
    error = fields.String(
        dump_default="forbidden",
        metadata={"description": "Error code"},
    )
    required_role = fields.String(
        dump_default="admin",
        metadata={"description": "Role required to access this resource"},
    )


@app.route("/create", methods=["POST"])
@authenticate(basic_auth, role=["user", "admin"])
@input(BookCreateSchema, location="form")
@output(BookSchema)
@expect(
    {
        401: InvalidTokenSchema,
        403: (
            InsufficientPermissionsSchema,
            "Requires elevated administrative privileges",
        ),
    }
)
async def create(req, resp, *, data):
    """Create book"""

    image = data.pop("image")
    await image.asave(image.filename)  # image already validated for extension and size

    session = await req.db
    book = Book(**data, cover=image.filename)
    session.add(book)
    await session.commit()

    resp.obj = book


@app.route("/book/{id}", methods=["POST"])
@authenticate(basic_auth, role="user")
@output(BookSchema)
async def book(req, resp, *, id):
    """Get a book"""

    session = await req.db
    resp.obj = await session.scalar(Book.select().filter_by(id=id))


@app.route("/update-price/{id}", methods=["PATCH"])
@webhook
@authenticate(basic_auth, role="user")
@input(PriceUpdateSchema)
@output(BookSchema)
@expect(
    {
        403: "Insufficient permissions",
        404: "Book not found",
    }
)
async def update_book_price(req, resp, id, *, data):
    """Update book price."""
    session = await req.db
    book = await session.scalar(Book.select().filter_by(id=id))
    if not book:
        abort(404)

    book.price = data["price"]
    await session.commit()

    resp.obj = book


@app.route("/all", methods=["GET"])
@authenticate(basic_auth)
@output(BookSchema(many=True))
async def all_books(req, resp):
    """Get all books"""

    session = await req.db
    query = await session.scalars(Book.select())

    resp.obj = query.all()


if __name__ == "__main__":
    app.run()
