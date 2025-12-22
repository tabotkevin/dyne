Feature Tour
============

Introduction
------------

Dyne brings simplicity and elegance to API development, offering built-in features such as:

- **Authentication**: Support for `BasicAuth`, `TokenAuth`, and `DigestAuth`.
- **Input Validation**: The `@input` decorator makes validating request bodies easy.
- **Response Serialization**: Use the `@output` decorator to serialize responses automatically.
- **OpenAPI Documentation**: Full self-generated OpenAPI documentation with seamless integration for both `Pydantic` and `Marshmallow` schemas.

Here's how you can get started:

::
    
    import dyne
    from dyne.ext.auth import BasicAuth


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

**Schemas: Marshmallow**

.. code-block:: python

    from dyne.ext.io.marshmallow.fields import FileField

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

    from dyne.ext.io.marshmallow import input, output, expect

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

Dyne provides built-in support for integrating ``GraphQL`` using both ``Strawberry`` and ``Graphene``.

To ensure consistent behavior, proper plugin isolation, and reliable runtime validation, Dyne requires that GraphQL schemas be created using Dyne-provided Schema classes, 
which act as thin wrappers around the underlying GraphQL backends.

With either backend, you can define GraphQL schemas containing queries, mutations, or both, and expose them via a ``GraphQLView``.

The view is added to a Dyne API route (for example, ``/graphql``). The endpoint can then be accessed through a GraphQL client, your browser, or tools such as Postman.
When accessed from a browser, the endpoint will render a GraphiQL interface, allowing you to easily explore and interact with your GraphQL schema.


**Installation**
Dyne’s GraphQL support is provided via optional dependencies.
Install Dyne along with the backend you intend to use.

* Strawberry:
.. code-block:: bash

    pip install dyne[strawberry]


* Graphene:
.. code-block:: bash

    pip install dyne[graphene]

Only install the backend(s) you plan to use. Dyne does not auto-detect GraphQL backends.


**Choosing a GraphQL Backend**

Dyne does not auto-detect which GraphQL backend you are using.

Instead, you explicitly opt into a backend by importing the corresponding Schema class:

* ``dyne.ext.graphql.strawberry.Schema``
* ``dyne.ext.graphql.graphene.Schema``

This explicit import ensures:

* Clear backend selection
* No accidental mixing of GraphQL backends
* Predictable runtime behavior and better error messages


.. contents::
   :local:
   :depth: 1

1. Strawberry GraphQL
---------------------

The following example demonstrates how to set up a ``Strawberry`` schema and route it through Dyne’s ``GraphQLView``:

.. code-block:: python

    import strawberry
    import dyne
    from dyne.ext.graphql import GraphQLView
    from dyne.ext.graphql.strawberry import Schema

    api = dyne.API()

    # Define a response type for mutations
    @strawberry.type
    class MessageResponse:
        ok: bool
        message: str

    # Define a Mutation class
    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def create_message(self, name: str, message: str) -> MessageResponse:
            return MessageResponse(ok=True, message=f"Message from {name}: {message}")

    # Define a Query class
    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self, name: str = "stranger") -> str:
            return f"Hello {name}"

    # Create the schema
    schema = Schema(query=Query, mutation=Mutation)

    # Create GraphQL view and add it to the API
    view = GraphQLView(api=api, schema=schema)
    api.add_route("/graphql", view)


You can make use of Dyne’s `Request` and `Response` objects in your GraphQL resolvers through ``info.context['request']`` and ``info.context['response']``. 
This allows you to access and manipulate request/response data within your GraphQL operations.

2. Graphene GraphQL
---------------------

The following example demonstrates how to set up a **Graphene** schema and route it through Dyne’s `GraphQLView`:

.. code-block:: python

    import graphene
    import dyne
    from dyne.ext.graphql import GraphQLView
    from dyne.ext.graphql.graphene import Schema

    api = dyne.API()

    # Define a Mutation for Graphene
    class CreateMessage(graphene.Mutation):
        class Arguments:
            name = graphene.String(required=True)
            message = graphene.String(required=True)

        ok = graphene.Boolean()
        message = graphene.String()

        def mutate(self, info, name, message):
            return CreateMessage(ok=True, message=f"Message from {name}: {message}")

    # Define a Mutation class
    class Mutation(graphene.ObjectType):
        create_message = CreateMessage.Field()

    # Define a Query class
    class Query(graphene.ObjectType):
        hello = graphene.String(name=graphene.String(default_value="stranger"))

        def resolve_hello(self, info, name):
            return f"Hello {name}"

    # Create the schema
    schema = Schema(query=Query, mutation=Mutation)

    # Create GraphQL view and add it to the API
    view = GraphQLView(api=api, schema=schema)
    api.add_route("/graphql", view)

Just like with **Strawberry**, Dyne’s `Request` and `Response` objects can be accessed in your GraphQL resolvers using ``info.context['request']`` and ``info.context['response']``.


Important Notes
---------------

* Do not pass raw `strawberry.Schema`` or `graphene.Schema` instances directly to `GraphQLView`.
* Always use the Schema class provided by Dyne for the backend you choose.
* Mixing GraphQL backends in a single application is not supported and will raise a runtime error.
* GraphQL support is optional and requires installing the appropriate extra.


GraphQL Queries and Mutations
---------------------

Once your API is set up with either **Strawberry** or **Graphene**, you can interact with it by making queries and mutations via the `/graphql` route.

Here are some example GraphQL queries and mutations you can use:

**Example Query 1: Fetch a default hello message**

.. code-block:: graphql

    query {
      hello
    }

**Expected Response:**

.. code-block:: json

    {
      "data": {
        "hello": "Hello stranger"
      }
    }


**Example Query 2: Fetch a personalized hello message**

.. code-block:: graphql

    query {
      hello(name: "Alice")
    }

**Expected Response:**

.. code-block:: json

    {
      "data": {
        "hello": "Hello Alice"
      }
    }


**Example Mutation: Create a message**

.. code-block:: graphql

    mutation {
      createMessage(name: "Alice", message: "GraphQL is awesome!") {
        ok
        message
      }
    }

**Expected Response:**

.. code-block:: json

    {
      "data": {
        "createMessage": {
          "ok": true,
          "message": "Message from Alice: GraphQL is awesome!"
        }
      }
    }


For more advanced configurations or additional examples, refer to the respective documentation for **Strawberry** and **Graphene**.


Request validation
------------------

Dyne provides specialized extensions for validating incoming requests against **Pydantic** models or **Marshmallow** schemas. Instead of a generic decorator, you import the `input` decorator specifically for the library you are using.

Validation is supported for various sources:

* **media**: Request body (JSON, Form, YAML). This is the default.
* **query**: URL query parameters.
* **headers**: Request headers.
* **cookies**: Browser cookies.

Data Injection
~~~~~~~~~~~~~~

Once validated, the data is injected into your handler as a keyword argument. 
* By default, the argument name is the value of the ``location`` (e.g., ``query``, ``headers``).
* For ``media``, the default argument name is ``data``.
* You can override this using the ``key`` parameter.

Pydantic Validation
~~~~~~~~~~~~~~~~~~~

To use Pydantic, import the decorator from `dyne.ext.io.pydantic`.

.. code-block:: python

  from pydantic import BaseModel, Field
  from dyne.ext.io.pydantic import input
  import dyne

  api = dyne.API()

  class Book(BaseModel):
      title: str
      price: float = Field(gt=0)

  @api.route("/books", methods=["POST"])
  @input(Book)  # Default location="media", default key="data"
  async def create_book(req, resp, *, data: Book):
      # 'data' is a validated Pydantic instance
      print(f"Creating {data['title']}")
      resp.media = {"status": "created"}

Marshmallow Validation
~~~~~~~~~~~~~~~~~~~~~~

To use Marshmallow, import the decorator from ``dyne.ext.io.marshmallow``.

.. code-block:: python

    from marshmallow import Schema, fields
    from dyne.ext.io.marshmallow import input
    import dyne

    api = dyne.API()

    class QuerySchema(Schema):
        page = fields.Int(load_default=1)
        limit = fields.Int(load_default=10)

    @api.route("/books", methods=["GET"])
    @input(QuerySchema, location="query") # key defaults to "query"
    async def list_books(req, resp, *, query):
        # 'query' is a validated dictionary
        page = query['page']
        resp.media = {"results": [], "page": page}

Advanced Locations and Keys
~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can validate multiple sources on a single endpoint and customize the variable names injected into the function.

.. code-block:: python

  class HeaderSchema(BaseModel):
      x_api_key: str = Field(alias="X-API-Key")

  @api.route("/secure-data")
  @input(HeaderSchema, location="headers")
  @input(QuerySchema, location="query", key="params")
  async def secure_endpoint(req, resp, *, headers, params):
      # Query params are available as 'params'
      print(f"API Keys: {headers['x_api_key']})
      print(f"Query: {params}")
      resp.media = {"data": "secret stuff"}

Key Differences
~~~~~~~~~~~~~~~

+-----------------+-----------------------------------+-----------------------------------------+
| Feature         | Pydantic                          | Marshmallow                             |
+=================+===================================+=========================================+
| **Import**      | ``dyne.ext.io.pydantic.input``    | ``dyne.ext.io.marshmallow.input``       |
+-----------------+-----------------------------------+-----------------------------------------+
| **Return Type** | A native Python dictionary.       | A native Python dictionary.             | 
+-----------------+-----------------------------------+-----------------------------------------+
| **OpenAPI**     | Automatically generates JSON      | Integrates with APISpec                 |
|                 | Schema from model fields.         | Marshmallow plugin.                     |
+-----------------+-----------------------------------+-----------------------------------------+


Response Serialization
----------------------

Dyne simplifies the process of converting Python objects, SQLAlchemy models, or database queries into JSON responses. This is managed by the `@output` decorator. Instead of manually assigning data to `resp.media`, you assign your data to `resp.obj`, and the extension handles the serialization based on the provided schema.

The `@output` decorator supports:

* **status_code**: The HTTP status code for the response (default is 200).
* **header**: A schema to validate and document response headers.
* **description**: A string used for OpenAPI documentation to describe the response.

Pydantic Output
~~~~~~~~~~~~~~~

To serialize using Pydantic, import the decorator from ``dyne.ext.io.pydantic``. 

**Note:** When working with SQLAlchemy or other ORMs, ensure your Pydantic model is configured with ``from_attributes=True`` (Pydantic V2) or ``orm_mode=True`` (Pydantic V1).

.. code-block:: python

    from pydantic import BaseModel, ConfigDict
    from dyne.ext.io.pydantic import output
    import dyne

    api = dyne.API()

    # Define an example SQLAlchemy model
    class Book(Base):
        __tablename__ = "books"
        id = Column(Integer, primary_key=True)
        price = Column(Float)
        title = Column(String)

    class BookSchema(BaseModel):
        id: int
        title: str
        price: float
        
        # Required for SQLAlchemy integration
        model_config = ConfigDict(from_attributes=True)

    @api.route("/books/{id}")
    @output(BookSchema)
    async def get_book(req, resp, id):
        # Fetch a SQLAlchemy object
        book = session.query(Book).get(id)
        
        # Assign the object to resp.obj
        # The extension converts the ORM model to JSON automatically
        resp.obj = book

    @api.route("/all-books")
    @output(BookSchema)
    async def list_all(req, resp):
        # resp.obj can also be a list or a query object
        resp.obj = session.query(Book).all()

Marshmallow Output
~~~~~~~~~~~~~~~~~~

To serialize using Marshmallow, import the decorator from `dyne.ext.io.marshmallow`.

.. code-block:: python

    from marshmallow import Schema, fields
    from dyne.ext.io.marshmallow import output
    import dyne

    api = dyne.API()

    # Define an example SQLAlchemy model
    class Book(Base):
        __tablename__ = "books"
        id = Column(Integer, primary_key=True)
        price = Column(Float)
        title = Column(String)

    class BookSchema(Schema):
        id = fields.Int()
        title = fields.Str()
        price = fields.Float()

    books = BookSchema(many=True)

    @api.route("/books/{id}")
    @output(BookSchema)
    async def get_book(req, resp, id):
        # Fetch a SQLAlchemy object
        book = session.query(Book).get(id)
        
        # Assign the object to resp.obj
        # The extension converts the ORM model to JSON automatically
        resp.obj = book

    @api.route("/all-books")
    @output(books)
    async def list_all(req, resp):
        # resp.obj can also be a list or a query object
        resp.obj = session.query(Book).all()


Manual Documentation with ``@expect``
-------------------------------------

The `@expect` decorator is used primarily for **OpenAPI documentation**. It allows you to define expected response status codes and descriptions that aren't necessarily part of the primary "success" flow.

This is particularly useful for documenting error states (401, 404, 409) or alternative success messages.

.. code-block:: python

  from dyne.ext.io.pydantic import expect

  @api.route("/create-book", methods=["POST"])
  @expect({
      201: "Book created successfully",
      401: "Invalid authentication credentials",
      409: "A book with this ISBN already exists"
  })
  async def create_book(req, resp):
      # Logic here...
      resp.status_code = 201
      resp.media = {"msg": "created"}


Unified Example: ``@input``, ``@output``, and ``@expect``
---------------------------------------------------------

In a production endpoint, you will typically use all three decorators together to create a fully validated and documented API.

.. code-block:: python

  from dyne.ext.io.pydantic import input
  from dyne.ext.io.pydantic import output
  from dyne.ext.io.pydantic import expect

  @api.route("/update-price/{id}", methods=["PATCH"])
  @input(PriceUpdateSchema)     # Validate request body
  @output(BookSchema)           # Serialize updated ORM object
  @expect({                        # Document potential errors
      403: "Insufficient permissions",
      404: "Book not found"
  })
  async def update_book_price(req, resp, id, *, data):
      book = session.query(Book).get(id)
      if not book:
          resp.status_code = 404
          return
          
      book.price = data.price
      session.commit()

      # The updated 'book' object is serialized back to the client
      resp.obj = book


Summary of Decorators
~~~~~~~~~~~~~~~~~~~~~


+-----------------+------------------------------------------+---------------------------------------+
| Decorator       | Primary Purpose                          | Core Mechanism                        |
+=================+==========================================+=======================================+
| ``@input``      | Request Validation                       | Injects data into handler kwargs.     |
+-----------------+------------------------------------------+---------------------------------------+
| ``@output``     | Response Serialization                   | Converts ``resp.obj`` to JSON.        |
+-----------------+------------------------------------------+---------------------------------------+
| ``@expect``     | Documentation                            | Adds responses to OpenAPI spec.       |
+-----------------+------------------------------------------+---------------------------------------+


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
        All api.client require an API key. Include your API key in the Authorization header as follows:
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

        r = api.client.get(url=api.url_for(some_view))
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
