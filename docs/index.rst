.. dyne documentation master file, created by
   sphinx-quickstart on Thu Oct 11 12:58:34 2018.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

A light weight Python async framework with batteries included.
=================================

|Build Status| |Documentation| |image1| |image2| |image3| |image4| |image5|

.. |Build Status| image:: https://github.com/tabotkevin/dyne/actions/workflows/build.yaml/badge.svg
   :target: https://github.com/tabotkevin/dyne/actions/workflows/build.yaml
.. |Documentation| image:: https://readthedocs.org/projects/dyneapi/badge/?version=latest
   :target: https://dyneapi.readthedocs.io/en/latest/?badge=latest
.. |image1| image:: https://img.shields.io/pypi/v/dyne.svg
   :target: https://pypi.org/project/dyne/
.. |image2| image:: https://img.shields.io/pypi/l/dyne.svg
   :target: https://pypi.org/project/dyne/
.. |image3| image:: https://img.shields.io/pypi/pyversions/dyne.svg
   :target: https://pypi.org/project/dyne/
.. |image4| image:: https://img.shields.io/github/contributors/tabotkevin/dyne.svg
   :target: https://github.com/tabotkevin/dyne/graphs/contributors
.. |image5| image:: https://img.shields.io/badge/Say%20Thanks-!-1EAEDB.svg
   :target: https://saythanks.io/to/tabotkevin

.. code:: python

    import dyne
    from pydantic import BaseModel, ConfigDict
    from dyne.ext.auth import authenticate
    from dyne.ext.auth.backends import BasicAuth
    from dyne.ext.io.pydantic import input, output, expect
    from dyne.ext.io.pydantic.fields import FileField
    from dyne.ext.openapi import OpenAPI

    app = dyne.App()
    api = OpenAPI(app, description=description)
    basic_auth = BasicAuth()

    
    class Book(Base): # An SQLAlchemy model
        __tablename__ = "books"
        id = Column(Integer, primary_key=True)
        price = Column(Float)
        title = Column(String)
        cover = Column(String, nullable=True)


    class BookSchema(BaseModel):
        id: int | None = None
        price: float
        title: str
        cover: str | None

        model_config = ConfigDict(from_attributes=True)

    class Image(FileField):
        max_size = 5 * 1024 * 1024
        allowed_extensions = {"jpg", "jpeg", "png"}

    class BookCreateSchema(BaseModel):
        price: float
        title: str
        image: Image

        model_config = ConfigDict(
            from_attributes=True,
            arbitrary_types_allowed=True
        )

    @app.route("/book", methods=["POST"])
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


Powered by `Starlette <https://www.starlette.io/>`_.

This gets you a ASGI app, with a production static files server
(`WhiteNoise <http://whitenoise.evans.io/en/stable/>`_)
pre-installed, jinja2 templating (without additional imports), and a
production webserver based on uvloop, serving up requests with
automatic gzip compression.

Features
--------

- A pleasant App, with a single import statement.
- Class-based views without inheritance.
- `ASGI <https://asgi.readthedocs.io>`_ framework, the future of Python web services.
- WebSocket support!
- The ability to mount any ASGI / WSGI app at a subroute.
- `f-string syntax <https://docs.python.org/3/whatsnew/3.6.html#pep-498-formatted-string-literals>`_ route declaration.
- Mutable response object, passed into each view. No need to return anything.
- Background tasks, spawned off in a ``ThreadPoolExecutor``.
- GraphQL (with *GraphiQL*) support!
- OpenAPI schema generation, with interactive documentation!
- Single-page webapp support!

User Guides
-----------

.. toctree::
   :maxdepth: 2

   quickstart
   tour
   deployment
   testing
   app
   maintainers


Installation Guide
------------------

Dyne uses **optional dependencies** (extras) to keep the core package lightweight. This allows you to install only the features you need for your specific project.

Installing Specific Feature Sets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can install the following bundles using `pip`. Note that the use of brackets `[]` is required.

1. OpenAPI & Serialization
^^^^^^^^^^^^^^^^^^^^^^^^^^

If you are building a REST API and want to use **Pydantic** or **Marshmallow** for validation and OpenAPI (Swagger) generation:

* **With Pydantic:**
.. code-block:: bash
  pip install "dyne[openapi_pydantic]"

* **With Marshmallow:**
.. code-block:: bash
  pip install "dyne[openapi_marshmallow]"

2. GraphQL Engines
^^^^^^^^^^^^^^^^^^

If you are building a GraphQL API, choose your preferred schema definition library:

* **With Strawberry:**
.. code-block:: bash
  pip install "dyne[graphql_strawberry]"

* **With Graphene:**
.. code-block:: bash
  pip install "dyne[graphql_graphene]"

3. Command Line Interface (CLI)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To enable Dyne's terminal-based tools and commands:

.. code-block:: bash

  pip install "dyne[cli]"

4. Full Installation
^^^^^^^^^^^^^^^^^^^^

To install all available features, including both GraphQL engines, both serialization engines, OpenAPI support, Flask adapters, and HTTP client helpers:

.. code-block:: bash

  pip install "dyne[full]"


Summary Table
^^^^^^^^^^^^^

+-----------------------+----------------------------------+----------------------------------+
| Bundle Name           | Primary Use Case                 | Key Dependencies                 |
+=======================+==================================+==================================+
| openapi_pydantic      | REST APIs with modern type hints | pydantic, apispec, requests      |
+-----------------------+----------------------------------+----------------------------------+
| openapi_marshmallow   | REST APIs with schema validation | marshmallow, apispec, requests   |
+-----------------------+----------------------------------+----------------------------------+
| graphql_strawberry    | Modern Pythonic GraphQL          | strawberry, graphql-server       |
+-----------------------+----------------------------------+----------------------------------+
| graphql_graphene      | Object-style GraphQL             | graphene, graphql-server         |
+-----------------------+----------------------------------+----------------------------------+
| cli                   | Terminal tools and scaffolding   | docopt                           |
+-----------------------+----------------------------------+----------------------------------+
| full                  | Everything included              | All of the above                 |
+-----------------------+----------------------------------+----------------------------------+

> **Note for Zsh users:** If you are using Zsh (default on macOS), you may need to wrap the package name in quotes to prevent the shell from interpreting the brackets: `pip install "dyne[full]"`.


Only **Python 3.10+** and above is supported.


The Basic Idea
--------------

The primary concept here is to bring the niceties that are brought forth from both Flask and Falcon and unify them into a single framework, along with some new ideas I have. I also wanted to take some of the API primitives that are instilled in the Requests library and put them into a web framework. So, you'll find a lot of parallels here with Requests.

- Setting ``resp.content`` sends back bytes.
- Setting ``resp.text`` sends back unicode, while setting ``resp.html`` sends back HTML.
- Setting ``resp.media`` sends back JSON/YAML (``.text``/``.html``/``.content`` override this).
- Case-insensitive ``req.headers`` dict (from Requests directly).
- ``resp.status_code``, ``req.method``, ``req.url``, and other familiar friends.

Ideas
-----

- Flask-style route expression, with new capabilities -- all while using Python 3.6+'s new f-string syntax.
- I love Falcon's "every request and response is passed into each view and mutated" methodology, especially ``response.media``, and have used it here. In addition to supporting JSON, I have decided to support YAML as well, as Kubernetes is slowly taking over the world, and it uses YAML for all the things. Content-negotiation and all that.
- **A built in testing client that uses the actual Requests you know and love**.
- The ability to mount other WSGI apps easily.
- Automatic gzipped-responses.
- In addition to Falcon's ``on_get``, ``on_post``, etc methods, dyne features an ``on_request`` method, which gets called on every type of request, much like Requests.
- A production static files server is built-in.
- `Uvicorn <https://www.uvicorn.org/>`_ is built-in as a production web server. I would have chosen Gunicorn, but it doesn't run on Windows. Plus, Uvicorn serves well to protect against `slowloris <https://en.wikipedia.org/wiki/Slowloris_(computer_security)>`_ attacks, making nginx unnecessary in production.
- GraphQL support, via Graphene. The goal here is to have any GraphQL query exposable at any route, magically.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
