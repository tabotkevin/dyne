## A light weight Python async framework with batteries included

[![Build](https://github.com/tabotkevin/dyne/actions/workflows/build.yaml/badge.svg)](https://github.com/tabotkevin/dyne/actions/workflows/build.yaml)
[![Documentation Status](https://readthedocs.org/projects/dyneapi/badge/?version=latest)](https://dyneapi.readthedocs.io/en/latest/?badge=latest)
[![image](https://img.shields.io/pypi/v/dyne.svg)](https://pypi.org/project/dyne/)
[![image](https://img.shields.io/pypi/l/dyne.svg)](https://pypi.org/project/dyne/)
[![image](https://img.shields.io/pypi/pyversions/dyne.svg)](https://pypi.org/project/dyne/)
[![image](https://img.shields.io/github/contributors/tabotkevin/dyne.svg)](https://github.com/tabotkevin/dyne/graphs/contributors)

```python

import dyne
from dyne.ext.auth import authenticate
from dyne.ext.io.pydantic import input, output, expect
from dyne.ext.openapi import OpenAPI

app = dyne.App()
api = OpenAPI(app, description=description)


@api.route("/book", methods=["POST"])
@authenticate(basic_auth, role="admin")
@input(BookCreateSchema, location="form")
@output(BookSchema, status_code=201)
@expect({401: "Unauthorized", 400: "Invalid file format"})
async def create_book(req, resp, *, data):
    """
    Create a new Book
    ---
    This endpoint allows admins to upload a book cover and metadata.
    """

    image = data.pop("image")
    await image.asave(f"uploads/{image.filename}") # The image is already validated for extension and size.


    book = Book(**data, cover=image.filename)
    session.add(book)
    session.commit()

    resp.obj = book

```

![screenshot](screenshot.png)

Dyne is a modern async framework for APIs and applications, featuring built-in authentication, validation & serialization (Pydantic & Marshmallow), automatic OpenAPI, GraphQL support (Strawberry & Graphene), and async SQLAlchemy integration via Alchemical—all with minimal first class configuration.

It delivers a production-ready ASGI foundation out of the box. It features an integrated static file server powered by (`WhiteNoise <http://whitenoise.evans.io/en/stable/>`\_), Jinja2 templating for dynamic rendering, and a high-performance uvloop-based webserver—all optimized with automatic Gzip compression for reduced latency.

## Documentation

See the [documentation](https://dyneapi.readthedocs.io), for more details on features available in dyne.

## Installation

Dyne uses **optional dependencies** (extras) to keep the core package lightweight.  
This allows you to install only the features you need for your specific project.

### Core Installation

To install the minimal ASGI core:

```bash
pip install dyne
```

## Installing Specific Feature Sets

Choose the bundle that fits your technology stack. Note that for most shells (like Zsh on macOS), you should wrap the package name in quotes to handle the brackets correctly.

> **Note:** The use of brackets `[]` is required.

### 1. OpenAPI + (Request Validation & Response Serialization)

Enable automated OpenAPI (Swagger) documentation, request validation and response serialization using your preferred schema library:

#### With Pydantic

```bash
pip install "dyne[openapi_pydantic]"
```

#### With Marshmallow

```bash
pip install "dyne[openapi_marshmallow]"
```

### 2. GraphQL Engines

Integrate a native GraphQL interface and the GraphiQL IDE:

#### With Strawberry

```bash
pip install "dyne[graphql_strawberry]"
```

#### With Graphene

```bash
pip install "dyne[graphql_graphene]"
```

### 3. Database SQLAlchemy with Alchemical

Database SQLAlchemy support with Alchemical

```bash
pip install "dyne[sqlalchemy]"
```

### 4. Full Installation

To install all available features, including:

- Both GraphQL engines
- SQLAlchemy (Alchemical)
- Both serialization engines
- OpenAPI support
- HTTP client helpers

```bash
pip install "dyne[full]"
```

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

- **A built in testing client that uses the actual Requests you know and love**.
- **A Pleasant Application Experience**: Designed for developer happiness with a clean, intuitive, and consistent API.
- **Native ASGI Foundation**: Built on the `ASGI <https://asgi.readthedocs.io>`\_ standard for high-performance, fully asynchronous applications.
- **Expressive Routing**: Declare routes using familiar `f-string syntax <https://docs.python.org/3/whatsnew/3.6.html#pep-498-formatted-string-literals>`\_, improving readability and maintainability.
- **First-Class Configuration**: Strongly typed, auto-casted configuration with `.env` auto-discovery, environment variable overrides, and validation at startup.
- **Database Integration**: First-class **SQLAlchemy** support powered by **Alchemical**, providing clean session management, async-friendly patterns, and declarative configuration.
- **Seamless API Documentation**: Fully self-generated **OpenAPI** documentation with an interactive UI and native support for both `Pydantic` and `Marshmallow` schemas.
- **Flexible View Layer**: Support for function-based or class-based views (without mandatory inheritance) and a mutable response object that simplifies response handling.
- **GraphQL Support**: Native integration with **Strawberry** and **Graphene**, including **GraphiQL** for interactive schema exploration.
- **Webhooks & Async Events**: First-class webhook definition and documentation via the `@webhook` decorator, enabling clearly defined outbound callbacks and event-driven workflows.
- **Request & Response Lifecycle**: Powerful decorators such as `@input` for validation, `@output` for serialization, and `@expect` for enforcing headers, cookies, and request metadata.
- **Bidirectional Communication**: Built-in support for **WebSockets** alongside traditional HTTP and GraphQL endpoints.
- **Background Tasks**: Easily offload long-running or blocking work using a built-in `ThreadPoolExecutor`.
- **Extensible Architecture**: Mount any ASGI-compatible application at a subroute and serve single-page applications (SPAs) natively.
- **Integrated Security**: First-class authentication support for `BasicAuth`, `TokenAuth`, and `DigestAuth`.
