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
    from dyne.ext.auth import authenticate
    from dyne.ext.auth.backends import BasicAuth
    from dyne.ext.io.pydantic import input, output, expect
    from dyne.ext.openapi import OpenAPI

    app = dyne.App()
    api = OpenAPI(app, description=description)
    basic_auth = BasicAuth()

    
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


Dyne delivers a production-ready ASGI foundation out of the box. It features an integrated static file server powered by (`WhiteNoise <http://whitenoise.evans.io/en/stable/>`_), Jinja2 templating for dynamic rendering, and a high-performance uvloop-based webserver—all optimized with automatic Gzip compression for reduced latency.

Features
--------

* **A pleasant App**: Designed for developer happiness with a clean, intuitive experience.
* **Native ASGI Support**: Built on the `ASGI <https://asgi.readthedocs.io>`_ standard for high-performance, asynchronous web services.
* **Intuitive Routing**: Use familiar `f-string syntax <https://docs.python.org/3/whatsnew/3.6.html#pep-498-formatted-string-literals>`_ for expressive, readable route declarations.
* **Production-Ready Config**: Hybrid configuration system with `.env` auto-discovery, Starlette-inspired type casting, and environment overrides.
* **Seamless Documentation**: Full, self-generating **OpenAPI** documentation with interactive UI and support for `Pydantic` or `Marshmallow` schemas.
* **Flexible Views**: Support for function-based or class-based views (without mandatory inheritance) and a mutable response object that simplifies view logic.
* **Bidirectional Communication**: Native support for **WebSockets** and **GraphQL** (including *GraphiQL* integration).
* **Request & Response Life-cycle**: Advanced decorators for `@input` validation, `@output` serialization, `@expect` headers, and `@webhook` callback documentation.
* **Background Tasks**: Built-in support for offloading long-running operations to a `ThreadPoolExecutor`.
* **Extensible Architecture**: Mount any existing ASGI application at a subroute and enjoy native single-page webapp (SPA) support.
* **Integrated Security**: First-class support for `BasicAuth`, `TokenAuth`, and `DigestAuth` authentication schemes.


User Guides
-----------

.. toctree::
   :maxdepth: 2

   quickstart
   tour
   deployment
   testing
   maintainers
