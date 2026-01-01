Building and Testing with Dyne
===================================

dyne comes with a first-class, well supported test client for your ASGI web services: **Requests**.

Here, we'll go over the basics of setting up a proper Python package and adding testing to it.

The Basics
----------

Your repository should look like this::

    app.py  test_app.py

``$ cat app.py``::

    import dyne

    app = dyne.App()

    @app.route("/")
    def hello_world(req, resp):
        resp.text = "hello, world!"

    if __name__ == "__main__":
        app.run()


Writing Tests
-------------

``$ cat test_app.py``::

    import pytest
    import app as service

    @pytest.fixture
    def app():
        return service.app


    def test_hello_world(app):
        r = app.client.get("/")
        assert r.text == "hello, world!"

``$ pytest``::

    ...
    ========================== 1 passed in 0.10 seconds ==========================


(Optional) Proper Python Package
--------------------------------

Optionally, you can not rely on relative imports, and instead install your app as a proper package. This requires:

1. Install `Rye` package manager from `https://rye-up.com`.
2. ``$ rye sync``
