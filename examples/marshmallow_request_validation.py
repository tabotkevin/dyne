import time

from marshmallow import Schema, fields

import dyne
from dyne.ext.io.marshmallow import input

api = dyne.API()


class BookSchema(Schema):
    title = fields.String(required=True)
    price = fields.Float(required=True)


class HeaderSchema(Schema):
    x_version = fields.String(
        data_key="X-Version",
        required=True,
    )


class CookiesSchema(Schema):
    max_age = fields.Int(required=True)
    is_cheap = fields.Bool(required=True)


class QuerySchema(Schema):
    page = fields.Int(load_default=1)
    limit = fields.Int(load_default=10)


# Media (JSON body)
@api.route("/book", methods=["POST"])
@input(BookSchema)
async def create_book(req, resp, *, data):
    @api.background.task
    def process(book):
        time.sleep(2)
        print(book)

    process(data)
    resp.media = {"status": "created"}


# Query parameters
@api.route("/books")
@input(QuerySchema, location="query")
async def list_books(req, resp, *, query):
    print(query)
    resp.media = [{"title": "Python", "price": 39.00}]


# Headers
@api.route("/book/{id}", methods=["POST"])
@input(HeaderSchema, location="headers")
async def book_version(req, resp, *, id, headers):
    print(headers)
    resp.media = {"id": id, "version": headers["x_version"]}


# Cookies
@api.route("/")
@input(CookiesSchema, location="cookies")
async def home(req, resp, *, cookies):
    print(cookies)
    resp.text = "Welcome (Marshmallow)"


# Stacked inputs (cookies + body)
@api.route("/store", methods=["POST"])
@input(CookiesSchema, location="cookies", key="cookies")
@input(BookSchema)
async def store(req, resp, *, cookies, data):
    print(f"Cookies: {cookies}")
    resp.media = data


# # Let's make an HTTP request to the server, to test it out.'}

# Media requests
r = api.client.post(
    "http://;/book", json={"price": 39.99, "title": "Pragmatic Programmer"}
)
print(r.json())


# Query(params) requests
r = api.client.get("http://;/books?page=2&limit=20")
print(r.json())


# Headers requests
r = api.client.post("http://;/book/1", headers={"X-Version": "2.4.5"})
print(r.json())


# Cookies requests
r = api.client.get("http://;/", cookies={"max_age": "123", "is_cheap": "True"})
print(r.text)


# Stacking inputs
r = api.client.post(
    "http://;/store",
    json={"price": 39.99, "title": "Pragmatic Programmer"},
    cookies={"max_age": "123", "is_cheap": "True"},
)
print(r.json())
