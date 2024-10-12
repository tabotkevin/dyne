## A light weight Python async framework with batteries included

[![Build](https://github.com/tabotkevin/dyne/actions/workflows/build.yaml/badge.svg)](https://github.com/tabotkevin/dyne/actions/workflows/build.yaml)
[![Documentation Status](https://readthedocs.org/projects/dyneapi/badge/?version=latest)](https://dyneapi.readthedocs.io/en/latest/?badge=latest)
[![image](https://img.shields.io/pypi/v/dyne.svg)](https://pypi.org/project/dyne/)
[![image](https://img.shields.io/pypi/l/dyne.svg)](https://pypi.org/project/dyne/)
[![image](https://img.shields.io/pypi/pyversions/dyne.svg)](https://pypi.org/project/dyne/)
[![image](https://img.shields.io/github/contributors/tabotkevin/dyne.svg)](https://github.com/tabotkevin/dyne/graphs/contributors)

```python
import dyne

api = dyne.API()

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
    await image.save(image.filename)  # File already validated for extension and size.

    book = Book(**data, cover=image.filename)
    session.add(book)
    session.commit()

    resp.obj = book

if __name__ == "__main__":
  api.run()
```

Powered by [Starlette](https://www.starlette.io/). [View documentation](https://dyneapi.readthedocs.io).

This gets you a ASGI app, with a production static files server pre-installed, jinja2
templating (without additional imports), and a production webserver based on uvloop,
serving up requests with gzip compression automatically.

## More Examples

See
[the documentation's feature tour](https://dyneapi.readthedocs.io/en/latest/tour.html)
for more details on features available in dyne.

## Installing dyne

Install the stable release:

    pip install dyne

## The Basic Idea

The primary concept here is to bring the niceties that are brought forth from both Flask
and Falcon and unify them into a single framework, along with some new ideas I have. I
also wanted to take some of the API primitives that are instilled in the Requests
library and put them into a web framework. So, you'll find a lot of parallels here with
Requests.

- Setting `resp.content` sends back bytes.
- Setting `resp.text` sends back unicode, while setting `resp.html` sends back HTML.
- Setting `resp.media` sends back JSON/YAML (`.text`/`.html`/`.content` override this).
- Setting `resp.obj` deserializes SQLAlchemy object(s) using Pydantic or Marshmallow schemas
- Case-insensitive `req.headers` dict (from Requests directly).
- `resp.status_code`, `req.method`, `req.url`, and other familiar friends.

## Ideas

- Flask-style route expression, with new capabilities -- all while using Python 3.6+'s
  new f-string syntax.
- I love Falcon's "every request and response is passed into to each view and mutated"
  methodology, especially `response.media`, and have used it here. In addition to
  supporting JSON, I have decided to support YAML as well, as Kubernetes is slowly
  taking over the world, and it uses YAML for all the things. Content-negotiation and
  all that.
- **A built in testing client that uses the actual Requests you know and love**.
- The ability to mount other WSGI apps easily.
- Automatic gzipped-responses.
- In addition to Falcon's `on_get`, `on_post`, etc methods, dyne features an
  `on_request` method, which gets called on every type of request, much like Requests.
- A production static file server is built-in.
- Uvicorn built-in as a production web server. I would have chosen Gunicorn, but it
  doesn't run on Windows. Plus, Uvicorn serves well to protect against slowloris
  attacks, making nginx unnecessary in production.
- GraphQL support, via Graphene. The goal here is to have any GraphQL query exposable at
  any route, magically.
- Provide an official way to run webpack.
