from pathlib import Path

import graphene
import pytest

import dyne
from dyne.ext.graphql.graphene import Schema


@pytest.fixture
def data_dir(current_dir):
    yield current_dir / "data"


@pytest.fixture()
def current_dir():
    yield Path(__file__).parent


@pytest.fixture
def app():
    return dyne.App(debug=False, allowed_hosts=[";"])


@pytest.fixture
def session(app):
    return app.client


@pytest.fixture
def url():
    def url_for(s):
        return f"http://;{s}"

    return url_for


@pytest.fixture
def flask():
    from flask import Flask

    flask_app = Flask(__name__)

    @flask_app.route("/")
    def hello():
        return "Hello World!"

    return flask_app


@pytest.fixture
def schema():
    class Query(graphene.ObjectType):
        hello = graphene.String(name=graphene.String(default_value="stranger"))

        def resolve_hello(self, info, name):
            return f"Hello {name}"

    return Schema(query=Query)


@pytest.fixture
def template_path(tmpdir):
    # create a Jinja template file on the filesystem
    template_name = "test.html"
    template_file = tmpdir.mkdir("static").join(template_name)
    template_file.write("{{ var }}")
    return template_file
