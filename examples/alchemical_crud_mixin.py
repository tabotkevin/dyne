from pydantic import BaseModel, ConfigDict
from pydantic.fields import Field
from sqlalchemy import Column, Float, Integer, String

import dyne
from dyne.exceptions import abort
from dyne.ext.auth import BasicAuth, authenticate
from dyne.ext.db.alchemical import Alchemical, CRUDMixin, Model
from dyne.ext.io.pydantic import expect, input, output, webhook
from dyne.ext.io.pydantic.fields import FileField
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


class Book(CRUDMixin, Model):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    price = Column(Float)
    title = Column(String)
    cover = Column(String, nullable=True)


class Config:
    ALCHEMICAL_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


app = dyne.App(debug=True)

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


class BookSchema(BaseModel):
    id: int | None = None
    price: float
    title: str
    cover: str | None

    model_config = ConfigDict(from_attributes=True)


class Image(FileField):
    max_size = 5 * 1024 * 1024
    allowed_extensions = {"jpg", "jpeg", "png"}


class BookCreateSchema(BaseModel):
    price: float
    title: str
    image: Image

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True,  # Crucial for custom classes like FileField
    )


class PriceUpdateSchema(BaseModel):
    price: float


class InvalidTokenSchema(BaseModel):
    error: str = Field("token_expired", description="The error code")
    message: str = Field(..., description="Details about the token failure")


class InsufficientPermissionsSchema(BaseModel):
    error: str = "forbidden"
    required_role: str = "admin"


@app.route("/create", methods=["POST"])
@authenticate(basic_auth, role="user")
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
@db.transaction
async def create(req, resp, *, data):
    """Create book"""

    image = data.pop("image")
    await image.asave(image.filename)

    book = await Book.create(**data, cover=image.filename)

    resp.obj = book


@app.route("/no_trans_create", methods=["POST"])
@authenticate(basic_auth, role="user")
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
async def no_transaction_create(req, resp, *, data):
    """Create book no transaction"""

    image = data.pop("image")
    await image.asave(image.filename)

    session = await req.db
    book = await Book.create(**data, cover=image.filename)
    await session.commit()

    resp.obj = book


@app.route("/book/{id}", methods=["GET"])
@authenticate(basic_auth)
@output(BookSchema)
async def book(req, resp, *, id):
    """Get a book"""

    await req.db
    resp.obj = await Book.find(id=id)


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
@db.transaction
async def update_book_price(req, resp, id, *, data):
    """Update book price."""

    book = await Book.get(id)
    if not book:
        abort(404)

    await book.patch(**data)

    resp.obj = book


@app.route("/no_trans_update-price/{id}", methods=["PATCH"])
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
async def no_trans_update_book_price(req, resp, id, *, data):
    """Update book price no transaction."""

    session = await req.db
    book = await Book.get(id)
    if not book:
        abort(404)

    await book.patch(**data)
    await session.commit()

    resp.obj = book


@app.route("/all", methods=["GET"])
@authenticate(basic_auth)
@output(BookSchema)
async def all_books(req, resp):
    """Get all books"""

    await req.db

    resp.obj = await Book.all()


@app.route("/books/{id}", methods=["DELETE"])
@authenticate(basic_auth)
@db.transaction
async def deleting_book(req, resp, *, id):
    """Delete a book"""

    book = await Book.get(id)
    await book.destroy()

    resp.status_code = 204


if __name__ == "__main__":
    app.run()
