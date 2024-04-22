import os
from typing import Optional

from marshmallow import Schema, fields
from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import dyne

api = dyne.API()


class Base(DeclarativeBase):
    pass


# Define an example SQLAlchemy model
class Book(Base):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    price = Column(Float)
    title = Column(String)


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


@api.schema("PydanticBookCreate")
class PydanticBookSchema(BaseModel):
    id: Optional[int] = None
    price: float
    title: str
    model_config = ConfigDict(from_attributes=True)


@api.schema("MarshmallowBookCreate")
class MarshmallowBookSchema(Schema):
    id = fields.Integer(dump_only=True)
    price = fields.Float()
    title = fields.Str()


@api.route("/create", methods=["POST"])
@api.input(MarshmallowBookSchema)
@api.output(MarshmallowBookSchema)
async def create(req, resp, *, data):
    """Create book"""

    book = Book(**data)
    session.add(book)
    session.commit()

    resp.obj = book


@api.route("/all", methods=["POST"])
@api.output(PydanticBookSchema)
async def all_books(req, resp):
    """Get all books"""

    resp.obj = session.query(Book)


r = api.requests.post("http://;/create", json={"price": 11.99, "title": "Monty Python"})
print(r.json())

r = api.requests.post("http://;/all")
print(r.json())
os.remove("db")
