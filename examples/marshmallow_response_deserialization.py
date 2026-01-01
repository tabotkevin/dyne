import os

from marshmallow import Schema, fields
from sqlalchemy import Column, Float, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import dyne
from dyne.ext.io.marshmallow import input, output

app = dyne.App()


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


class BookSchema(Schema):
    id = fields.Integer(dump_only=True)
    price = fields.Float()
    title = fields.Str()


@app.route("/create", methods=["POST"])
@input(BookSchema)
@output(BookSchema)
async def create(req, resp, *, data):
    """Create book"""

    book = Book(**data)
    session.add(book)
    session.commit()

    resp.obj = book


@app.route("/all", methods=["POST"])
@output(BookSchema)
async def all_books(req, resp):
    """Get all books"""

    resp.obj = session.query(Book)


r = app.client.post("http://;/create", json={"price": 11.99, "title": "Monty Python"})
print(r.json())

r = app.client.post("http://;/all")
print(r.json())
os.remove("db")
