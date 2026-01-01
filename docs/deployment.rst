Deploying Dyne
===================

You can deploy Dyne anywhere you can deploy a basic Python application.

Docker Deployment
-----------------

Assuming existing ``app.py`` containing ``dyne``.

``Dockerfile``::

    FROM python:3.12-slim
    ENV PORT '80'
    COPY . /app
    CMD python3 app.py
    EXPOSE 80

That's it!

Heroku Deployment
-----------------

The basics::

    $ mkdir my-app
    $ cd my-app
    $ git init
    $ heroku create
    ...

Install dyne::

    $ pipenv install dyne
    ...

Write out an ``app.py``::

    import dyne

    app = dyne.App()

    @app.route("/")
    async def hello(req, resp):
        resp.text = "hello, world!"

    if __name__ == "__main__":
        app.run()

Write out a ``Procfile``::

    web: python app.py

That's it! Next, we commit and push to Heroku::

    $ git add -A
    $ git commit -m 'initial commit'
    $ git push heroku master
