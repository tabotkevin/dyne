Feature Tour
============

Introduction
------------

Dyne brings simplicity and elegance to API development, offering built-in features such as:

* **Authentication**: Support for `BasicAuth`, `TokenAuth`, and `DigestAuth`.
* **Input Validation**: The `@input` decorator makes validating request bodies easy.
* **Response Serialization**: Use the `@output` decorator to serialize responses automatically.
* **Request Contracts**: The ``@expect`` decorator allows you to document and enforce required headers, cookies, or specific request metadata.
* **Asynchronous Events**: Use the @webhook decorator to define and document the webhooks your application has.
* **OpenAPI Documentation**: Full self-generated OpenAPI documentation with seamless integration for both `Pydantic` and `Marshmallow` schemas.

Here's how you can get started:

::
    
    import dyne
    from dyne.ext.auth.backends import BasicAuth


    app = dyne.App()
    api = OpenAPI(app, description=description)

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

Example: Book Creation API
~~~~~~~~~~~~~~~~~~~~~~~~~~

This example demonstrates a clean and minimal API endpoint for creating a new book. The API supports file uploads with built-in validation for file extensions and file sizes.

.. code-block:: python

    import dyne
    from dyne.ext.auth import authenticate
    from dyne.ext.auth.backends import BasicAuth
    from dyne.ext.io.marshmallow import expect, input, output
    from dyne.ext.io.marshmallow.fields import FileField

    app = dyne.App()
    api = OpenAPI(app, description=description)
    basic_auth = BasicAuth()

    class Book(Base):  # SQLAlchemy Model
        __tablename__ = "books"
        id = Column(Integer, primary_key=True)
        price = Column(Float)
        title = Column(String)
        cover = Column(String, nullable=True)


    class BookSchema(Schema): # Schemas: Marshmallow
        id = fields.Integer(dump_only=True)
        price = fields.Float()
        title = fields.Str()
        cover = fields.Str()

    class BookCreateSchema(Schema):
        price = fields.Float()
        title = fields.Str()
        image = FileField(allowed_extensions=["png", "jpg"], max_size=5 * 1024 * 1024)  # Built-in file validation


    @app.route("/create", methods=["POST"])
    @authenticate(basic_auth, role="user")
    @input(BookCreateSchema, location="form")
    @output(BookSchema)
    @expect(
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

    @app.route("/{greeting}")
    class GreetingResource:
        def on_request(self, req, resp, *, greeting):   # or on_get...
            resp.text = f"{greeting}, world!"
            resp.headers.update({'X-Life': '42'})
            resp.status_code = app.status.HTTP_416


Background Tasks
----------------

Here, you can spawn off a background thread to run any function, out-of-request::

    @app.route("/")
    def hello(req, resp):

        @app.background.task
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

The view is added to a Dyne App route (for example, ``/graphql``). The endpoint can then be accessed through a GraphQL client, your browser, or tools such as Postman.
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

    app = dyne.App()

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
    view = GraphQLView(app=app, schema=schema)
    app.add_route("/graphql", view)


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

    app = dyne.App()

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
    view = GraphQLView(app=app, schema=schema)
    app.add_route("/graphql", view)

Just like with **Strawberry**, Dyne’s `Request` and `Response` objects can be accessed in your GraphQL resolvers using ``info.context['request']`` and ``info.context['response']``.


Important Notes
---------------

* Do not pass raw `strawberry.Schema`` or `graphene.Schema` instances directly to `GraphQLView`.
* Always use the Schema class provided by Dyne for the backend you choose.
* Mixing GraphQL backends in a single application is not supported and will raise a runtime error.
* GraphQL support is optional and requires installing the appropriate extra.


GraphQL Queries and Mutations
---------------------

Once your App is set up with either **Strawberry** or **Graphene**, you can interact with it by making queries and mutations via the `/graphql` route.

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

Dyne provides specialized extensions for validating incoming requests against **Pydantic** models or **Marshmallow** schemas. Instead of a generic decorator, you import the ``input`` decorator specifically for the library you are using.

Validation is supported for various sources:

* **media**: Request body (``json``, ``form``, ``yaml``). This is the default.
* **query**: URL query parameters.
* **header**: Request headers.
* **cookie**: Browser cookies.

Data Injection
~~~~~~~~~~~~~~

Once validated, the data is injected into your handler as a keyword argument. 
* By default, the argument name is the value of the ``location`` (e.g., ``query``, ``header``).
* For ``media``, the default argument name is ``data``.
* You can override this using the ``key`` parameter.

Pydantic Validation
~~~~~~~~~~~~~~~~~~~

To use Pydantic, import the decorator from `dyne.ext.io.pydantic`.

.. code-block:: python

  import dyne
  from pydantic import BaseModel, Field
  from dyne.ext.io.pydantic import input

  app = dyne.App()

  class Book(BaseModel):
      title: str
      price: float = Field(gt=0)

  @app.route("/books", methods=["POST"])
  @input(Book)  # Default location="media", default key="data"
  async def create_book(req, resp, *, data: Book):
      # 'data' is a validated Pydantic instance
      print(f"Creating {data['title']}")
      resp.media = {"status": "created"}

Marshmallow Validation
~~~~~~~~~~~~~~~~~~~~~~

To use Marshmallow, import the decorator from ``dyne.ext.io.marshmallow``.

.. code-block:: python

    import dyne
    from marshmallow import Schema, fields
    from dyne.ext.io.marshmallow import input

    app = dyne.App()

    class QuerySchema(Schema):
        page = fields.Int(load_default=1)
        limit = fields.Int(load_default=10)

    @app.route("/books", methods=["GET"])
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

  @app.route("/secure-data")
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


Response Serialization
----------------------

Dyne simplifies the process of converting Python objects, SQLAlchemy models, or database queries into JSON responses. This is managed by the `@output` decorator. Instead of manually assigning data to `resp.media`, you assign your data to `resp.obj`, and the extension handles the serialization based on the provided schema.

The ``@output`` decorator supports:

* **status_code**: The HTTP status code for the response (default is 200).
* **header**: A schema to validate and document response headers.
* **description**: A string used for OpenAPI documentation to describe the response.

Pydantic Output
~~~~~~~~~~~~~~~

To serialize using Pydantic, import the decorator from ``dyne.ext.io.pydantic``. 

**Note:** When working with SQLAlchemy or other ORMs, ensure your Pydantic model is configured with ``from_attributes=True`` (Pydantic V2) or ``orm_mode=True`` (Pydantic V1).

.. code-block:: python

    import dyne
    from pydantic import BaseModel, ConfigDict
    from dyne.ext.io.pydantic import output

    app = dyne.App()

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

    @app.route("/books/{id}")
    @output(BookSchema)
    async def get_book(req, resp, id):
        # Fetch a SQLAlchemy object
        book = session.query(Book).get(id)
        
        # Assign the object to resp.obj
        # The extension converts the ORM model to JSON automatically
        resp.obj = book

    @app.route("/all-books")
    @output(BookSchema)
    async def list_all(req, resp):
        # resp.obj can also be a list or a query object
        resp.obj = session.query(Book).all()

Marshmallow Output
~~~~~~~~~~~~~~~~~~

To serialize using Marshmallow, import the decorator from ``dyne.ext.io.marshmallow``.

.. code-block:: python

    from marshmallow import Schema, fields
    from dyne.ext.io.marshmallow import output
    import dyne

    app = dyne.App()

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

    @app.route("/books/{id}")
    @output(BookSchema)
    async def get_book(req, resp, id):
        # Fetch a SQLAlchemy object
        book = session.query(Book).get(id)
        
        # Assign the object to resp.obj
        # The extension converts the ORM model to JSON automatically
        resp.obj = book

    @app.route("/all-books")
    @output(books)
    async def list_all(req, resp):
        # resp.obj can also be a list or a query object
        resp.obj = session.query(Book).all()


API Documentation with ``@expect``
-----------------------------------

The ``@expect`` decorator is a powerful tool for **OpenAPI (Swagger) documentation**. While your primary success response is usually handled by ``@output``, ``@expect`` allows you to document **additional HTTP responses**—such as authentication errors, validation failures, or conflicts—that an endpoint might return.

The decorator is flexible and supports three distinct formats depending on the level of detail required for your API specification.Instead of a generic decorator, you import the `input` decorator specifically for the library you are using.

* **Note:** Import the ``expect`` decorator specifically for the library you are using.

* Pydantic: ``dyne.ext.io.pydantic``.
* Marshmallow: ``dyne.ext.io.marshmallow``.


Usage Patterns
~~~~~~~~~~~~~~

1. Description-Only Responses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use this format for simple errors when the status code and a message are sufficient.

.. code-block:: python

    @app.route("/secure-data", methods=["GET"])
    @expect({
        401: 'Invalid access or refresh token',
        403: 'Insufficient permissions'
    })
    async def get_data(req, resp):
        # Logic here...
        pass


2. Schema-Only Responses
^^^^^^^^^^^^^^^^^^^^^^^^
Use this form when the response includes a **JSON body**, but the description can be inferred or is not necessary (e.g., "Unauthorized" for 401).

Sample Error Schemas
~~~~~~~~~~~~~~~~~~~~~

To provide structured error responses in your documentation, define your error schemss using Pydantic or Marshmallow:

.. code-block:: python

    # Pydantic example
    from pydantic import BaseModel, Field

    class InvalidTokenSchema(BaseModel):
        error: str = Field("token_expired", description="The error code")
        message: str = Field(..., description="Details about the token failure")

    class InsufficientPermissionsSchema(BaseModel):
        error: str = "forbidden"
        required_role: str = "admin"


    # Marshmallow example
    from marshmallow import Schema, fields

    class InvalidTokenSchema(Schema):
        error = fields.String(
            dump_default="token_expired",
            metadata={"description": "The error code"},
        )
        message = fields.String(
            required=True,
            metadata={"description": "Details about the token failure"},
        )

    class InsufficientPermissionsSchema(Schema):
        error = fields.String(
            dump_default="forbidden",
            metadata={"description": "Error code"},
        )
        required_role = fields.String(
            dump_default="admin",
            metadata={"description": "Role required to access this resource"},
        )

.. code-block:: python

    @app.route("/secure-data", methods=["GET"])
    @expect({
        401: InvalidTokenSchema,
        403: InsufficientPermissionsSchema
    })
    async def get_data(req, resp):
        pass


3. Schema + Description Responses (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Use this form when you want **full control** over both the response schema and its description.

.. code-block:: python

    @app.route("/secure-data", methods=["GET"])
    @expect({
        401: (InvalidTokenSchema, 'Invalid access or refresh token'),
        403: (InsufficientPermissionsSchema, 'Requires elevated administrative privileges')
    })
    async def get_data(req, resp):
        pass


Webhooks
_________

The `@webhook` decorator is used to mark a standard endpoint as a webhook receiver. 
This attaches metadata to the route, allowing Dyne to identify it in generated documentation (like OpenAPI Callbacks) or for internal routing.

The decorator is flexible and supports two calling conventions:

* **Note:** Import the ``expect`` decorator specifically for the library you are using.

* Pydantic: ``dyne.ext.io.pydantic``.
* Marshmallow: ``dyne.ext.io.marshmallow``.

1. Basic Usage (Implicit Naming)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

When used without parentheses, the webhook uses the function name as its default identifier.

.. code-block:: python

@app.route("/events", methods=["POST"])
@webhook
async def handle_event(req, resp):
    pass


2. Explicit Naming
~~~~~~~~~~~~~~~~~~

You can provide a specific name for the webhook using the `name` argument. This is useful when the external service requires a specific endpoint identifier that differs from your function name.

.. code-block:: python

@app.route("/transaction", methods=["POST"])
@webhook(name="transaction_callback")
async def process_payment(req, resp):
    pass


* **Note:** A function decorated with ``@webhook`` automatically inherits the HTTP method defined in the ``@app.route`` decorator. For example, if your route is configured for ``POST``, the webhook documentation will reflect that it expects a ``POST`` request from the external caller.

Example
^^^^^^^

.. code-block:: python

    @app.route("/transaction", methods=["POST"])
    @webhook(name="transaction")
    @input(BookSchema)
    async def purchase_book(req, resp, *, data):
        """
        Receives a book purchase notification and processes it asynchronously.
        """
        @app.background.task
        def process(book):
            # Simulate heavy processing
            time.sleep(2)
            print(f"Processing webhook for: {book['title']}")

        process(data)
        resp.media = {"status": "Received!"}


Unified Example: ``@input``, ``@output``, ``@expect`` and ``@webhook``
----------------------------------------------------------------------

In a production endpoint, you will typically use all three decorators together to create a fully validated and documented API using the OpenAPI extension.

.. code-block:: python

  import dyne
  from dyne.exceptions import abort
  from dyne.ext.io.pydantic import expect, input, output, webhook
  from dyne.ext.openapi import OpenAPI

  app = dyne.App()
  api = OpenAPI(app, description=description)

  @app.route("/update-price/{id}", methods=["PATCH"])
  @webhook                      # Documents this endpoint as a webhook.
  @input(PriceUpdateSchema)     # Validate request body.
  @output(BookSchema)           # Serialize updated ORM object.
  @expect({                     # Document potential errors.
      403: "Insufficient permissions",
      404: "Book not found"
  })
  async def update_book_price(req, resp, id, *, data):
      book = session.query(Book).get(id)
      if not book:
          abort(404)
  
      book.price = data.price
      session.commit()

      # The updated 'book' object is serialized back to the client
      resp.obj = book


Summary of Decorators
~~~~~~~~~~~~~~~~~~~~~

+-----------------+------------------------------------------+----------------------------------------------+
| Decorator       | Primary Purpose                          | Core Mechanism                               |
+=================+==========================================+==============================================+
| ``@input``      | Request Validation                       | Injects data into handler kwargs.            |
+-----------------+------------------------------------------+----------------------------------------------+
| ``@output``     | Response Serialization                   | Converts ``resp.obj`` to JSON.               |
+-----------------+------------------------------------------+----------------------------------------------+
| ``@expect``     | Documentation                            | Adds responses to OpenAPI spec.              |
+-----------------+------------------------------------------+----------------------------------------------+
| ``@webhook``    | Documentation                            | Adds endpoint as a webhook in OpenAPI spec.  |
+-----------------+------------------------------------------+----------------------------------------------+


Authentication
______________

Dyne provides a robust authentication system through its ``auth`` extension. By separating the **Backend** logic (how credentials are verified) from the **Decorator** (how the route is protected), Dyne allows for a highly flexible security architecture.

All authentication backends are located in ``dyne.ext.auth.backends``, while the protection decorator is in ``dyne.ext.auth``.

The User Object
~~~~~~~~~~~~~~~

In the ``verify_password``, ``verify_token``, or ``get_password`` callbacks, you can return any object (e.g., a database model, a dictionary, or a string) that represents your user.

Once authenticated, this object is automatically attached to the request and can be accessed within your handlers via:

.. code-block:: python

  username = req.state.user


Basic Authentication
~~~~~~~~~~~~~~~~~~~~

``BasicAuth`` verifies a username and password sent via the standard HTTP Basic Auth header.

.. code-block:: python

    import dyne
    from dyne.ext.auth import authenticate
    from dyne.ext.auth.backends import BasicAuth

    app = dyne.App()
    users = dict(john="password", admin="password123")

    basic_auth = BasicAuth()

    @basic_auth.verify_password
    async def verify_password(username, password):
        if users.get(username) == password:
            return username
        return None

    @app.route("/greet")
    @authenticate(basic_auth)
    async def basic_greet(req, resp):
        resp.text = f"Hello, {req.state.user}!"


**Request Example:**

.. code-block:: bash

    http -a john:password GET http://localhost:5042/greet


Token Authentication
~~~~~~~~~~~~~~~~~~~~

``TokenAuth`` is used for Bearer token strategies (like JWTs or API Keys).

.. code-block:: python

    from dyne.ext.auth.backends import TokenAuth
    from dyne.ext.auth import authenticate

    token_auth = TokenAuth()

    @token_auth.verify_token
    async def verify_token(token):
        if token == "secret_key_123":
            return "David"
        return None

    @app.route("/dashboard")
    @authenticate(token_auth)
    async def secure_route(req, resp):
        resp.media = {"data": "Top Secret", "username": req.state.user}


**Request Example:**

.. code-block:: bash

    http GET http://localhost:5042/dashboard "Authorization: Bearer secret_key_123"


Digest Authentication
~~~~~~~~~~~~~~~~~~~~~

``DigestAuth`` provides a more secure alternative to Basic Auth by using a challenge-response mechanism that never sends the password in plaintext.

.. code-block:: python

    from dyne.ext.auth.backends import DigestAuth

    digest_auth = DigestAuth()

    @digest_auth.get_password
    async def get_password(username):
        return users.get(username)

    @app.route("/greet")
    @authenticate(digest_auth)
    async def digest_greet(req, resp):
        resp.text = f"Hello to {req.state.user}"


**Request Example:**

.. code-block:: bash

    http --auth-type=digest -a john:password get http://127.0.0.1:5042/greet


Advanced Digest Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For production environments, ``DigestAuth`` offers additional hooks to increase security and customize the challenge-response lifecycle.

Using Precomputed Hashes
~~~~~~~~~~~~~~~~~~~~~~~~

Storing plaintext passwords in a database is a security risk. You can instead store precomputed **HA1** hashes. 

.. note::
    The ``realm`` used to compute the hash must match the ``realm`` defined in your ``DigestAuth`` backend (the default is "Authentication Required").

.. code-block:: python

    import hashlib
    from dyne.ext.auth.backends import DigestAuth

    digest_auth = DigestAuth(realm="My App")

    @digest_auth.get_password
    async def get_ha1_pw(username):
        password = users.get(username) # In reality, fetch from DB
        realm = "My App"
        # Precompute HA1: md5(username:realm:password)
        return hashlib.md5(f"{username}:{realm}:{password}".encode("utf-8")).hexdigest()

Custom Nonce and Opaque Management
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To support stateless horizontally-scaled environments or to implement custom expiration logic, you can override the generation and verification of `nonce` and `opaque` values.

.. code-block:: python

    import hmac

    MY_SECRET_NONCE = "37e9292aecca04bd7e834e3e983f5d4"
    MY_SECRET_OPAQUE = "f8bf1725d7a942c6511cc7ed38c169fo"

    @digest_auth.generate_nonce
    async def gen_nonce(request):
        return MY_SECRET_NONCE

    @digest_auth.verify_nonce
    async def ver_nonce(request, nonce):
        return hmac.compare_digest(MY_SECRET_NONCE, nonce)

    @digest_auth.generate_opaque
    async def gen_opaque(request):
        return MY_SECRET_OPAQUE

    @digest_auth.verify_opaque
    async def ver_opaque(request, opaque):
        return hmac.compare_digest(MY_SECRET_OPAQUE, opaque)


Custom Error Handling
~~~~~~~~~~~~~~~~~~~~~

Every backend allows you to override the default error message and status_code by providing an ``error_handler``.

.. code-block:: python

    @basic_auth.error_handler
    async def custom_error(req, resp, status_code):
        resp.status_code = 401
        resp.media = {"error": "Custom Authentication Failed"}


Multi-Backend Authentication
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``MultiAuth`` backend allows you to support multiple authentication methods on a single route. Dyne will attempt to authenticate the request using each backend in the order they are provided.

.. code-block:: python

    from dyne.ext.auth.backends import MultiAuth

    # Support Token and Basic and Digest authentication
    multi_auth = MultiAuth(digest_auth, token_auth, basic_auth)

    @app.route("/{greeting}")
    @authenticate(multi_auth)
    async def multi_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

**Request Example:**

You can now access this route using either a Bearer token, a Basic username/password **OR** a Digest username/password.

.. code-block:: bash

    # Option 1: Basic Auth
    http -a john:password get http://127.0.0.1:5042/Hi

    # Option 2: Token Auth
    http get http://127.0.0.1:5042/Hi "Authorization: Bearer secret_key_123"

    # Option 3: Digest Auth
    http --auth-type=digest -a john:password get http://127.0.0.1:5042/Hi


Role-Based Authorization (RBAC)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Authorization happens after authentication. You can restrict routes to specific roles by implementing the `get_user_roles` callback on any backend.

How it Works

```

1. **Authentication:** The backend verifies the credentials and returns a ``user`` object.
2. **Role Retrieval:** Dyne calls your ``get_user_roles(user)`` function.
3. **Validation:** Dyne checks if the returned roles match the ``role`` requirement in the decorator.

Sample code using the ``basic_auth`` backends:

.. code-block:: python

    from dyne.ext.auth.backends import BasicAuth
    from dyne.ext.auth import authenticate

    basic_auth = BasicAuth()

    # Define user roles (usually stored in a DB)
    roles = {
        "john": "user", 
        "admin_user": ["user", "admin"]
    }

    @basic_auth.get_user_roles
    async def get_user_roles(user):
        # 'user' is the object returned by verify_password
        return roles.get(user)

    # Both `john`` and ``admin_user`` can access this ruote
    @app.route("/dashboard")
    @authenticate(basic_auth, role="user")
    async def dashboard(req, resp):
        resp.text = f"Welcome to the user dashboard, {req.state.user}!"

    # Only ``admin_user`` can access this ruote
    @app.route("/system-settings")
    @authenticate(basic_auth, role="admin")
    async def admin_settings(req, resp):
        resp.text = "Sensitive administrative settings."

Accessing Protected Routes
~~~~~~~~~~~~~~~~~~~~~~~~~~

When using RBAC, the client sends credentials normally. The server handles the permission check internally.

.. code-block:: bash

    # Accessing user-level route
    http -a john:password GET http://localhost:5042/dashboard

    # Accessing admin-level route (will return 403 if roles don't match)
    http -a admin_user:password123 GET http://localhost:5042/system-settings


OpenAPI Documentation
---------------------

Dyne utilizes a plugin-based architecture for API documentation, decoupling the documentation engine from the core ``:class:App`` to ensure the framework remains lightweight. 
By integrating the OpenAPI plugin from ``dyne.ext.openapi``, the system automatically generates a compliant OpenAPI 3.0.x specification by inspecting the metadata left 
behind by extension decorators—such as those from ``dyne.ext.io`` or ``dyne.ext.auth``. Consequently, you are never just validating requests, serializing responses, 
or enforcing authentication; you are simultaneously building your API's documentation in real-time.

It is important to understand that decorators like ``@input``, ``@output`` and ``@authenticate`` are designed to work independently of the documentation system:

1.  **At Runtime:** These decorators manage the essential logic of the request-response cycle. They perform the critical tasks of **validating incoming request data** and **serializing outgoing responses** using your preferred strategy (Pydantic or Marshmallow). Furthermore, they manage the security layer of your application by providing robust **Authentication** (supporting Basic, Token, and Digest schemes) and fine-grained **Authorization** for your endpoints.
2.  **For Documentation:** When combined with the ``OpenAPI`` extension, these same decorators serve as metadata providers. The extension introspects the schemas and security requirements defined by these decorators to automatically populate the paths, components, and security schemes in your ``schema.yml``.

**The Power of Synergy:** By using these decorators, you eliminate the need to maintain a separate documentation file. Your code becomes the single source of truth for both application logic and the API contract.


Configuring the API Metadata
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To provide a title and description for your API, assign a docstring or a configuration object to your API instance. This information appears at the very top of your generated documentation.

.. code-block:: python

    import dyne
    from dyne.ext.openapi import OpenAPI


    description = """ 
    User Management API
    -------------------
    This API allows for comprehensive management of users and books.

    **Base URL:** `https://api.example.com/v1`
    **Support:** `support@example.com`
    """

    app = dyne.App()
    api = OpenAPI(app, description=description)


  Other variables include:
  - title e.g "Book Store",
  - version e.g "1.0",
  - terms_of_service
  - contact
  - license
  - openapi e.g "3.0.1",
  - theme e.g ``elements``, ``rapidoc``, ``redoc``, ``swaggerui``

The Documentation Decorators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The documentation engine gathers data from five primary sources:

* **authenticate (auth extension)**: Documents security schemes (Basic, Bearer, Digest, etc.) and required roles.
* **input (io extensions)**: Documents request bodies(josn, form and yaml), query parameters, cookies, headers and file uploads.
* **output (io extensions)**: Documents the structure of successful (2xx) responses.
* **expect (io extensions)**: Documents success and error codes (2xx, 3xx, 4xx, 5xx) and specific response messages.
* **@webhook**: Documents endpoints as webhooks.

Full Example: Creating a Book with File Upload
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

This example demonstrates how the Marshmallow strategy captures a complex schema—including a file upload—and represents it in the OpenAPI spec as `multipart/form-data`.

.. code-block:: python

    import dyne
    from dyne.ext.openapi import OpenAPI
    from marshmallow import Schema, fields
    from dyne.ext.auth import authenticate
    from dyne.ext.auth.backends import BasicAuth
    from dyne.ext.io.marshmallow import input, output, expect
    from dyne.ext.io.marshmallow.fields import FileField

    # Define your schemas
    class BookSchema(Schema):
        id = fields.Integer(dump_only=True)
        price = fields.Float()
        title = fields.Str()
        cover_url = fields.Str()

    class BookCreateSchema(Schema):
        price = fields.Float(required=True)
        title = fields.Str(required=True)
        # FileField is automatically documented as a 'binary' format string
        image = FileField(allowed_extensions=["png", "jpg"], max_size=5 * 1024 * 1024)

    description = """ 
    User Management API
    -------------------
    This API allows for comprehensive management of users and books.

    **Base URL:** `https://api.example.com/v1`
    **Support:** `support@example.com`
    """

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


        book = Book(**data, cover_url=image.filename)
        session.add(book)
        session.commit()

        resp.obj = book


Viewing the Documentation
~~~~~~~~~~~~~~~~~~~~~~~~~

Once you have initialized the `OpenAPI` plugin and your routes are decorated, the documentation is automatically served by your application. 
By default, there are two primary endpoints available.

* **Interactive UI**: ``/docs`` (Swagger UI)
* **Raw Specification**: ``/schema.yml``

This documentation is always in sync with your code. If you add a field to your Marshmallow / Pydantic model or change a required role in your Auth backend, the documentation updates automatically on the next refresh.

> **Note:** Without the ``OpenAPI`` extension initialized, these decorators still protect your routes via validation, but no ``/docs`` or ``/schema.yml`` will be generated.


Single-Page Web Apps
--------------------

If you have a single-page webapp, you can tell dyne to serve up your ``static/index.html`` at a route, like so::

    app.add_route("/", static=True)

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

You can easily read a Request's session data, that can be trusted to have originated from the App::

    >>> req.session
    {'username': 'john'}

**Note**: if you are using this in production, you should pass the ``secret_key`` argument to ``App(...)``::

    app = dyne.App(secret_key=os.environ['SECRET_KEY'])

Using ``before_request``
------------------------

If you'd like a view to be executed before every request, simply do the following::

    @app.route(before_request=True)
    def prepare_response(req, resp):
        resp.headers["X-Pizza"] = "42"

Now all requests to your HTTP Service will include an ``X-Pizza`` header.

For ``websockets``::

    @app.route(before_request=True, websocket=True)
    def prepare_response(ws):
        await ws.accept()


WebSocket Support
-----------------

dyne supports WebSockets::

    @app.route('/ws', websocket=True)
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


Application and Request State
_____________________________

Dyne provides a way to store arbitrary extra information in the application instance 
and the request instance using the **State** object.

There are two primary types of state available:

1. **Application State**: Persistent data that lives for the entire lifecycle of the application.
2. **Request State**: Ephemeral data that lives only for the duration of a single HTTP request.

Global Application State
------------------------

To store variables that should be accessible globally (such as database connection pools, 
configuration settings, or shared caches), use the ``app.state`` attribute.

this state is designed to be:

- Application-scoped (not request-scoped)
- Mutable
- Explicit
- Easy to test

Initialization  State (Startup)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The best place to initialize application state is within a ``startup`` event handler:

.. code-block:: python

    @app.on_event("startup")
    async def startup():
        app.state.db = await create_database_pool()
        app.state.admin_email = "admin@example.com"

This ensures resources are created once and reused across requests.

Accessing State in Endpoints
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Inside your route handlers, you can access the application state through the 
``req.app.state`` attribute:

.. code-block:: python

    @app.route("/config")
    async def get_config(req, resp):
        email = req.app.state.admin_email
        resp.media = {"contact": email}

Cleaning Up State (Shutdown)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Long-lived resources should be properly closed during application shutdown.

.. code-block:: python

    @app.on_event("shutdown")
    async def shutdown():
        await app.state.db.close()

State vs. Request State
-----------------------

It is important to distinguish between ``req.app.state`` and ``req.state``.

+-------------------+---------------------------+--------------------------------+
| Feature           | Request State (req.state) | App State (req.app.state)      |
+===================+===========================+================================+
| **Scope**         | Single HTTP Request       | Entire Application             |
+-------------------+---------------------------+--------------------------------+
| **Lifecycle**     | Created/Destroyed per req | Persists until server stops    |
+-------------------+---------------------------+--------------------------------+
| **Typical Use**   | User ID, Request Timer    | DB Pools, Clients, Config      |
+-------------------+---------------------------+--------------------------------+
| **Thread Safety** | Isolated to request       | Shared across all requests     |
+-------------------+---------------------------+--------------------------------+


.. note::
   If you try to access a state attribute that has not been set, it will raise 
   an ``AttributeError``. Use ``getattr(req.app.state, "key", default)`` if 
   you are unsure if a value exists.



Using Requests Test Client
--------------------------

dyne comes with a first-class, well supported test client for your ASGI web services: **Requests**.

Here's an example of a test (written with pytest)::

    import dyne

    @pytest.fixture
    def app():
        return dyne.App()

    def test_response(app):
        hello = "hello, world!"

        @app.route('/some-url')
        def some_view(req, resp):
            resp.text = hello

        r = app.client.get(url=app.url_for(some_view))
        assert r.text == hello

HSTS (Redirect to HTTPS)
------------------------

Want HSTS (to redirect all traffic to HTTPS)?

::

    app = dyne.App(enable_hsts=True)


Boom.

CORS
----

Want `CORS <https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS/>`_ ?

::

    app = dyne.App(cors=True)


The default parameters used by **dyne** are restrictive by default, so you'll need to explicitly enable particular origins, methods, or headers, in order for browsers to be permitted to use them in a Cross-Domain context.

In order to set custom parameters, you need to set the ``cors_params`` argument of ``app``, a dictionary containing the following entries:

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

    app = dyne.App(allowed_hosts=['example.com', 'tenant.example.com'])

* ``allowed_hosts`` - A list of allowed hostnames. 

Note:

* By default, all hostnames are allowed.
* Wildcard domains such as ``*.example.com`` are supported.
* To allow any hostname use ``allowed_hosts=["*"]``.
