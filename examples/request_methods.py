import dyne

api = dyne.API()


@api.route("/greet/{greeting}")
async def greet(req, resp, *, greeting):  # Default `GET` request.
    resp.text = f"{greeting}, world!"


@api.route("/create", methods=["POST"])
async def book(req, resp):
    resp.media = await req.media()


@api.route("/book/{id}")
class BookResource:
    def on_get(self, req, resp, *, id):
        resp.text = f"Book - {id}"
        resp.status_code = api.status_codes.HTTP_201

    async def on_post(self, req, resp, *, id):
        resp.media = await req.media()

    def on_request(self, req, resp, *, id):  # any request method.
        resp.headers.update({"X-Life": f"{id}"})


if __name__ == "__main__":
    api.run()
