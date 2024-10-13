Feature Tour
============

Introduction
------------

Dyne brings simplicity and elegance to API development, offering built-in features such as:

- **Authentication**: Support for `BasicAuth`, `TokenAuth`, and `DigestAuth`.
- **Input Validation**: The `@api.input` decorator makes validating request bodies easy.
- **Response Serialization**: Use the `@api.output` decorator to serialize responses automatically.
- **OpenAPI Documentation**: Full self-generated OpenAPI documentation with seamless integration for both `Pydantic` and `Marshmallow` schemas.

Here's how you can get started:

::

    api = dyne.API()

    # Basic Authentication Example
    users = dict(john="password", admin="password123")
    roles = {"john": "user", "admin": ["user", "admin"]}

    basic_auth = BasicAuth()

    @basic_auth.verify_password
    async def verify_password(username, password):
        if username in users and users.get(username) == password:
            return username
        return None

    @basic_auth.error_handler
    async def error_handler(req, resp, status_code=401):
        resp.text = "Invalid credentials"
        resp.status_code = status_code

    @basic_auth.get_user_roles
    async def get_user_roles(user):
        return roles.get(user)

### Example: Book Creation API

This example demonstrates a clean and minimal API endpoint for creating a new book. The API supports file uploads with built-in validation for file extensions and file sizes.

**SQLAlchemy Model:**

.. code-block:: python

    class Book(Base):
        __tablename__ = "books"
        id = Column(Integer, primary_key=True)
        price = Column(Float)
        title = Column(String)
        cover = Column(String, nullable=True)

**Schemas: Marshmellow**

.. code-block:: python

    class BookSchema(Schema):
        id = fields.Integer(dump_only=True)
        price = fields.Float()
        title = fields.Str()
        cover = fields.Str()

    class BookCreateSchema(Schema):
        price = fields.Float()
        title = fields.Str()
        image = FileField(allowed_extensions=["png", "jpg"], max_size=5 * 1024 * 1024)  # Built-in file validation

**Endpoint:**

.. code-block:: python

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
        await image.save(image.filename)  # File already validated

        book = Book(**data, cover=image.filename)
        session.add(book)
        session.commit()

        resp.obj = book

This example demonstrates how Dyne simplifies API development by handling authentication, input validation, response serialization, and file handling with minimal code, while automatically generating OpenAPI documentation. 


Class-Based Views
-----------------

Class-based views (and setting some headers and stuff)::

    @api.route("/{greeting}")
    class GreetingResource:
        def on_request(self, req, resp, *, greeting):   # or on_get...
            resp.text = f"{greeting}, world!"
            resp.headers.update({'X-Life': '42'})
            resp.status_code = api.status_codes.HTTP_416


Background Tasks
----------------

Here, you can spawn off a background thread to run any function, out-of-request::

    @api.route("/")
    def hello(req, resp):

        @api.background.task
        def sleep(s=10):
            time.sleep(s)
            print("slept!")

        sleep()
        resp.content = "processing"


GraphQL
-------

Serve a GraphQL API::

    import graphene

    class Query(graphene.ObjectType):
        hello = graphene.String(name=graphene.String(default_value="stranger"))

        def resolve_hello(self, info, name):
            return f"Hello {name}"

    schema = graphene.Schema(query=Query)
    view = dyne.ext.GraphQLView(api=api, schema=schema)

    api.add_route("/graph", view)

Visiting the endpoint will render a *GraphiQL* instance, in the browser.

You can make use of dyne's Request and Response objects in your GraphQL resolvers through ``info.context['request']`` and ``info.context['response']``.



Request validation
------------------
Dyne provides built-in support for validating requests from various sources such as the request body (JSON, form, YAML), headers, cookies, and query parameters against Marshmallow and Pydantic schemas. This is done using the `@input` decorator, which specifies the location for validation. Supported locations are `media`, `headers`, `cookies`, and `query(params)`. 

Optionally, you can provide a `key` variable, which acts as the name of the variable to be used in the endpoint. By default, the `key` is the value of the location, except for `media`, where the key is called `data` by default.


::

    import time

    from marshmallow import Schema, fields
    from pydantic import BaseModel

    import dyne

    api = dyne.API()


    @api.schema("BookSchema")
    class BookSchema(BaseModel):  # Pydantic schema
        price: float
        title: str


    class QuerySchema(Schema):  # Marshmellow schema
        page = fields.Int(missing=1)
        limit = fields.Int(missing=10)


    # Media routes
    @api.route("/book", methods=["POST"])
    @api.input(BookSchema)  # default location is `media` default media key is `data`
    async def book_create(req, resp, *, data):
        @api.background.task
        def process_book(book):
            time.sleep(2)
            print(book)

        process_book(data)
        resp.media = {"msg": "created"}


    # Query(params) route
    @api.route("/books")
    @api.input(QuerySchema, location="query")
    async def get_books(req, resp, *, query):
        print(query)  # e.g {'page': 2, 'limit': 20}
        resp.media = {"books": [{"title": "Python", "price": 39.00}]}


    # Media requests
    r = api.requests.post("http://;/book", json={"price": 9.99, "title": "Pydantic book"})
    print(r.json())

    # Query(params) requests
    r = api.requests.get("http://;/books?page=2&limit=20")
    print(r.json())


Response Serialization
----------------------
Dyne provides the functionality to serialize SQLAlchemy objects or queries into JSON responses using Marshmallow or Pydantic schemas. This is achieved by using the `@output` decorator and setting `resp.obj` within the endpoint, which allows Dyne to deserialize the response as specified by the schema.

This decorator also supports parameters such as `header`, which defines a schema for the response headers, and `description`, which can be used to provide a description in place of a status code for successful responses.


::

    import os
    from typing import Optional

    from marshmallow import Schema, fields
    from pydantic import BaseModel, ConfigDict
    from sqlalchemy import Column, Float, Integer, String, create_engine
    from sqlalchemy.orm import DeclarativeBase, sessionmaker

    import dyne

    api = dyne.API()


    # Define an example SQLAlchemy model
    class Book(DeclarativeBase):
        __tablename__ = "books"
        id = Column(Integer, primary_key=True)
        price = Column(Float)
        title = Column(String)


    # Create tables in the database
    engine = create_engine("sqlite:///db", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)

    # Create a session
    Session = sessionmaker(bind=engine)
    session = Session()

    book1 = Book(price=9.99, title="Harry Potter")
    session.add(book1)
    session.commit()


    @api.schema("BookSchema")
    class BookSchema(BaseModel):
        id: Optional[int] = None
        price: float
        title: str
        model_config = ConfigDict(from_attributes=True)


    @api.route("/create", methods=["POST"])
    @api.input(BookSchema)
    @api.output(BookSchema)
    async def create(req, resp, *, data):
        """Create book"""

        book = Book(**data)
        session.add(book)
        session.commit()

        resp.obj = book


    @api.route("/all", methods=["POST"])
    @api.output(BookSchema)
    async def all_books(req, resp):
        """Get all books"""

        resp.obj = session.query(Book)


    r = api.requests.post("http://;/create", json={"price": 11.99, "title": "Monty Python"})
    print(r.json())  # {'id': 3, 'price': 11.99, 'title': 'Monty Python'}

    r = api.requests.post("http://;/all")
    print(r.json())  # [{'id': 1, 'price': 9.99, 'title': 'Harry Potter'}, {'id': 2, 'price': 11.99, 'title': 'Monty Python'}]


Other responses
-------
The `@expect` decorator accepts a dictionary argument containing response status codes as keys and their corresponding documentation as values.

To include text descriptions for these responses, assign a description string to the value of each status code. Used in the `OpenAPI` documentation.

::

    import dyne

    api = dyne.API()


    @api.route("/book", methods=["POST"])
    @api.expect(
        {
            401: "Invalid access or refresh token",
            403: "Please verify your account",
        }
    )
    async def book_create(req, resp):
        resp.media = {"msg": "created"}


@input / @output / @expect
-------
Putting `@input`, `@output` and `@expect` together.

::
    
    @api.route("/create", methods=["POST"])
    @api.input(BookSchema)
    @api.output(BookSchema)
    @api.expect(
        {
            401: "Invalid access or refresh token",
            409: "Book already exists",
        }
    )
    async def create(req, resp, *, data):
        """Create book"""

        book = Book(**data)
        session.add(book)
        session.commit()

        resp.obj = book


Authentication
--------------

This part explains how to use authentication mechanisms in Dyne, including `BasicAuth`, `TokenAuth`, `DigestAuth`, and `MultiAuth`.
It also includes examples of custom error handling and role-based authorization.

Note: In the `verify_password`, `verify_token`, and `get_password` callbacks, you can return any object (or class) that represents your `user`. 
The authenticated user can then be accessed through `request.state.user`.


Basic Authentication
--------------------
`BasicAuth` verifies user credentials (username and password) and provides access to protected routes.

Sample code:

.. code-block:: python

    import dyne
    from dyne.ext.auth import BasicAuth

    api = dyne.API()

    users = dict(john="password", admin="password123")

    basic_auth = BasicAuth()

    @basic_auth.verify_password
    async def verify_password(username, password):
        if username in users and users.get(username) == password:
            return username
        return None

    @basic_auth.error_handler
    async def error_handler(req, resp, status_code=401):
        resp.text = "Basic Custom Error"
        resp.status_code = status_code

    @api.route("/{greeting}")
    @api.authenticate(basic_auth)
    async def basic_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

Make a basic authentication request:

.. code-block:: bash

    http -a john:password get http://127.0.0.1:5042/Hello


Token Authentication
--------------------
`TokenAuth` authenticates requests based on bearer tokens.

Sample code:

.. code-block:: python

    token_auth = TokenAuth()

    @token_auth.verify_token
    async def verify_token(token):
        if token == "valid_token":
            return "admin"
        return None

    @token_auth.error_handler
    async def token_error_handler(req, resp, status_code=401):
        resp.text = "Token Custom Error"
        resp.status_code = status_code

    @api.route("/{greeting}")
    @api.authenticate(token_auth)
    async def token_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

Make a token authentication request:

.. code-block:: bash

    http get http://127.0.0.1:5042/Hi "Authorization: Bearer valid_token"


Digest Authentication
---------------------
`DigestAuth` is a more secure method than Basic Auth for protecting routes.

Sample code:

.. code-block:: python

    digest_auth = DigestAuth()

    @digest_auth.get_password
    async def get_password(username):
        return users.get(username)

    @digest_auth.error_handler
    async def digest_error_handler(req, resp, status_code=401):
        resp.text = "Digest Custom Error"
        resp.status_code = status_code

    @api.route("/{greeting}")
    @api.authenticate(digest_auth)
    async def digest_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

Make a digest authentication request:

.. code-block:: bash

    http --auth-type=digest -a john:password get http://127.0.0.1:5042/Hola

You can also use precomputed hashes for passwords:

Note: Make sure the `realm` is the same as that used in the `DigestAuth` backend

.. code-block:: python

    @digest_auth.get_password
    async def get_ha1_pw(username):
        password = users.get(username)
        realm = "Authentication Required"
        return hashlib.md5(f"{username}:{realm}:{password}".encode("utf-8")).hexdigest()


Custom `Nonce` and `Opaque` generation and verification callbacks:

Sample code:

.. code-block:: python

    my_nonce = "37e9292aecca04bd7e834e3e983f5d4"
    my_opaque = "f8bf1725d7a942c6511cc7ed38c169fo"

    @digest_auth.generate_nonce
    async def gen_nonce(request):
        return my_nonce

    @digest_auth.verify_nonce
    async def ver_nonce(request, nonce):
        return hmac.compare_digest(my_nonce, nonce)

    @digest_auth.generate_opaque
    async def gen_opaque(request):
        return my_opaque

    @digest_auth.verify_opaque
    async def ver_opaque(request, opaque):
        return hmac.compare_digest(my_opaque, opaque)


Role-Based Authorization
------------------------
You can restrict routes to specific roles using role-based authorization with any of the backends.

Sample code using the `basic_auth` backends:

.. code-block:: python

    users = dict(john="password", admin="password123")
    roles = {"john": "user", "admin": ["user", "admin"]}

    @basic_auth.get_user_roles
    async def get_user_roles(user):
        return roles.get(user)

    # Both `john` and `admin` can access this ruote
    @api.route("/welcome")
    @api.authenticate(basic_auth, role="user")
    async def welcome(req, resp):
        resp.text = f"welcome back {req.state.user}!"


    # Only `admin` can access this ruote
    @api.route("/admin")
    @api.authenticate(basic_auth, role="admin")
    async def admin(req, resp):
        resp.text = f"Hello {req.state.user}, you are an admin!"

Make a role-based  authentication request:

.. code-block:: bash

    http -a john:password get http://127.0.0.1:5042/welcome
    http -a admin:password123 get http://127.0.0.1:5042/admin


Multi Authentication
--------------------
`MultiAuth` allows for multiple authentication schemes, enabling a flexible authentication strategy.

Sample code:

.. code-block:: python

    multi_auth = MultiAuth(digest_auth, token_auth, basic_auth)

    @api.route("/{greeting}")
    @api.authenticate(multi_auth)
    async def multi_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

Make a request using any of the configured authentication schemes:

.. code-block:: bash

    # Basic Auth
    http -a john:password get http://127.0.0.1:5042/Hi

    # Token Auth
    http get http://127.0.0.1:5042/Hi "Authorization: Bearer valid_token"

    # Digest Auth
    http --auth-type=digest -a john:password get http://127.0.0.1:5042/Hi


Automatic OpenAPI Documentation Generation
------------------------------------------

Dyne includes built-in support for self-documentation through OpenAPI, with seamless integration for both `Marshmallow` and `Pydantic`.
By using the `authenticate`, `input`, `output`, and `expect` decorators, you can easily generate self-documentation for your API endpoints, 
covering authorization schemes, request bodies, responses, and errors.


First, define the overview documentation string for your API. This string should provide a general description of your API.

Example:

::

    doc = \"\"\" 
    API Documentation

    This module provides an interface to interact with the user management API. It allows for operations such as retrieving user information, creating new users, updating existing users, and deleting users.

    Base URL:
        https://api.example.com/v1

    Authentication:
        All API requests require an API key. Include your API key in the Authorization header as follows:
        Authorization: Bearer YOUR_API_KEY

    For further inquiries or support, please contact support@example.com.
    \"\"\"

Next, assign this `doc` string to the `api.state.doc` variable in your Dyne application

::

    api = dyne.API()
    api.state.doc = doc


After setting the overview documentation, you can use the following decorators to define the specific behavior of each API endpoint.

- **`@api.authenticate`**: Specifies the authentication scheme for the endpoint.
- **`@api.input`**: Defines the expected input schema for the request body.
- **`@api.output`**: Specifies the output schema for the response.
- **`@api.expect`**: Maps specific response codes to their descriptions, e.g., error responses.

Example: Creating a Book
Below is an example demonstrating how to use these decorators for an endpoint that creates a new book entry, including file upload with validation.

::

    from marshmallow import Schema, fields
    from dyne.fields.mashmellow import FileField

    class BookSchema(Schema):
        id = fields.Integer(dump_only=True)
        price = fields.Float()
        title = fields.Str()
        cover = fields.Str()

    class BookCreateSchema(Schema):
        price = fields.Float()
        title = fields.Str()
        image = FileField(allowed_extensions=["png", "jpg"], max_size=5 * 1024 * 1024)  # Built-in File Extension and Size Validation.

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
        await image.save(image.filename)  # The image is already validated for extension and size

        book = Book(**data, cover=image.filename)
        session.add(book)
        session.commit()

        resp.obj = book


Once you have decorated your endpoint and set the overview documentation, visit the `/docs` URL in your application to see the automatically generated API documentation, including:

- API Overview (base URL, authentication, etc.)
- Authorization scheme
- Request body with input validation
- Output response schema
- Defined error responses

This approach simplifies the process of maintaining up-to-date API documentation for your users.


Mount a WSGI / ASGI Apps (e.g. Flask, Starlette,...)
----------------------------------------------------

dyne gives you the ability to mount another ASGI / WSGI app at a subroute::

    import dyne
    from flask import Flask

    api = dyne.API()
    flask = Flask(__name__)

    @flask.route('/')
    def hello():
        return 'hello'

    api.mount('/flask', flask)

That's it!

Single-Page Web Apps
--------------------

If you have a single-page webapp, you can tell dyne to serve up your ``static/index.html`` at a route, like so::

    api.add_route("/", static=True)

This will make ``index.html`` the default response to all undefined routes.

Reading / Writing Cookies
-------------------------

dyne makes it very easy to interact with cookies from a Request, or add some to a Response::

    >>> resp.cookies["hello"] = "world"

    >>> req.cookies
    {"hello": "world"}


To set cookies directives, you should use `resp.set_cookie`::

    >>> resp.set_cookie("hello", value="world", max_age=60)

Supported directives:

* ``key`` - **Required**
* ``value`` - [OPTIONAL] - Defaults to ``""``. 
* ``expires`` - Defaults to ``None``.
* ``max_age`` - Defaults to ``None``.
* ``domain`` - Defaults to ``None``.
* ``path`` - Defaults to ``"/"``.
* ``secure`` - Defaults to ``False``.
* ``httponly`` - Defaults to ``True``.

For more information see `directives <https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Set-Cookie#Directives>`_


Using Cookie-Based Sessions
---------------------------

dyne has built-in support for cookie-based sessions. To enable cookie-based sessions, simply add something to the ``resp.session`` dictionary::

    >>> resp.session['username'] = 'john'

A cookie called ``dyne-Session`` will be set, which contains all the data in ``resp.session``. It is signed, for verification purposes.

You can easily read a Request's session data, that can be trusted to have originated from the API::

    >>> req.session
    {'username': 'john'}

**Note**: if you are using this in production, you should pass the ``secret_key`` argument to ``API(...)``::

    api = dyne.API(secret_key=os.environ['SECRET_KEY'])

Using ``before_request``
------------------------

If you'd like a view to be executed before every request, simply do the following::

    @api.route(before_request=True)
    def prepare_response(req, resp):
        resp.headers["X-Pizza"] = "42"

Now all requests to your HTTP Service will include an ``X-Pizza`` header.

For ``websockets``::

    @api.route(before_request=True, websocket=True)
    def prepare_response(ws):
        await ws.accept()


WebSocket Support
-----------------

dyne supports WebSockets::

    @api.route('/ws', websocket=True)
    async def websocket(ws):
        await ws.accept()
        while True:
            name = await ws.receive_text()
            await ws.send_text(f"Hello {name}!")
        await ws.close()

Accepting the connection::

    await websocket.accept()

Sending and receiving data::

    await websocket.send_{format}(data) 
    await websocket.receive_{format}(data)

Supported formats: ``text``, ``json``, ``bytes``.

Closing the connection::

    await websocket.close()

Using Requests Test Client
--------------------------

dyne comes with a first-class, well supported test client for your ASGI web services: **Requests**.

Here's an example of a test (written with pytest)::

    import myapi

    @pytest.fixture
    def api():
        return myapi.api

    def test_response(api):
        hello = "hello, world!"

        @api.route('/some-url')
        def some_view(req, resp):
            resp.text = hello

        r = api.requests.get(url=api.url_for(some_view))
        assert r.text == hello

HSTS (Redirect to HTTPS)
------------------------

Want HSTS (to redirect all traffic to HTTPS)?

::

    api = dyne.API(enable_hsts=True)


Boom.

CORS
----

Want `CORS <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS/>`_ ?

::

    api = dyne.API(cors=True)


The default parameters used by **dyne** are restrictive by default, so you'll need to explicitly enable particular origins, methods, or headers, in order for browsers to be permitted to use them in a Cross-Domain context.

In order to set custom parameters, you need to set the ``cors_params`` argument of ``api``, a dictionary containing the following entries:

* ``allow_origins`` - A list of origins that should be permitted to make cross-origin requests. eg. ``['https://example.org', 'https://www.example.org']``. You can use ``['*']`` to allow any origin.
* ``allow_origin_regex`` - A regex string to match against origins that should be permitted to make cross-origin requests. eg. ``'https://.*\.example\.org'``.
* ``allow_methods`` - A list of HTTP methods that should be allowed for cross-origin requests. Defaults to `['GET']`. You can use ``['*']`` to allow all standard methods.
* ``allow_headers`` - A list of HTTP request headers that should be supported for cross-origin requests. Defaults to ``[]``. You can use ``['*']`` to allow all headers. The ``Accept``, ``Accept-Language``, ``Content-Language`` and ``Content-Type`` headers are always allowed for CORS requests.
* ``allow_credentials`` - Indicate that cookies should be supported for cross-origin requests. Defaults to ``False``.
* ``expose_headers`` - Indicate any response headers that should be made accessible to the browser. Defaults to ``[]``.
* ``max_age`` - Sets a maximum time in seconds for browsers to cache CORS responses. Defaults to ``60``.

Trusted Hosts
-------------

Make sure that all the incoming requests headers have a valid ``host``, that matches one of the provided patterns in the ``allowed_hosts`` attribute, in order to prevent HTTP Host Header attacks.

A 400 response will be raised, if a request does not match any of the provided patterns in the ``allowed_hosts`` attribute.

::

    api = dyne.API(allowed_hosts=['example.com', 'tenant.example.com'])

* ``allowed_hosts`` - A list of allowed hostnames. 

Note:

* By default, all hostnames are allowed.
* Wildcard domains such as ``*.example.com`` are supported.
* To allow any hostname use ``allowed_hosts=["*"]``.
