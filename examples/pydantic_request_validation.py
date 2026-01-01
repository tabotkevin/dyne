import time

from pydantic import AliasGenerator, BaseModel, ConfigDict

import dyne
from dyne.ext.io.pydantic import input, webhook

app = dyne.App()


class BookSchema(BaseModel):
    title: str
    price: float


class HeaderSchema(BaseModel):
    x_version: str

    model_config = ConfigDict(
        # Accept the alias even if the framework lowercased it and try converting 'x-version' to 'x_version'
        alias_generator=AliasGenerator(
            validation_alias=lambda field_name: field_name.replace("_", "-"),
        ),
        populate_by_name=True,
    )


class CookiesSchema(BaseModel):
    max_age: int
    is_cheap: bool


class QuerySchema(BaseModel):
    page: int = 1
    limit: int = 10


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
    resp.media = [{"title": "Pragmatic Programmer", "price": 39.99}]


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
    resp.text = "Welcome (Pydantic)"


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


# Let's make an HTTP request to the server, to test it out.'}

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


# # Cookies requests
r = app.client.get("http://;/", cookies={"max_age": "123", "is_cheap": "True"})
print(r.text)

# Stacking inputs
r = app.client.post(
    "http://;/store",
    json={"price": 39.99, "title": "Pragmatic Programmer"},
    cookies={"max_age": "123", "is_cheap": "True"},
)
print(r.json())
