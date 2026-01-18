Feature Tour
============

Introduction
------------


Dyne brings simplicity and elegance to modern application and API development, with a carefully curated set of built-in capabilities:

* **Authentication**: First-class support for ``BasicAuth``, ``TokenAuth``, and ``DigestAuth``.
* **Request Validation**: The ``@input`` decorator provides clear, declarative validation for request payloads.
* **Response Serialization**: Automatically serialize responses using the ``@output`` decorator.
* **Request Contracts**: Use ``@expect`` to document and enforce required headers, cookies, and request metadata.
* **Asynchronous Events**: Define and document application webhooks with the ``@webhook`` decorator.
* **OpenAPI Documentation**: Fully self-generated OpenAPI specifications with seamless support for both `Pydantic` and `Marshmallow`.
* **Type-Casted Configuration**: First-class configuration with automatic casting and validation for environment variables and application settings.
* **GraphQL Support**: Native integration with ``Strawberry`` and ``Graphene`` for building GraphQL APIs alongside REST endpoints.
* **Database Integration**: Native SQLAlchemy support powered by ``Alchemical``, offering async-first, request-scoped session management with minimal configuration.
* **Advanced File Uploads**: Robust file handling via a configurable ``FileField``, enabling seamless binary data validation and storage integration for both ``Pydantic`` and ``Marshmallow`` schemas.


Here's how you can get started:


Installation
------------

Dyne uses **optional dependencies** (pip extras) to keep the core package lightweight.  
This allows you to install only the features you need for your specific project.

Core Installation
^^^^^^^^^^^^^^^^^

To install the minimal ASGI core:

.. code-block:: bash

  pip install dyne

Feature Bundles
^^^^^^^^^^^^^^^

Choose the bundle that fits your technology stack. Note that for most shells (like Zsh on macOS), you should wrap the package name in quotes to handle the brackets correctly.

1. OpenAPI & Serialization
""""""""""""""""""""""""""

Enable automated OpenAPI (Swagger) documentation, request validation and response serialization using your preferred schema library:

* **Pydantic Support:**
  
.. code-block:: bash
  
  pip install "dyne[openapi_pydantic]"

* **Marshmallow Support:**
  
.. code-block:: bash
  
  pip install "dyne[openapi_marshmallow]"

2. GraphQL Engines
""""""""""""""""""

Integrate a native GraphQL interface and the GraphiQL IDE:

* **Strawberry:**
  
.. code-block:: bash
  
  pip install "dyne[graphql_strawberry]"

* **Graphene:**
  
.. code-block:: bash
  
  pip install "dyne[graphql_graphene]"

3. Full Suite
"""""""""""""

For a comprehensive development environment including all serialization engines, GraphQL support, Flask adapters, and testing utilities:

.. code-block:: bash

  pip install "dyne[full]"


System Requirements
^^^^^^^^^^^^^^^^^^^

Dyne is built for the modern Python ecosystem and requires **Python 3.12** or newer. This ensures first-class support for advanced type hinting and the latest asynchronous performance improvements.

.. tip::
   **Zsh Users:** If you encounter a `no matches found` error, ensure your package name is quoted: ``pip install "dyne[extra]"``.


Background Tasks
----------------

Here, you can spawn off a background thread to run any function, out-of-request

.. code-block:: python

    @app.route("/")
    def hello(req, resp):

        @app.background.task
        def sleep(s=10):
            time.sleep(s)
            print("slept!")

        sleep()
        resp.content = "processing"


Error Handling
--------------

Dyne provides an ergonomic and flexible mechanism for handling HTTP errors and unexpected exceptions. You can define custom responses for specific HTTP status codes (such as ``404`` or ``403``) and also handle unhandled server errors (``500``).

Error handlers integrate directly into the request lifecycle and give you full control over the response sent to the client.

The `@error_handler` Decorator
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To register a custom error handler, use the ``@app.error_handler`` decorator.
The decorated function **must** be asynchronous and accept the following arguments:

* `req` – The incoming :class:`Request`
* `resp` – The outgoing :class:`Response`
* `exc` – The raised exception object

Example:

.. code-block:: python

  @app.error_handler(404)
  async def handle_404(req, resp, exc):
    resp.status_code = 404
    resp.media = {"error": The page you are looking for does not exist."}

  @app.error_handler(500)
  async def handle_500(req, resp, exc):
    resp.status_code = 500
    resp.text = f"Internal Server Error: {str(exc)}"

Manual Error Triggering
^^^^^^^^^^^^^^^^^^^^^^^

You can manually invoke an error handler from within any route using the ``abort()`` function.
This is particularly useful for validation errors, authentication failures, or permission checks.

Example:

.. code-block:: python

  from dyne.exceptions import abort

  @app.route("/secret")
  async def secret_page(req, resp):
    if not req.headers.get("Authorization"):
      # Triggers the 403 error handler
      abort(403, detail="You do not have access to this resource.")

    resp.text = "Welcome to the secret vault."

Using the Exception Object
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``exc`` argument passed into your handler provides context about the error:

* For ``HTTPException`` instances (raised via ``abort()``):

  * ``exc.status_code`` contains the HTTP status
  * ``exc.detail`` contains the custom error message (if provided)

* For unhandled runtime errors, ``exc`` will be the original Python exception
  (e.g., ``ValueError``, ``AttributeError``).

Example:

.. code-block:: python

  @app.error_handler(403)
  async def forbidden_handler(req, resp, exc):
    resp.status_code = 403
    resp.media = {
      "error": "Forbidden",
      "message": getattr(exc, "detail", "Access Denied"),
    }

Debug vs. Production Mode
^^^^^^^^^^^^^^^^^^^^^^^^^

Error-handling behavior depends on the application's boolean ``debug`` attribute.

**Debug Mode** (``debug=True``)
"""""""""""""""""""""""""""""

* Unhandled exceptions (``500`` errors) are re-raised.
* The Interactive Traceback middleware displays detailed error information in the browser.
* Ideal for development and debugging.

**Production Mode** (`debug=False`)
"""""""""""""""""""""""""""""""""""

* Unhandled exceptions are intercepted by your custom ``500`` handler (or a default fallback).
* Internal stack traces are hidden from users for security reasons.

Example:

.. code-block:: python

  app = App(debug=False)  # Production mode

Default Error Handlers
^^^^^^^^^^^^^^^^^^^^^^

If no custom error handlers are registered, Dyne provides safe defaults:

* **404 Not Found**
  Returns a plain-text `"Not Found"` response.

* **500 Internal Server Error**
  When ``debug=False``, returns a plain-text `"500 Internal Server Error"` response.

These defaults ensure predictable behavior even without explicit configuration.


File Uploads
------------

Dyne simplifies file handling by offering two primary approaches: **Schema-based validation** (via Marshmallow or Pydantic) for robust type and constraint checking, and **Native handling** for direct, manual processing.

1. Schema-Based Uploads
~~~~~~~~~~~~~~~~~~~~~~~

Using the ``@input`` decorator with a schema is the recommended way to handle uploads. This allows you to validate file metadata, size, and extensions before your code ever runs.

A. Marshmallow Upload
^^^^^^^^^^^^^^^^^^^^^

Marshmallow integration uses the ``FileField`` to define constraints like allowed extensions and maximum file size.

.. code-block:: python

    from marshmallow import Schema, fields
    from dyne.ext.io.marshmallow.fields import FileField
    from dyne.ext.io.marshmallow import input

    class UploadSchema(Schema):
        description = fields.Str()
        image = FileField(
            allowed_extensions=["png", "jpg", "jpeg"], 
            max_size=5 * 1024 * 1024  # 5MB
        )

    @app.route("/upload", methods=["POST"])
    @input(UploadSchema, location="form")
    async def upload(req, resp, *, data):
        image = data.pop("image") # 'image' is a validated File object.
        await image.asave(image.filename) 
        
        resp.media = {"success": True}

B. Pydantic Upload
^^^^^^^^^^^^^^^^^^

Pydantic integration allows you to create reusable file types by subclassing ``FileField``. 

.. important::
    To support custom file objects in Pydantic V2, your schema must include ``arbitrary_types_allowed=True`` within the ``model_config``.

.. code-block:: python

    from pydantic import BaseModel, ConfigDict
    from dyne.ext.io.pydantic.fields import FileField
    from dyne.ext.io.pydantic import input

    class Image(FileField):
        max_size = 5 * 1024 * 1024
        allowed_extensions = {"jpg", "jpeg", "png"}

    class UploadSchema(BaseModel):
        description: str
        image: Image

        model_config = ConfigDict(
            from_attributes=True,
            arbitrary_types_allowed=True
        )

    @app.route("/upload", methods=["POST"])
    @input(UploadSchema, location="form")
    async def upload(req, resp, *, data):
        image = data.pop("image") # 'image' is a validated File object.
        await image.asave(image.filename)

        resp.media = {"success": True}


Creating Custom Validators
^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``FileField`` system is designed to be extensible. By default, both Pydantic and Marshmallow versions come pre-configured with two core validators:

* ``validate_size``: Enforces the `max_size` constraint.
* ``validate_extension``: Enforces the `allowed_extensions` constraint.

Every validator in the registry—whether default or custom—receives a `File` object (imported from `from dyne.ext.io import File`) as its primary argument.

Pydantic: Validation
""""""""""""""""""""

In Pydantic, you extend the validation logic by creating a subclass and updating the `file_validators` class variable. Custom validator methods must be decorated with `@classmethod` and should raise a standard `ValueError` upon failure.

.. code-block:: python

    from dyne.ext.io.pydantic.fields import FileField
    from dyne.ext.io import File
    from pydantic import BaseModel

    class ImageField(FileField):
        max_size = 2 * 1024 * 1024
        allowed_extensions = {"jpg", "jpeg", "png"}
        
        # Append the new validator method name to the registry
        file_validators = FileField.file_validators + ["validate_is_image"]

        @classmethod
        def validate_is_image(cls, file: File):
            # Custom logic to check MIME types
            if not file.content_type.startswith("image/"):
                raise ValueError("File is not a valid image")

    # Usage in a Model
    class ProfileUpdate(BaseModel):
        username: str
        avatar: ImageField


Marshmallow: Validation
"""""""""""""""""""""""

Marshmallow fields offer two ways to register custom validators. Unlike Pydantic, these methods are instance methods and must raise `marshmallow.ValidationError`.

1. Using the Constructor (Instance Level)
''''''''''''''''''''''''''''''''''''''''''

This approach is ideal for adding validators dynamically during initialization. You modify the ``self.active_file_validators`` list inside the ``__init__`` method.

.. code-block:: python

    from dyne.ext.io import File
    from dyne.ext.io.marshmallow.fields import FileField
    from marshmallow import Schema, ValidationError

    class SecureFileField(FileField):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # Add a custom validator to this specific instance
            self.active_file_validators.append("validate_virus_scan")

        def validate_virus_scan(self, file: File):
            if "virus" in file.filename:
                raise ValidationError("Malicious file detected.")

    # Usage in a Schema
    class SubmissionSchema(Schema):
        tax_report = SecureFileField(
            max_size=2 * 1024 * 1024, 
            allowed_extensions=["pdf"],
            required=True
        )

2. Extending the Class Variable (Global Level)
''''''''''''''''''''''''''''''''''''''''''''''

For a simpler, more declarative approach, you can extend the `file_validators` class variable directly. This ensures that every instance of that subclass uses the custom validator by default.

.. code-block:: python

    class SecureFileField(FileField):
        file_validators = FileField.file_validators + ["validate_virus_scan"]

        def validate_virus_scan(self, file: File):
            if "virus" in file.filename:
                raise ValidationError("Malicious file detected")

.. note::
  **File Persistence Options**

  Files uploaded via `FileFields` provide dual-mode persistence to fit your execution context. You can persist these files asynchronously using the `asave()` method—ideal for maintaining high-throughput in `async` views—or use the standard `save()` method for synchronous operations.

2. Native File Uploads
~~~~~~~~~~~~~~~~~~~~~~

If you prefer not to use a schema, you can access uploaded files directly from the request object. This is useful for simple endpoints or when handling dynamic file inputs.

.. code-block:: python

    @app.route("/native-upload", methods=["POST"])
    async def upload_file(req, resp):

        @app.background.task
        def process_file(file_data):
            with open(f"./{file_data['filename']}", 'wb') as f:
                f.write(file_data['content'])

        # Extracts files from the multipart request
        data = await req.media(format='files')
        file_obj = data['image']

        process_file(file_obj)
        resp.media = {'status': 'processing'}

Client-Side Request
~~~~~~~~~~~~~~~~~~~

You can test your file upload endpoints using ``httpx`` or any standard HTTP client.

.. code-block:: python

    files = {'image': ('photo.jpg', open('photo.jpg', 'rb'), 'image/jpeg')}
    data = {'description': 'A beautiful sunset'}

    r = app.client.post("http://;/native-upload", data=data, files=files)
    print(r.json())


GraphQL
-------

Dyne provides built-in support for integrating ``GraphQL`` using both ``Strawberry`` and ``Graphene``.

To ensure consistent behavior, proper plugin isolation, and reliable runtime validation, Dyne requires that GraphQL schemas be created using Dyne-provided Schema classes, 
which act as thin wrappers around the underlying GraphQL backends.

With either backend, you can define GraphQL schemas containing queries, mutations, or both, and expose them via a ``GraphQLView``.

The view is added to a Dyne App route (for example, ``/graphql``). The endpoint can then be accessed through a GraphQL client, your browser, or tools such as Postman.
When accessed from a browser, the endpoint will render a GraphiQL interface, allowing you to easily explore and interact with your GraphQL schema.


Installation
^^^^^^^^^^^^

Dyne’s GraphQL support is provided via optional dependencies.
Install Dyne along with the backend you intend to use.

* Strawberry:
.. code-block:: bash

    pip install dyne[strawberry]


* Graphene:
.. code-block:: bash

    pip install dyne[graphene]

Only install the backend(s) you plan to use. Dyne does not auto-detect GraphQL backends.


Choosing a GraphQL Backend
^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^

* Do not pass raw `strawberry.Schema`` or `graphene.Schema` instances directly to `GraphQLView`.
* Always use the Schema class provided by Dyne for the backend you choose.
* Mixing GraphQL backends in a single application is not supported and will raise a runtime error.
* GraphQL support is optional and requires installing the appropriate extra.


GraphQL Queries and Mutations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Once your App is set up with either ``Strawberry`` or ``Graphene``, you can interact with it by making queries and mutations via the `/graphql` route.

Here are some example GraphQL queries and mutations you can use:

**Example Query 1**: Fetch a default hello message

.. code-block:: graphql

    query {
      hello
    }

**Expected Response**:

.. code-block:: json

    {
      "data": {
        "hello": "Hello stranger"
      }
    }


**Example Query 2**: Fetch a personalized hello message

.. code-block:: graphql

    query {
      hello(name: "Alice")
    }

**Expected Response**:

.. code-block:: json

    {
      "data": {
        "hello": "Hello Alice"
      }
    }


**Example Mutation**: Create a message

.. code-block:: graphql

    mutation {
      createMessage(name: "Alice", message: "GraphQL is awesome!") {
        ok
        message
      }
    }

**Expected Response**:

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


Configuration
--------------

Dyne features a hybrid configuration system that is "Zero-Config" by default but highly customizable when needed. 

Automatic Discovery
^^^^^^^^^^^^^^^^^^^

Dyne automatically looks for a file named ``.env`` in your current working directory (CWD) upon initialization. If found, these variables are loaded as defaults.

.. code-block:: python

    from dyne import App

    # If a .env exists in your folder, it is loaded automatically!
    app = App()
    print(app.config.DATABASE_URL)

Manual Initialization
^^^^^^^^^^^^^^^^^^^^^

You can override the discovery behavior or add prefixes to your environment lookups.

.. code-block:: python

    app = App(
        env_file=".env.production", # Use a specific file instead of discovery
        env_prefix="DYNE_",         # Only look for vars starting with DYNE_
        encoding="utf-8"            # Specify file encoding
    )

From Python Objects
^^^^^^^^^^^^^^^^^^^

You can seed your configuration using a class or module. Only **UPPERCASE** attributes are imported.

.. code-block:: python

    class DevelopmentConfig:
        PORT = 5042
        DEBUG = True

    app.config.from_object(DevelopmentConfig)


Resolution Hierarchy
^^^^^^^^^^^^^^^^^^^^

When you access a configuration key, Dyne searches in this specific order to ensure production environments can always override local settings:

1. **OS Environment**: System variables (e.g., set via ``export`` or Docker).
2. **Internal Store**: Values from the automatically discovered ``.env`` or an explicit ``env_file``.
3. **Python Objects**: Values seeded via ``app.config.from_object()``.
4. **Defaults**: The fallback value provided in ``app.config.get(key, default=...)``.

Type Casting
^^^^^^^^^^^^

Because environment variables are always strings, Dyne provides a casting engine to prevent "stringly-typed" bugs.

.. code-block:: python

    # Automatically converts "true", "1", "yes" to True
    debug = app.config.get("DEBUG", cast=bool)

    # Converts string "8080" to integer 8080
    port = app.config.get("PORT", cast=int, default=8000)

Configuration in Routes
^^^^^^^^^^^^^^^^^^^^^^^

Access your settings anywhere in your application via the ``request.app`` reference.

.. code-block:: python

    @app.route("/status")
    async def status(req, resp):
        if req.app.config.DEBUG:
            resp.media = {"status": "debug-mode", "db": req.app.config.DATABASE_URL}
        else:
            resp.media = {"status": "production"}


Access Patterns
^^^^^^^^^^^^^^^

Dyne's configuration system provides three distinct ways to access configuration
values. Each is designed for a specific use case.

Using ``get()`` (Safe & Optional)
"""""""""""""""""""""""""""""""""

The :meth:`Config.get` method is the most flexible and extension-friendly way
to read configuration values.

* Returns a default value when the key is missing
* Supports automatic type casting
* Never raises for missing keys

Example::

    debug = app.config.get("DEBUG", cast=bool, default=False)
    pool_size = app.config.get("DB_POOL_SIZE", cast=int, default=5)

This is the **preferred access method for plugins and optional features**.


Using ``require()`` (Mandatory Configuration)
"""""""""""""""""""""""""""""""""""""""""""""

The :meth:`Config.require` method is used when a configuration value is
**mandatory for correct application behavior**.

* Raises immediately if the key is missing
* Supports type casting
* Fails fast during application startup

Example::

    database_url = app.config.require("DATABASE_URL")

If the value is missing, Dyne raises::

    RuntimeError: Missing required config: DATABASE_URL

This method is ideal for database connections, secret keys, and core services.


Using Attribute Access (Strict & Explicit)
""""""""""""""""""""""""""""""""""""""""""

Configuration values may also be accessed as attributes::

    app.config.DATABASE_URL

Attribute access is **strict**:

* Raises :class:`AttributeError` if the key is missing
* Does not support defaults or casting
* Best suited for application-level constants

This behavior helps catch typos and misconfiguration early::

    app.config.DATABSE_URL
    AttributeError: Config has no attribute 'DATABSE_URL'


Summary
^^^^^^^

+------------------+------------+------------+---------------+
| Access Method     | Defaults   | Casting    | Raises on Miss|
+==================+============+============+===============+
| ``get()``         | Yes        | Yes        | No            |
+------------------+------------+------------+---------------+
| ``require()``     | No         | Yes        | Yes           |
+------------------+------------+------------+---------------+
| Attribute Access  | No         | No         | Yes           |
+------------------+------------+------------+---------------+

Choose the access pattern that best matches the criticality of the configuration
value.



SQLAlchemy Integration (Alchemical)
-----------------------------------

Dyne provides first-class **SQLAlchemy** support through an integration with
`Alchemical <https://alchemical.readthedocs.io/>`_, a lightweight wrapper around
SQLAlchemy that simplifies engine, session, and transaction management.

This integration is designed to be:

- **Async-native**
- **Zero-config by default**
- **Framework-agnostic**
- **Production-ready**

Overview
^^^^^^^^

The Alchemical extension provides:

- Automatic engine and session management
- Async SQLAlchemy 2.0 support
- Lazy session creation per request
- Optional automatic transaction commit
- Clean request-scoped lifecycle handling

Installation
^^^^^^^^^^^^

Install Dyne with SQLAlchemy support:

.. code-block:: bash

    pip install "dyne[sqlalchemy]"

Configuration
^^^^^^^^^^^^^

Alchemical uses Dyne’s configuration system and requires **one database URL**.

Supported configuration keys:

+------------------------------+----------+---------------------------------------------+
| Key                          | Required | Description                                 |
+==============================+==========+=============================================+
| ALCHEMICAL_DATABASE_URL      | Yes      | Primary database connection URL             |
+------------------------------+----------+---------------------------------------------+
| ALCHEMICAL_BINDS             | No       | Additional database binds                   |
+------------------------------+----------+---------------------------------------------+
| ALCHEMICAL_ENGINE_OPTIONS    | No       | Extra SQLAlchemy engine options             |
+------------------------------+----------+---------------------------------------------+
| ALCHEMICAL_AUTOCOMMIT        | No       | Auto-commit at end of request (default: no) |
+------------------------------+----------+---------------------------------------------+

Example ``.env`` file:

.. code-block:: bash

    ALCHEMICAL_DATABASE_URL="sqlite:///app.db"
    ALCHEMICAL_AUTOCOMMIT=true

Initializing the Extension
^^^^^^^^^^^^^^^^^^^^^^^^^^

Create and register the database extension during app setup:

.. code-block:: python

    from dyne import App
    from dyne.ext.db.alchemical import Alchemical

    app = App()
    db = Alchemical(app)

The database instance is automatically attached to:

.. code-block:: python

    app.state.db

Defining Models
^^^^^^^^^^^^^^^

Models inherit from the Alchemical ``Model`` base class:

.. code-block:: python


    from sqlalchemy.orm import Mapped, mapped_column
    from dyne.ext.db.alchemical import Model
    from sqlalchemy import String

    class User(Model):
        id: Mapped[int] = mapped_column(primary_key=True)
        username: Mapped[str] = mapped_column(String(64), unique=True)

Creating Tables
^^^^^^^^^^^^^^^

Create database tables on application startup:

.. code-block:: python

    @app.on_event("startup")
    async def create_tables():
        await db.create_all()

Request-Scoped Sessions
^^^^^^^^^^^^^^^^^^^^^^^

Each HTTP request receives a **lazy, request-scoped session**.

The session is created **only when accessed**, and is automatically:

- Rolled back on error
- Committed (if ``ALCHEMICAL_AUTOCOMMIT=true``)
- Closed at the end of the request

Accessing the Session
^^^^^^^^^^^^^^^^^^^^^

Inside route handlers, access the session via the request:

.. code-block:: python

    @app.route("/users")
    async def list_users(req, resp):
        session = await req.db

        result = await session.execute(
            User.select()
        )
        users = result.scalars().all()

        resp.media = [
            {"id": u.id, "username": u.username}
            for u in users
        ]

Creating Records
^^^^^^^^^^^^^^^^

.. code-block:: python

    @app.route("/users", methods=["POST"])
    async def create_user(req, resp):
        data = await req.media()

        if "username" not in data:
            abort(400, "username required")

        user = User(username=data["username"])

        session = await req.db
        session.add(user)
        await session.commit() # Or not at all if auto commit is True

        resp.status_code = 201
        resp.media = {"message": "User created"}

Transaction Behavior
^^^^^^^^^^^^^^^^^^^^

By default:

- Transactions **must be committed manually**
- Rollbacks occur automatically on unhandled exceptions

Enable automatic commit by setting:

.. code-block:: bash

    ALCHEMICAL_AUTOCOMMIT=true

Multiple Databases (Binds)
^^^^^^^^^^^^^^^^^^^^^^^^^^

Alchemical supports multiple databases via **binds**:

.. code-block:: python

    ALCHEMICAL_BINDS = {
        "analytics": "postgresql+asyncpg://..."
    }

Models can specify a bind using:

.. code-block:: python

    class Event(Model):
        __bind_key__ = "analytics"

Async-First Design
^^^^^^^^^^^^^^^^^^

This integration uses:

- SQLAlchemy 2.x async engine
- ``async_sessionmaker``
- Proper ASGI lifecycle handling
- Zero thread-locals

It is safe for:

- High concurrency
- Background tasks
- Long-running requests

Error Handling
^^^^^^^^^^^^^^

If a route raises an exception:

- The session is rolled back
- The connection is released
- Dyne’s error handlers take over

No session leaks occur between requests.


CRUDMixin (Active Record Utilities)
-----------------------------------

``CRUDMixin`` is an optional Active Record–style helper for Alchemical models.
It provides small, explicit CRUD utilities while remaining fully compatible
with SQLAlchemy’s unit-of-work pattern.

This mixin is designed to improve developer ergonomics without hiding
SQLAlchemy behavior.

Overview
^^^^^^^^

``CRUDMixin`` adds convenience helpers for common operations:

* Creating records
* Fetching records
* Updating records
* Deleting records

All operations are asynchronous and require an active database session
managed by Alchemical.

Session Requirement
^^^^^^^^^^^^^^^^^^^

All ``CRUDMixin`` operations require an active request-scoped session.

Before calling any CRUD helper, a session **must** be initialized:

.. code-block:: python

  await req.db

If no active session is available, CRUD operations will raise
``RuntimeError``.

Instance Methods
^^^^^^^^^^^^^^^^

save()
"""""

Adds the current instance to the active session and flushes it.

.. code-block:: python

  user = User(name="Dyne")
  await user.save()

Returns the persisted instance.

patch(**kwargs)
""""""""""""""""

Updates one or more attributes on the model and persists the changes.

.. code-block:: python

  await user.patch(name="Updated Name", role="admin")

Only attributes that already exist on the model are updated.

destroy()
"""""""""

Deletes the current instance and flushes the session.

.. code-block:: python

  await user.destroy()

Class Methods
^^^^^^^^^^^^^

create(**kwargs)
""""""""""""""""

Creates, saves, and returns a new instance.

.. code-block:: python

  user = await User.create(name="New User")

all()
"""""

Fetches all records for the model.

.. code-block:: python

  users = await User.all()

Returns a sequence of model instances.

find(**kwargs)
""""""""""""""

Fetches a single record matching the given criteria.

.. code-block:: python

  user = await User.find(email="test@example.com")

Returns the first matching record or `None`.

Usage Example
^^^^^^^^^^^^^

Model definition:

.. code-block:: python

  class User(CRUDMixin, Model):
      id: Mapped[int] = mapped_column(primary_key=True)
      name: Mapped[str] = mapped_column()

Create a record:

.. code-block:: python

  @app.route("/users", methods=["POST"])
  async def create_user(req, resp):
      await req.db
      user = await User.create(name="Dyne User")
      resp.media = {"id": user.id}

Update a record:

.. code-block:: python

  @app.route("/user/{id}/promote", methods=["POST"])
  async def promote_user(req, resp, id):
      await req.db

      user = await User.find(id=int(id))
      if not user:
          resp.status_code = 404
          return

      await user.patch(role="admin")
      resp.media = {"status": "promoted"}

Design Notes
^^^^^^^^^^^^

`CRUDMixin` is intentionally minimal:

* No implicit commits
* No automatic session creation
* No hidden queries

For complex queries or bulk operations, use SQLAlchemy’s `select()`
constructs directly.

Error Handling
^^^^^^^^^^^^^^

If a CRUD method is called without an active session, a
`RuntimeError` is raised:

.. code-block:: text

  RuntimeError: No active database session. Did you await req.db?

This behavior is intentional and helps surface configuration issues early.

Summary
^^^^^^^

* Optional Active Record helpers
* Async-first and request-scoped
* Compatible with SQLAlchemy’s unit-of-work model
* No framework lock-in

`CRUDMixin` is best used for simple workflows where clarity and brevity
matter.


Transaction Decorator
---------------------

Dyne’s Alchemical integration provides a ``@db.transaction`` decorator to
simplify transactional database workflows while keeping full control over
commit and rollback behavior.

The decorator automatically manages the database transaction lifecycle,
removing the need to manually open sessions or explicitly call
``session.commit()`` inside your endpoints.

Overview
^^^^^^^^

When applied to an async endpoint or handler, ``@db.transaction``:

* Lazily initializes the database session
* Commits the transaction on successful completion
* Rolls back the transaction if an exception is raised
* Prevents nested commits when already inside a transaction

This results in cleaner, more readable endpoints with fewer failure points.

Basic Usage
^^^^^^^^^^^

Without ``@transaction``, database operations are more verbose and error-prone:

.. code-block:: python

   @app.route("/create", methods=["POST"])
   async def create(req, resp):
       """Create book"""

       data = req.media()

       session = await req.db
       book = await Book.create(**data)
       await session.commit()

       resp.media = {"id": book.id, "title": book.title, "price": book.price}


Using ``@db.transaction``, the same endpoint becomes:

.. code-block:: python

   @app.route("/create", methods=["POST"])
   @db.transaction
   async def create(req, resp):
       """Create book"""

       data = req.media()
       book = await Book.create(**data)

       resp.media = {"id": book.id, "title": book.title, "price": book.price}

Notice that:

* ``await req.db`` is no longer required
* No explicit ``commit()`` call is needed
* The transaction is automatically committed on success

Updating Records
^^^^^^^^^^^^^^^^

Without the transaction decorator:

.. code-block:: python

   @app.route("/update-price/{id}", methods=["PATCH"])
   async def update_book_price(req, resp, id):
       """Update book price."""

       data = req.media()
       session = await req.db

       book = await Book.get(id)
       if not book:
           abort(404)

       await book.modify(**data)
       await session.commit()

       resp.status_code = 201
       resp.media = {"id": book.id, "title": book.title, "price": book.price}

With ``@db.transaction``:

.. code-block:: python

   @app.route("/update-price/{id}", methods=["PATCH"])
   @db.transaction
   async def update_book_price(req, resp, id):
       """Update book price."""

       data = req.media()
       book = await Book.get(id)
       if not book:
           abort(404)

       await book.patch(**data)

       resp.status_code = 201
       resp.media = {"id": book.id, "title": book.title, "price": book.price}

Nested Transactions
^^^^^^^^^^^^^^^^^^^

The ``@transaction`` decorator is safe to use in nested contexts.

If a session is already inside an active transaction (for example, when
`@transaction` is applied at a higher level or when middleware has already
opened one), the decorator will not create a new transaction.

In this case, the decorated function executes within the existing transaction
scope, preventing double commits or premature rollbacks.

``@transaction`` vs Autocommit 
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Although both approaches aim to reduce boilerplate, they serve different needs.

Autocommit
""""""""""

Autocommit is enabled at the middleware level and applies to **every request**.

* Commits automatically at the end of each request
* Rolls back on unhandled exceptions
* Useful for simple CRUD-heavy applications
* Applies globally and implicitly

However, autocommit:

* Runs even for read-only endpoints
* Offers less control over transaction boundaries
* Makes it harder to reason about complex flows

``@db.transaction``
"""""""""""""""""""

The ``@transaction`` decorator is **explicit and scoped**.

* Applied only where needed
* Commits only when the decorated function succeeds
* Rolls back immediately on failure
* Ideal for write-heavy or critical operations

Recommended Usage
^^^^^^^^^^^^^^^^^

Use ``@db.transaction`` when:

* Performing writes
* You want explicit transactional boundaries
* You want minimal endpoint verbosity
* You need safe composition with domain logic

Use autocommit when:

* Most endpoints perform simple writes
* You prefer implicit behavior
* You do not need fine-grained transaction control

.. note::

   ``@db.transaction`` and ``ALCHEMICAL_AUTOCOMMIT`` should not be used together.

   When ``@db.transaction`` is applied, it becomes the authoritative transaction
   boundary and manages commits explicitly using SQLAlchemy’s transaction API.

Summary
^^^^^^^

The ``@db.transaction`` decorator provides a clean, explicit, and safe way to
manage database transactions in Dyne applications. It reduces boilerplate,
prevents common transactional bugs, and keeps business logic focused on intent
rather than infrastructure.


Request Validation
------------------

Dyne provides specialized extensions for validating incoming requests against **Pydantic** models or **Marshmallow** schemas. Instead of a generic decorator, you import the ``input`` decorator specifically for the library you are using.

Validation is supported for various sources:

* **media**: Request body (``json``, ``form``, ``yaml``). This is the default.
* **query**: URL query parameters.
* **header**: Request headers.
* **cookie**: Browser cookies.


Installation
^^^^^^^^^^^^

Dyne’s IO support is provided via optional dependencies.
Install Dyne along with the schema library you intend to use.

* Pydantic:
.. code-block:: bash

    pip install "dyne[openapi_pydantic]"


* Marshmallow:
.. code-block:: bash

    pip install "dyne[openapi_marshmallow]"


Data Injection
^^^^^^^^^^^^^^

Once validated, the data is injected into your handler as a keyword argument. 
* By default, the argument name is the value of the ``location`` (e.g., ``query``, ``header``).
* For ``media``, the default argument name is ``data``.
* You can override this using the ``key`` parameter.

1. Pydantic validation
^^^^^^^^^^^^^^^^^^^^^^

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

2. Marshmallow Validation
^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^

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


Response Serialization
----------------------

Dyne simplifies the process of converting Python objects, SQLAlchemy models, or database queries into JSON responses. This is managed by the `@output` decorator. Instead of manually assigning data to `resp.media`, you assign your data to `resp.obj`, and the extension handles the serialization based on the provided schema.

The ``@output`` decorator supports:

* **status_code**: The HTTP status code for the response (default is 200).
* **header**: A schema to validate and document response headers.
* **description**: A string used for OpenAPI documentation to describe the response.

Installation
^^^^^^^^^^^^

Dyne’s IO support is provided via optional dependencies.
Install Dyne along with the schema library you intend to use.

* Pydantic:
.. code-block:: bash

    pip install "dyne[openapi_pydantic]"


* Marshmallow:
.. code-block:: bash

    pip install "dyne[openapi_marshmallow]"

1. Pydantic Output
^^^^^^^^^^^^^^^^^^

To serialize using Pydantic, import the decorator from ``dyne.ext.io.pydantic``. 

**Note:** When working with SQLAlchemy or other ORMs, ensure your Pydantic model is configured with ``from_attributes=True`` (Pydantic V2) or ``orm_mode=True`` (Pydantic V1).

.. code-block:: python

    import dyne
    from pydantic import BaseModel, ConfigDict
    from dyne.ext.db.alchemical import Alchemical, Model
    from dyne.ext.io.pydantic import output

    class Config:
        ALCHEMICAL_DATABASE_URL = "sqlite:///app.db"

    app = dyne.App()
    app.config.from_object(Config)

    db = Alchemical(app)

    @app.on_event("startup")
    async def setup_db():
        await db.create_all()

    # Define an example SQLAlchemy model
    class Book(Model):
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
        session = await req.db
        book = await session.scalar(Book.select().filter_by(id=id))
        
        # Assign the object to resp.obj
        # The extension converts the ORM model to JSON automatically
        resp.obj = book

    @app.route("/all-books")
    @output(BookSchema)
    async def list_all(req, resp):
        session = await req.db
        query = await session.scalars(Book.select())

        # resp.obj can also be a list or a query object
        resp.obj = query.all()

2. Marshmallow Output
^^^^^^^^^^^^^^^^^^^^^

To serialize using Marshmallow, import the decorator from ``dyne.ext.io.marshmallow``.

.. code-block:: python

    from marshmallow import Schema, fields
    from dyne.ext.db.alchemical import Alchemical, Model
    from dyne.ext.io.marshmallow import output
    import dyne

    class Config:
        ALCHEMICAL_DATABASE_URL = "sqlite:///app.db"

    app = dyne.App()
    app.config.from_object(Config)

    db = Alchemical(app)

    @app.on_event("startup")
    async def setup_db():
        await db.create_all()

    # Define an example SQLAlchemy model
    class Book(Model):
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
        session = await req.db
        book = await session.scalar(Book.select().filter_by(id=id))
        
        # Assign the object to resp.obj
        # The extension converts the ORM model to JSON automatically
        resp.obj = book

    @app.route("/all-books")
    @output(books)
    async def list_all(req, resp):
        session = await req.db
        query = await session.scalars(Book.select())

        # resp.obj can also be a list or a query object
        resp.obj = query.all()


Expected Responses
------------------

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


3. Schema + Description Responses
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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
--------

The `@webhook` decorator is used to mark a standard endpoint as a webhook receiver. 
This attaches metadata to the route, allowing Dyne to identify it in generated documentation (like OpenAPI Callbacks) or for internal routing.

The decorator is flexible and supports two calling conventions:

* **Note:** Import the ``expect`` decorator specifically for the library you are using.

* Pydantic: ``dyne.ext.io.pydantic``.
* Marshmallow: ``dyne.ext.io.marshmallow``.

1. Implicit Naming
^^^^^^^^^^^^^^^^^^

When used without parentheses, the webhook uses the function name as its default identifier.

.. code-block:: python

    @app.route("/events", methods=["POST"])
    @webhook
    async def handle_event(req, resp):
        pass


2. Explicit Naming
^^^^^^^^^^^^^^^^^^

You can provide a specific name for the webhook using the `name` argument. This is useful when the external service requires a specific endpoint identifier that differs from your function name.

.. code-block:: python

    @app.route("/transaction", methods=["POST"])
    @webhook(name="transaction_callback")
    async def process_payment(req, resp):
        pass


* **Note:** A function decorated with ``@webhook`` automatically inherits the HTTP method defined in the ``@app.route`` decorator. For example, if your route is configured for ``POST``, the webhook documentation will reflect that it expects a ``POST`` request from the external caller.

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


Grouping Request & Response Decorators
--------------------------------------

In a production endpoint, you will typically use all three decorators together to create a fully validated and documented API using the OpenAPI extension.

.. code-block:: python

  import dyne
  from dyne.exceptions import abort
  from dyne.ext.io.pydantic import expect, input, output, webhook
  from dyne.ext.openapi import OpenAPI

  app = dyne.App()

  db = Alchemical(app)
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
      session = await req.db
      book = await session.scalar(Book.select().filter_by(id=id))
      if not book:
          abort(404)
  
      book.price = data.price
      await session.commit()

      # The updated 'book' object is serialized back to the client
      resp.obj = book


**Summary**:

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
.


Stateless Authentication
------------------------


Dyne provides a robust authentication system through its ``auth.stateless`` extension. By separating the **Backend** logic (how credentials are verified) from the **Decorator** (how the route is protected), Dyne allows for a highly flexible stateless security architecture.

All authentication backends are located in ``dyne.ext.auth.stateless.backends``, while the protection decorator is in ``dyne.ext.auth.stateless``. For brevity, both the backends and the decorator can be imported directly from ``dyne.ext.auth``

The User Object
^^^^^^^^^^^^^^^

In the ``verify_password``, ``verify_token``, or ``get_password`` callbacks, you can return any object (e.g., a database model, a dictionary, or a string) that represents your user.

Once authenticated, this object is automatically attached to the request and can be accessed within your handlers via:

.. code-block:: python

  username = req.state.user


1. Basic Authentication
^^^^^^^^^^^^^^^^^^^^^^^

``BasicAuth`` verifies a username and password sent via the standard HTTP Basic Auth header.

.. code-block:: python

    import dyne
    from dyne.ext.auth import authenticate, BasicAuth

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


**Sample request**:

.. code-block:: bash

    http -a john:password GET http://localhost:5042/greet


2. Token Authentication
^^^^^^^^^^^^^^^^^^^^^^^

``TokenAuth`` is used for Bearer token strategies (like JWTs or API Keys).

.. code-block:: python

    from dyne.ext.auth import authenticate, TokenAuth

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


**Sample request**:

.. code-block:: bash

    http GET http://localhost:5042/dashboard "Authorization: Bearer secret_key_123"


3. Digest Authentication
^^^^^^^^^^^^^^^^^^^^^^^^

``DigestAuth`` provides a more secure alternative to Basic Auth by using a challenge-response mechanism that never sends the password in plaintext.

.. code-block:: python

    from dyne.ext.auth import authenticate, DigestAuth

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
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For production environments, ``DigestAuth`` offers additional hooks to increase security and customize the challenge-response lifecycle.

**Using Precomputed Hashes**


Storing plaintext passwords in a database is a security risk. You can instead store precomputed **HA1** hashes. 

.. note::
    The ``realm`` used to compute the hash must match the ``realm`` defined in your ``DigestAuth`` backend (the default is "Authentication Required").

.. code-block:: python

    import hashlib
    from dyne.ext.auth import DigestAuth

    digest_auth = DigestAuth(realm="My App")

    @digest_auth.get_password
    async def get_ha1_pw(username):
        password = users.get(username) # In reality, fetch from DB
        realm = "My App"
        # Precompute HA1: md5(username:realm:password)
        return hashlib.md5(f"{username}:{realm}:{password}".encode("utf-8")).hexdigest()

Custom Nonce and Opaque Management
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
^^^^^^^^^^^^^^^^^^^^^

Every backend allows you to override the default error message and status_code by providing an ``error_handler``.

.. code-block:: python

    @basic_auth.error_handler
    async def custom_error(req, resp, status_code):
        resp.status_code = 401
        resp.media = {"error": "Custom Authentication Failed"}


4. Multi-Backend Authentication
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The ``MultiAuth`` backend allows you to support multiple authentication methods on a single route. Dyne will attempt to authenticate the request using each backend in the order they are provided.

.. code-block:: python

    from dyne.ext.auth import MultiAuth

    # Support Token and Basic and Digest authentication
    multi_auth = MultiAuth(digest_auth, token_auth, basic_auth)

    @app.route("/{greeting}")
    @authenticate(multi_auth)
    async def multi_greet(req, resp, *, greeting):
        resp.text = f"{greeting}, {req.state.user}!"

**Sample request**:

You can now access this route using either a Bearer token, a Basic username/password **OR** a Digest username/password.

.. code-block:: bash

    # Option 1: Basic Auth
    http -a john:password get http://127.0.0.1:5042/Hi

    # Option 2: Token Auth
    http get http://127.0.0.1:5042/Hi "Authorization: Bearer secret_key_123"

    # Option 3: Digest Auth
    http --auth-type=digest -a john:password get http://127.0.0.1:5042/Hi


Role-Based Authorization (RBAC)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Authorization happens after authentication. You can restrict routes to specific roles by implementing the `get_user_roles` callback on any backend.

How it Works:


1. **Authentication:** The backend verifies the credentials and returns a ``user`` object.
2. **Role Retrieval:** Dyne calls your ``get_user_roles(user)`` function.
3. **Validation:** Dyne checks if the returned roles match the ``role`` requirement in the decorator.

Sample code using the ``basic_auth`` backends:

.. code-block:: python

    from dyne.ext.auth import authenticate, BasicAuth

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
^^^^^^^^^^^^^^^^^^^^^^^^^^

When using RBAC, the client sends credentials normally. The server handles the permission check internally.

.. code-block:: bash

    # Accessing user-level route
    http -a john:password GET http://localhost:5042/dashboard

    # Accessing admin-level route (will return 403 if roles don't match)
    http -a admin_user:password123 GET http://localhost:5042/system-settings



Session Authentication
----------------------


The ``LoginManager`` provides a robust, session-based authentication system for Dyne. 
It supports "Remember Me" functionality, flexible user loading, and complex 
Role-Based Access Control (RBAC). This can accessed from `dyne.ext.auth.session`, but
for brevity it can be imported directly from `dyne.ext.auth`.

 It supports:

* User session loading
* Remember-me cookies
* Login and logout flows
* Role-based Authorization
* Authentication hooks
* Custom authentication failure handling
* Middleware-based user injection

Configuration
^^^^^^^^^^^^^

Initialize the manager with your application and optional configuration:

.. code-block:: python

    auth = LoginManager(
        app, 
        login_url="/login",
        remember_me_duration=2592000,  # Optional 30 days default
        user_id_attribute="id",  # Optional and defaults to `id` 
    )

The manager requires SECRET_KEY to be defined in app.config. This key is used to sign and verify remember-me cookies.
By default, the user ID is taken from the ``id`` attribute. This can be customized via ``user_id_attribute``.

User Loading
^^^^^^^^^^^^

You must tell the manager how to retrieve a user from your database using 
the ``@user_loader`` decorator.

.. code-block:: python

    @auth.user_loader
    async def load_user(user_id: str):
        return await User.find(id=int(user_id))

Must return a user object or `None`. The returned object **must** have an ``id`` attribute or the attribute set in ``user_id_attribute``. Both object attributes and dictionary keys are supported.

Logging In
^^^^^^^^^^

To log a user in

.. code-block:: python

    await auth.login(req, resp, user, redirect_url="/dashboard")

Enable remember-me support

.. code-block:: python

    await auth.login(req, resp, user, remember_me=True, redirect_url="/dashboard")

This will:

* Store the user ID in the session
* Optionally set a signed remember-me cookie
* The remember_me cookie expires after ``remember_me_duration`` seconds
* Invoke ``on_login`` hooks


Logging Out
^^^^^^^^^^^

To log out the current user
.. code-block:: python

    await auth.logout(req, resp)

This clears:

* Session user ID
* Remember-me cookie
* Cached request user


Accessing the Current User
^^^^^^^^^^^^^^^^^^^^^^^^^^

The current user is stored on the request state

.. code-block:: python

    req.state.user

The ``LoginMiddleware`` ensures the user is loaded before handlers execute and if no user is authenticated, this value is ``None``.

Session Management
^^^^^^^^^^^^^^^^^^

To authenticate a user (e.g., after checking their password), use ``login()``. 
To clear the session, use ``logout()``.

.. code-block:: python

    @app.route("/login", methods=["POST"])
    async def login_route(req, resp):
        user = await User.authenticate(req.media())
        if user:
            await auth.login(req, resp, user, remember_me=True, redirect_url="/dashboard")
        ...

    @app.route("/logout")
    async def logout_route(req, resp):
        await auth.logout(req, resp)
        return resp.redirect("/")

Access Control
^^^^^^^^^^^^^^

Protect routes using the ``@login_required`` decorator. If a user is not logged in, 
they will be redirected to the ``login_url`` or receive a 401 response.

.. code-block:: python

    @app.route("/profile")
    @auth.login_required
    async def profile(req, resp):
        return {"user": req.state.user.username}

Role-Based Authorization (RBAC)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To use roles, register a role loader and pass requirements to the decorator.

.. code-block:: python

    @auth.get_user_roles
    async def get_roles(user):
        return [r.name for r in user.roles]

    # Requires 'admin' OR 'editor'
    @app.route("/post/edit")
    @auth.login_required(role=["admin", "editor"])
    async def edit(req, resp):
        pass

    # Requires 'admin' AND 'super_user'
    @app.route("/system/reset")
    @auth.login_required(role=[["admin", "super_user"]])
    async def reset(req, resp):
        pass

Event Hooks
^^^^^^^^^^^

Trigger logic automatically during authentication events.

.. code-block:: python

    @auth.on_login
    async def update_last_login(req, resp, user):
        await user.update(last_login=datetime.now())

    @auth.on_logout
    async def log_logout(req, resp, user):
        logger.info(f"User {user.id} logged out")

Customizing Failure
^^^^^^^^^^^^^^^^^^^

By default, unauthenticated users are redirected to the ``login_url``. 
You can override this to return JSON or custom HTML.

.. code-block:: python
   from dyne.ext.auth import AuthFailureReason

    @auth.on_failure
    async def custom_auth_failure(req, resp, reason):

        if reason == AuthFailureReason.UNAUTHENTICATED:
            resp.status_code = HTTPStatus.UNAUTHORIZED
            resp.media = {"error": "Authentication required", "code": "AUTH_REQUIRED"}

        if reason == AuthFailureReason.UNAUTHORIZED:
            resp.status_code = HTTPStatus.FORBIDDEN
            resp.media = {
                "error": "Insufficient permissions",
                "required_roles": "admin",
            }

            resp.status_code = HTTPStatus.FORBIDDEN
            resp.text = "<h1>403 - Forbidden</h1><p>You do not have permission to view this page.</p>"

        # Or fallback to default implementation
        # await auth.default_failure(req, resp, reason)

Failure Reasons
^^^^^^^^^^^^^^^

- ``AuthFailureReason.UNAUTHENTICATED``
- ``AuthFailureReason.UNAUTHORIZED``

Remember-Me Cookies
^^^^^^^^^^^^^^^^^^^

When enabled, remember-me cookies:

- Are signed
- Have configurable expiration
- Automatically restore the session on next request


Middleware
^^^^^^^^^^

``LoginMiddleware`` loads the current user for every HTTP request
and stores it in ``req.state.user``.


OpenAPI Documentation
---------------------

Dyne utilizes a plugin-based architecture for API documentation, decoupling the documentation engine from the core ``:class:App`` to ensure the framework remains lightweight. 

By integrating the OpenAPI plugin from ``dyne.ext.openapi``, the system automatically generates a compliant OpenAPI 3.0.x specification by inspecting the metadata left behind by extension decorators—such as those from ``dyne.ext.io`` or ``dyne.ext.auth``. Consequently, you are never just validating requests, serializing responses, or enforcing authentication; you are simultaneously building your API's documentation in real-time.

It is important to understand that decorators like ``@input``, ``@output`` and ``@authenticate`` are designed to work independently of the documentation system:

1.  **At Runtime:** These decorators manage the essential logic of the request-response cycle. They perform the critical tasks of ``validating incoming request data`` and ``serializing outgoing responses`` using your preferred strategy (Pydantic or Marshmallow). Furthermore, they manage the security layer of your application by providing robust ``Authentication`` (supporting Basic, Token, and Digest authentication) and fine-grained ``Authorization`` for your endpoints.
2.  **For Documentation:** When combined with the ``OpenAPI`` extension, these same decorators serve as metadata providers. The extension introspects the schemas and security requirements defined by these decorators to automatically populate the paths, components, and security schemes in your ``schema.yml``.

**The Power of Synergy:** By using these decorators, you eliminate the need to maintain a separate documentation file. Your code becomes the single source of truth for both application logic and the API contract.


Configuring the API Metadata
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

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
  - theme e.g "elements", "rapidoc", "redoc", "swaggerui"

The Documentation Decorators
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The documentation engine gathers data from five primary sources:

* **authenticate (auth extension)**: Documents security schemes (Basic, Bearer, Digest, etc.) and required roles.
* **input (io extensions)**: Documents request bodies(josn, form and yaml), query parameters, cookies, headers and file uploads.
* **output (io extensions)**: Documents the structure of successful (2xx) responses.
* **expect (io extensions)**: Documents success and error codes (2xx, 3xx, 4xx, 5xx) and specific response messages.
* **@webhook**: Documents endpoints as webhooks.

Full Example: Creating a Book with File Upload
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This example demonstrates how the Marshmallow strategy captures a complex schema—including a file upload—and represents it in the OpenAPI spec as `multipart/form-data`.

.. code-block:: python

    import dyne
    from dyne.ext.openapi import OpenAPI
    from marshmallow import Schema, fields
    from dyne.ext.auth import authenticate, BasicAuth
    from dyne.ext.io.marshmallow import input, output, expect
    from dyne.ext.io.marshmallow.fields import FileField
    from dyne.ext.db.alchemical import Alchemical, CRUDMixin, Model

    class Book(CRUDMixin, Model):  # SQLAlchemy Model
        __tablename__ = "books"
        id = Column(Integer, primary_key=True)
        price = Column(Float)
        title = Column(String)
        cover = Column(String, nullable=True)

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

    class Config:
        ALCHEMICAL_DATABASE_URL = "sqlite:///app.db"

    app = dyne.App()
    app.config.from_object(Config)

    db = Alchemical(app)
    api = OpenAPI(app, description=description)

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

    @app.route("/book", methods=["POST"])
    @authenticate(basic_auth, role="admin")
    @input(BookCreateSchema, location="form")
    @output(BookSchema, status_code=201)
    @expect({401: "Unauthorized", 400: "Invalid file format"})
    @db.transaction
    async def create_book(req, resp, *, data):
        """
        Create a new Book
        ---
        This endpoint allows admins to upload a book cover and metadata.
        """

        image = data.pop("image")
        await image.asave(f"uploads/{image.filename}") # The image is already validated for extension and size.


        book = await Book.create(**data, cover=image.filename)

        resp.obj = book


Viewing the Documentation
^^^^^^^^^^^^^^^^^^^^^^^^^

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
-----------------------------

Dyne provides a way to store arbitrary extra information in the application instance 
and the request instance using the **State** object.

There are two primary types of state available:

1. **Application State**: Persistent data that lives for the entire lifecycle of the application.
2. **Request State**: Ephemeral data that lives only for the duration of a single HTTP request.

Global Application State
^^^^^^^^^^^^^^^^^^^^^^^^

To store variables that should be accessible globally (such as database connection pools, 
configuration settings, or shared caches), use the ``app.state`` attribute.

this state is designed to be:

- Application-scoped (not request-scoped)
- Mutable
- Explicit
- Easy to test

Initialization  State (Startup)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The best place to initialize application state is within a ``startup`` event handler:

.. code-block:: python

    @app.on_event("startup")
    async def startup():
        app.state.db = await create_database_pool()
        app.state.admin_email = "admin@example.com"

This ensures resources are created once and reused across requests.

Accessing State in Endpoints
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Inside your route handlers, you can access the application state through the 
``req.app.state`` attribute:

.. code-block:: python

    @app.route("/config")
    async def get_config(req, resp):
        email = req.app.state.admin_email
        resp.media = {"contact": email}

Cleaning Up State (Shutdown)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Long-lived resources should be properly closed during application shutdown.

.. code-block:: python

    @app.on_event("shutdown")
    async def shutdown():
        await app.state.db.close()

State vs. Request State
^^^^^^^^^^^^^^^^^^^^^^^

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
