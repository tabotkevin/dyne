import os
from typing import Optional

from pydantic import BaseModel, ConfigDict
from sqlalchemy import Column, Float, Integer, String

import dyne
from dyne.ext.db.alchemical import Alchemical, Model
from dyne.ext.io.pydantic import input, output


# Define an example SQLAlchemy model
class Book(Model):
    __tablename__ = "books"
    id = Column(Integer, primary_key=True)
    price = Column(Float)
    title = Column(String)


class Config:
    ALCHEMICAL_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


app = dyne.App()
app.config.from_object(Config)
db = Alchemical(app)


class BookSchema(BaseModel):
    id: Optional[int] = None
    price: float
    title: str
    model_config = ConfigDict(from_attributes=True)


@app.route("/create", methods=["POST"])
@input(BookSchema)
@output(BookSchema)
async def create(req, resp, *, data):
    """Create book"""

    session = await req.db
    book = Book(**data)
    session.add(book)
    await session.commit()

    resp.obj = book


@app.route("/all", methods=["POST"])
@output(BookSchema)
async def all_books(req, resp):
    """Get all books"""

    session = await req.db
    query = await session.scalars(Book.select())

    resp.obj = query.all()


if __name__ == "__main__":
    app.run()

r = app.client.post("http://;/create", json={"price": 11.99, "title": "Monty Python"})
print(r.json())

r = app.client.post("http://;/all")
print(r.json())
os.remove("db")
