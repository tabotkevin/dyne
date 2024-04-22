Feature Tour
============


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


OpenAPI Schema Support
----------------------

dyne comes with built-in support for OpenAPI / marshmallow and Pydantic::

    import dyne
    from marshmallow import Schema, fields

    api = dyne.API()

    @api.schema("Pet")
    class PetSchema(Schema):
        name = fields.Str()

    @api.route("/")
    def route(req, resp):
        """A cute furry animal endpoint.
        ---
        get:
            description: Get a random pet
            responses:
                200:
                    description: A pet to be returned
                    content:  
                        application/json: 
                            schema: 
                                $ref: '#/components/schemas/Pet'                         
        """
        resp.media = PetSchema().dump({"name": "little orange"})

::

    >>> r = api.session().get("http://;/schema.yml")

    >>> print(r.text)
    components:
      parameters: {}
      responses: {}
      schemas:
        Pet:
          properties:
            name: {type: string}
          type: object
      securitySchemes: {}
    info:
      contact: {email: support@example.com, name: API Support, url: 'http://www.example.com/support'}
      description: This is a sample server for a pet store.
      license: {name: Apache 2.0, url: 'https://www.apache.org/licenses/LICENSE-2.0.html'}
      termsOfService: http://example.com/terms/
      title: Web Service
      version: 1.0
    openapi: 3.0.2
    paths:
      /:
        get:
          description: Get a random pet
          responses:
            200: {description: A pet to be returned, schema: $ref: "#/components/schemas/Pet"}
    tags: []


Interactive Documentation
-------------------------

dyne can automatically supply API Documentation for you. Using the example above

This will make ``/docs`` render interactive documentation for your API.


Request validation
-------
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


Response Deserialization
-------
Dyne provides the functionality to deserialize SQLAlchemy objects or queries into JSON responses using Marshmallow or Pydantic schemas. This is achieved by using the `@output` decorator and setting `resp.obj` within the endpoint, which allows Dyne to deserialize the response as specified by the schema.

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

    import dune

    api = dune.API()


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

    >>> resp.session['username'] = 'kennethreitz'

A cookie called ``dyne-Session`` will be set, which contains all the data in ``resp.session``. It is signed, for verification purposes.

You can easily read a Request's session data, that can be trusted to have originated from the API::

    >>> req.session
    {'username': 'kennethreitz'}

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
