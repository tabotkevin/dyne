import time

from marshmallow import Schema, fields

import dyne
from dyne.ext.io.marshmallow import input, webhook

app = dyne.App()


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
@app.route("/book", methods=["POST"])
@input(BookSchema)
async def create_book(req, resp, *, data):
    @app.background.task
    def process(book):
        time.sleep(2)
        print(book)

    process(data)
    resp.media = {"status": "created"}


# Query parameters
@app.route("/books")
@input(QuerySchema, location="query")
async def list_books(req, resp, *, query):
    print(query)
    resp.media = [{"title": "Python", "price": 39.00}]


# Headers
@app.route("/book/{id}", methods=["POST"])
@input(HeaderSchema, location="header")
async def book_version(req, resp, *, id, header):
    print(header)
    resp.media = {"id": id, "version": header["x_version"]}


# Cookies
@app.route("/")
@input(CookiesSchema, location="cookie")
async def home(req, resp, *, cookie):
    print(cookie)
    resp.text = "Welcome (Marshmallow)"


# With webhook annotation.
@app.route("/transaction", methods=["POST"])
@webhook(name="transaction")
@input(BookSchema)
async def purchases(req, resp, *, data):
    @app.background.task
    def process(book):
        time.sleep(2)
        print(book)

    process(data)
    resp.media = {"status": "Received!"}


# Stacked inputs (cookies + body)
@app.route("/store", methods=["POST"])
@input(CookiesSchema, location="cookie", key="cookies")
@input(BookSchema)
async def store(req, resp, *, cookies, data):
    print(f"Cookies: {cookies}")
    resp.media = data


# # Let's make an HTTP request to the server, to test it out.'}

# Media requests
r = app.client.post(
    "http://;/book", json={"price": 39.99, "title": "Pragmatic Programmer"}
)
print(r.json())


# Query(params) requests
r = app.client.get("http://;/books?page=2&limit=20")
print(r.json())


# Headers requests
r = app.client.post("http://;/book/1", headers={"X-Version": "2.4.5"})
print(r.json())


# Cookies requests
r = app.client.get("http://;/", cookies={"max_age": "123", "is_cheap": "True"})
print(r.text)


# Stacking inputs
r = app.client.post(
    "http://;/store",
    json={"price": 39.99, "title": "Pragmatic Programmer"},
    cookies={"max_age": "123", "is_cheap": "True"},
)
print(r.json())
