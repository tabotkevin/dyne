from marshmallow import Schema, fields
from pydantic import BaseModel, Field
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import dyne
from dyne.ext.auth import BasicAuth
from dyne.fields.mashmellow import FileField
from dyne.fields.pydantic import File

doc = """
API Documentation

This module provides an interface to interact with the user management API. It allows for operations such as retrieving user information, creating new users, updating existing users, and deleting users.

Base URL:
    https://api.example.com/v1

Authentication:
    All API requests require an API key. Include your API key in the Authorization header as follows:
    Authorization: Bearer YOUR_API_KEY

For further inquiries or support, please contact support@example.com.
"""


api = dyne.API()
api.state.doc = doc  # Set the `doc` on state variable to get the overview documentation


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


class Base(DeclarativeBase):
    pass


# An SQLAlchemy model
class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    price = Column(Float)
    title = Column(String)
    cover = Column(String, nullable=True)


# Create tables in the database
engine = create_engine("sqlite:///db", connect_args={"check_same_thread": False})
Base.metadata.create_all(engine)


# Create a session
Session = sessionmaker(bind=engine)
session = Session()

book1 = Book(price=9.99, title="Harry Potter")
book2 = Book(price=10.99, title="Pirates of the sea")
session.add(book1)
session.add(book2)
session.commit()


class BookSchema(Schema):
    id = fields.Integer(dump_only=True)
    price = fields.Float()
    title = fields.Str()
    cover = fields.Str()


class BookCreateSchema(Schema):
    price = fields.Float()
    title = fields.Str()
    image = FileField(allowed_extensions=["png", "jpg"], max_size=5 * 1024 * 1024)


@api.schema("PydanticBookCreateSchema")
class PydanticBookCreateSchema(BaseModel):
    price: float
    title: str
    image: File = Field(...)

    class Config:
        from_attributes = True


@api.route("/create", methods=["POST"])
@api.authenticate(basic_auth, role="user")
@api.input(BookCreateSchema, location="form")
@api.output(BookSchema)
@api.expect(
    {
        401: "Invalid credentials",
    }
)
async def create(req, resp, *, data):
    """Create book"""

    image = data.pop("image")
    await image.save(image.filename)  # image already validated for extension and size

    book = Book(**data, cover=image.filename)
    session.add(book)
    session.commit()

    resp.obj = book


@api.route("/book/{id}", methods=["POST"])
@api.authenticate(basic_auth)
@api.output(BookSchema)
async def book(req, resp, *, id):
    """Get a book"""

    resp.obj = session.query(Book).filter_by(id=id).first()


@api.route("/all", methods=["GET"])
@api.authenticate(basic_auth)
@api.output(BookSchema)
async def all_books(req, resp):
    """Get all books"""

    resp.obj = session.query(Book)


if __name__ == "__main__":
    api.run()
