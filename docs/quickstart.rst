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


File Upload
-----------

Dyne provides two ways to handle file uploads: using the `@api.input` decorator with either Marshmallow or Pydantic schemas, 
or via native file upload support.

1. Uploading Files with `@api.input` Decorator
----------------------------------------------

You can define file upload logic using Marshmallow or Pydantic schemas. 
Each approach offers different features for handling file validation and input processing.

a. Uploading with a `Marshmallow` Schema
----------------------------------------

When using a Marshmallow schema, you need to utilize the `FileField` class. 
This class provides built-in validation for file extensions and file size, 
ensuring that uploaded files meet specified constraints.

**Example:**

.. code-block:: python

    from marshmallow import Schema, fields
    from dyne.fields.marshmallow import FileField

    class UploadSchema(Schema):
        description = fields.Str()
        image = FileField(allowed_extensions=["png", "jpg"], max_size=5 * 1024 * 1024)

    @api.input(UploadSchema, location="form")
    async def upload(req, resp, *, data):
        image = data.pop("image")
        await image.save(image.filename)  # The image is already validated for extension and size

        resp.media = {"success": True}


b. Uploading with a `Pydantic` Schema
-------------------------------------

When using a Pydantic schema, you can use the `File` class. While this approach is similar to the Marshmallow version, 
it does not include built-in support for file extension and size validation. 
If validation is needed, it must be handled manually.

**Note:** Remember to set `from_attributes = True` in the schema's `Config` to enable proper handling of file uploads.

**Example:**

.. code-block:: python

    from pydantic import BaseModel, Field
    from dyne.fields.pydantic import File

    class UploadSchema(BaseModel):
        description: str
        image: File = Field(...)

        class Config:
            from_attributes = True

    @api.input(UploadSchema, location="form")
    async def upload(req, resp, *, data):
        image = data.pop("image")
        await image.save(image.filename)  # Perform validation before saving

        resp.media = {"success": True}


2. Native File Upload Support
-----------------------------

Dyne also offers native support for file uploads without requiring schemas. 
This approach allows for easy handling of files, including background tasks for processing the uploaded content.

**Example:**

.. code-block:: python

    @api.route("/")
    async def upload_file(req, resp):

        @api.background.task
        def process_data(data):
            with open('./{}'.format(data['file']['filename']), 'w') as f:
                f.write(data['file']['content'].decode('utf-8'))

        data = await req.media(format='files')
        process_data(data)
        resp.media = {'success': 'ok'}


You can send a file easily with `requests`.

**Example:**

.. code-block:: python

    import requests

    data = {'file': ('hello.txt', 'hello, world!', 'text/plain')}
    r = requests.post('http://127.0.0.1:8210/file', files=data)

    print(r.text)

This sends a file named `hello.txt` with the content `"hello, world!"` to the specified API endpoint.

