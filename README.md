## A light weight Python async framework with batteries included.

[![Documentation Status](https://readthedocs.org/projects/mybinder/badge/?version=latest)](https://responder.kennethreitz.org/en/latest/)
[![image](https://img.shields.io/pypi/v/responder.svg)](https://pypi.org/project/responder/)
[![image](https://img.shields.io/pypi/l/responder.svg)](https://pypi.org/project/responder/)
[![image](https://img.shields.io/pypi/pyversions/responder.svg)](https://pypi.org/project/responder/)
[![image](https://img.shields.io/github/contributors/kennethreitz/responder.svg)](https://github.com/kennethreitz/responder/graphs/contributors)

```python

import dyne

api = dyne.API()


@api.route("/{greeting}")
async def greet_world(req, resp, *, greeting):
    resp.text = f"{greeting}, world!"


if __name__ == "__main__":
    api.run()

```

Powered by [Starlette](https://www.starlette.io/). That `async` declaration is optional.
[View documentation](https://responder.readthedocs.io).

This gets you a ASGI app, with a production static files server pre-installed, jinja2
templating (without additional imports), and a production webserver based on uvloop,
serving up requests with gzip compression automatically.

## More Examples

See
[the documentation's feature tour](https://responder.readthedocs.io/en/latest/tour.html)
for more details on features available in dyne.

## Installing dyne

Install the stable release:

    $ pip install dyne

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
