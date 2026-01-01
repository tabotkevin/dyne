import time

from pydantic import BaseModel

import dyne
from dyne.ext.io.pydantic import expect, input

app = dyne.App()


class BookSchema(BaseModel):
    price: float
    title: str


@app.route("/book", methods=["POST"])
@input(BookSchema)
@expect(
    {
        401: "Invalid access or refresh token",
        403: "Please verify your account",
    }
)
async def book_create(req, resp, *, data):
    @app.background.task
    def process_book(book):
        time.sleep(2)
        print(book)

    process_book(data)
    resp.media = {"msg": "created"}


r = app.client.post("http://;/book", json={"price": 9.99, "title": "Rust book"})
print(r.json())
print(f"Route's _spec: {book_create._spec}")
