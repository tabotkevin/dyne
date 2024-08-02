import time

from marshmallow import Schema, fields
from pydantic import BaseModel

import dyne

api = dyne.API()


@api.schema("BookSchema")
class BookSchema(BaseModel):  # Pydantic schema
    price: float
    title: str


@api.schema("HeaderSchema")
class HeaderSchema(Schema):  # Mashmellow schema
    x_version = fields.String(data_key="X-Version", required=True)


class CookiesSchema(BaseModel):
    max_age: int
    is_cheap: bool


class QuerySchema(Schema):
    page = fields.Int(load_default=1)
    limit = fields.Int(load_default=10)


class ItemModel(BaseModel):
    hello: str


# Manual validation
@api.route("/shop", methods=["POST"])
async def shop(req, resp):
    data = await req.validate(BookSchema)
    resp.media = data


# Media routes
@api.route("/book", methods=["POST"])
@api.input(BookSchema)  # default location is `media` default media key is `data`
async def book_create(req, resp, *, data):
    @api.background.task
    def process_book(book):
        time.sleep(2)
        print(book)

    process_book(data)
    resp.media = {"msg": "created"}


# Query(params) route
@api.route("/books")
@api.input(QuerySchema, location="query")
async def get_books(req, resp, *, query):
    print(query)  # e.g {'page': 2, 'limit': 20}
    resp.media = {"books": [{"title": "Python", "price": 39.00}]}


# Headers routes
@api.route("/book/{id}", methods=["POST"])
@api.input(HeaderSchema, location="headers")
async def book(req, resp, *, id, headers):
    """Header Pydantic"""
    print(headers)  # e.g {"x_version": "2.4.5"}
    resp.media = {"title": f"Lost {id}", "price": 9.99}


# Cookies routes
@api.route("/")
@api.input(CookiesSchema, location="cookies")
async def home(req, resp, *, cookies):
    """Cookies Mashmellow"""
    print(cookies)  # e.g {"max_age": "123", "is_cheap": True}
    resp.text = "Welcome to book store."


# Demonstrating stacking of decorators routes
@api.route("/store", methods=["POST"])
@api.input(
    CookiesSchema, location="cookies", key="c"
)  # default key is the value of location.
@api.input(BookSchema)
async def store(req, resp, *, c, data):
    print(f"Cookies: {c}")
    resp.media = data


# Let's make an HTTP request to the server, to test it out.'}

# Media requests
r = api.requests.post("http://;/book", json={"price": 9.99, "title": "Pydantic book"})
print(r.json())


# Query(params) requests
r = api.requests.get("http://;/books?page=2&limit=20")
print(r.json())


# Headers requests
r = api.requests.post("http://;/book/1", headers={"X-Version": "2.4.5"})
print(r.json())


# Cookies requests
r = api.requests.get("http://;/", cookies={"max_age": "123", "is_cheap": "True"})
print(r.text)


r = api.requests.post(
    "http://;/store",
    json={"price": 9.99, "title": "Pydantic book"},
    cookies={"max_age": "123", "is_cheap": "True"},
)
print(r.json())


# Manual validation
r = api.requests.post("http://;/shop", json={"price": 9.99, "title": "Harry Potter"})
print(r.text)
