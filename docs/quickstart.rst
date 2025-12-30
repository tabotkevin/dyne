Quick Start!
============

This section of the documentation exists to provide an introduction to the dyne interface,
as well as educate the user on basic functionality.


Declare a Web Service
---------------------

The first thing you need to do is declare a web service::

    import dyne

    api = dyne.API()

Hello World!
------------

Then, you can add a view / route to it.

Here, we'll make the root URL say "hello world!"::

    @api.route("/")
    def hello_world(req, resp):
        resp.text = "hello, world!"

Run the Server
--------------

Next, we can run our web service easily, with ``api.run()``::

    api.run()

This will spin up a production web server on port ``5042``, ready for incoming HTTP requests.

Note: you can pass ``port=5000`` if you want to customize the port. The ``PORT`` environment variable for established web service providers (e.g. Heroku) will automatically be honored and will set the listening address to ``0.0.0.0`` automatically (also configurable through the ``address`` keyword argument).


Accept Route Arguments
----------------------

If you want dynamic URLs, you can use Python's familiar *f-string syntax* to declare variables in your routes::

    @api.route("/hello/{who}")
    def hello_to(req, resp, *, who):
        resp.text = f"hello, {who}!"

A ``GET`` request to ``/hello/brettcannon`` will result in a response of ``hello, brettcannon!``.

Type convertors are also available::

    @api.route("/add/{a:int}/{b:int}")
    async def add(req, resp, *, a, b):
        resp.text = f"{a} + {b} = {a + b}"

Supported types: ``str``, ``int`` and ``float``.

Returning JSON / YAML
---------------------

If you want your API to send back JSON, simply set the ``resp.media`` property to a JSON-serializable Python object::


    @api.route("/hello/{who}/json")
    def hello_to(req, resp, *, who):
        resp.media = {"hello": who}

A ``GET`` request to ``/hello/guido/json`` will result in a response of ``{'hello': 'guido'}``.

If the client requests YAML instead (with a header of ``Accept: application/x-yaml``), YAML will be sent.

Rendering a Template
--------------------

dyne provides a built-in light `jinja2 <http://jinja.pocoo.org/docs/>`_ wrapper ``templates.Templates``

Usage::

  from dyne.templates import Templates

  templates = Templates()

  @api.route("/hello/{name}/html")
  def hello(req, resp, name):
      resp.html = templates.render("hello.html", name=name)


Also a ``render_async`` is available::

    templates = Templates(enable_async=True)
    resp.html = await templates.render_async("hello.html", who=who)

You can also use the existing ``api.template(filename, *args, **kwargs)`` to render templates::

    @api.route("/hello/{who}/html")
    def hello_html(req, resp, *, who):
        resp.html = api.template('hello.html', who=who)


Setting Response Status Code
----------------------------

If you want to set the response status code, simply set ``resp.status_code``::

    @api.route("/416")
    def teapot(req, resp):
        resp.status_code = api.status_codes.HTTP_416   # ...or 416


Setting Response Headers
------------------------

If you want to set a response header, like ``X-Pizza: 42``, simply modify the ``resp.headers`` dictionary::

    @api.route("/pizza")
    def pizza_pizza(req, resp):
        resp.headers['X-Pizza'] = '42'

That's it!


Receiving Data & Background Tasks
---------------------------------

If you're expecting to read any request data, on the server, you need to declare your view as async and await the content.

Here, we'll process our data in the background, while responding immediately to the client::

    import time

    @api.route("/incoming")
    async def receive_incoming(req, resp):

        @api.background.task
        def process_data(data):
            """Just sleeps for three seconds, as a demo."""
            time.sleep(3)


        # Parse the incoming data as form-encoded.
        # Note: 'json' and 'yaml' formats are also automatically supported.
        data = await req.media()

        # Process the data (in the background).
        process_data(data)

        # Immediately respond that upload was successful.
        resp.media = {'success': True}

A ``POST`` request to ``/incoming`` will result in an immediate response of ``{'success': true}``.


File Uploads
============

Dyne simplifies file handling by offering two primary approaches: **Schema-based validation** (via Marshmallow or Pydantic) for robust type and constraint checking, and **Native handling** for direct, manual processing.

1. Schema-Based Uploads
-----------------------

Using the ``@input`` decorator with a schema is the recommended way to handle uploads. This allows you to validate file metadata, size, and extensions before your code ever runs.

A. Using Marshmallow
~~~~~~~~~~~~~~~~~~~~

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

    @api.route("/upload", methods=["POST"])
    @input(UploadSchema, location="form")
    async def upload(req, resp, *, data):
        image = data.pop("image") # 'image' is a validated File object.
        await image.asave(image.filename) 
        
        resp.media = {"success": True}

B. Using Pydantic
~~~~~~~~~~~~~~~~~

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

    @api.route("/upload", methods=["POST"])
    @input(UploadSchema, location="form")
    async def upload(req, resp, *, data):
        image = data.pop("image") # 'image' is a validated File object.
        await image.asave(image.filename)

        resp.media = {"success": True}


Creating Custom Validators
~~~~~~~~~~~~~~~~~~~~~~~~~~

The ``FileField`` system is designed to be extensible. By default, both Pydantic and Marshmallow versions come pre-configured with two core validators:

* ``validate_size``: Enforces the `max_size` constraint.
* ``validate_extension``: Enforces the `allowed_extensions` constraint.

Every validator in the registry—whether default or custom—receives a `File` object (imported from `from dyne.ext.io import File`) as its primary argument.

Pydantic: Class-Based Extension
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

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


Marshmallow: Flexible Validation Registry
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Marshmallow fields offer two ways to register custom validators. Unlike Pydantic, these methods are instance methods and must raise `marshmallow.ValidationError`.

1. Using the Constructor (Instance Level)

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

For a simpler, more declarative approach, you can extend the `file_validators` class variable directly. This ensures that every instance of that subclass uses the custom validator by default.

.. code-block:: python

    class SecureFileField(FileField):
        file_validators = FileField.file_validators + ["validate_virus_scan"]

        def validate_virus_scan(self, file: File):
            if "virus" in file.filename:
                raise ValidationError("Malicious file detected")


2. Native File Uploads
----------------------

If you prefer not to use a schema, you can access uploaded files directly from the request object. This is useful for simple endpoints or when handling dynamic file inputs.

.. code-block:: python

    @api.route("/native-upload", methods=["POST"])
    async def upload_file(req, resp):

        @api.background.task
        def process_file(file_data):
            with open(f"./{file_data['filename']}", 'wb') as f:
                f.write(file_data['content'])

        # Extracts files from the multipart request
        data = await req.media(format='files')
        file_obj = data['image']

        process_file(file_obj)
        resp.media = {'status': 'processing'}

Client-Side Example
-------------------

You can test your file upload endpoints using ``httpx`` or any standard HTTP client.

.. code-block:: python

    files = {'image': ('photo.jpg', open('photo.jpg', 'rb'), 'image/jpeg')}
    data = {'description': 'A beautiful sunset'}

    r = api.client.post("http://;/native-upload", data=data, files=files)
    print(r.json())
