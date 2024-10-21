Building and Testing with Dyne
===================================

dyne comes with a first-class, well supported test client for your ASGI web services: **Requests**.

Here, we'll go over the basics of setting up a proper Python package and adding testing to it.

The Basics
----------

Your repository should look like this::

    api.py  test_api.py

``$ cat api.py``::

    import dyne

    api = dyne.API()

    @api.route("/")
    def hello_world(req, resp):
        resp.text = "hello, world!"

    if __name__ == "__main__":
        api.run()


Writing Tests
-------------

``$ cat test_api.py``::

    import pytest
    import api as service

    @pytest.fixture
    def api():
        return service.api


    def test_hello_world(api):
        r = api.client.get("/")
        assert r.text == "hello, world!"

``$ pytest``::

    ...
    ========================== 1 passed in 0.10 seconds ==========================


(Optional) Proper Python Package
--------------------------------

Optionally, you can not rely on relative imports, and instead install your api as a proper package. This requires:

1. Install `Rye` package manager from `https://rye-up.com`.
2. ``$ rye sync``
