from http import HTTPStatus

import graphene
import strawberry

from dyne.ext.graphql import GraphQLView


def test_strawberry(app):
    from dyne.ext.graphql.strawberry import Schema

    @strawberry.type
    class MessageResponse:
        ok: bool
        message: str

    @strawberry.type
    class Mutation:
        @strawberry.mutation
        def create_message(self, name: str, message: str) -> MessageResponse:
            return MessageResponse(ok=True, message=f"Message from {name}: {message}")

    @strawberry.type
    class Query:
        @strawberry.field
        def hello(self, name: str = "stranger") -> str:
            return f"Hello {name}"

    schema = Schema(query=Query, mutation=Mutation)
    view = GraphQLView(app=app, schema=schema)
    app.add_route("/graphql", view)

    # Test graphene query
    query = """
    query {
      hello(name: "Alice")
    }
    """
    response = app.client.post("http://;/graphql", json={"query": query})
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data": {"hello": "Hello Alice"}}

    # Test graphene mutation
    mutation = """
    mutation {
      createMessage(name: "Alice", message: "GraphQL is awesome!") {
        ok
        message
      }
    }
    """
    response = app.client.post("http://;/graphql", json={"query": mutation})
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "data": {
            "createMessage": {
                "ok": True,
                "message": "Message from Alice: GraphQL is awesome!",
            }
        }
    }

    # Test graphene error query
    invalid_query = """
    query {
      nonExistentField
    }
    """
    response = app.client.post("http://;/graphql", json={"query": invalid_query})
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "errors" in response.json()


def test_graphene(app):
    from dyne.ext.graphql.graphene import Schema

    class Query(graphene.ObjectType):
        hello = graphene.String(name=graphene.String(default_value="stranger"))

        def resolve_hello(self, info, name):
            return f"Hello {name}"

    class CreateMessage(graphene.Mutation):
        class Arguments:
            name = graphene.String()
            message = graphene.String()

        ok = graphene.Boolean()
        message = graphene.String()

        def mutate(self, info, name, message):
            return CreateMessage(ok=True, message=f"Message from {name}: {message}")

    class Mutation(graphene.ObjectType):
        create_message = CreateMessage.Field()

    schema = Schema(query=Query, mutation=Mutation)
    view = GraphQLView(app=app, schema=schema)
    app.add_route("/graphql", view)

    # Test graphene query
    query = """
    query {
      hello(name: "Alice")
    }
    """
    response = app.client.post("http://;/graphql", json={"query": query})
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"data": {"hello": "Hello Alice"}}

    # Test graphene mutation
    mutation = """
    mutation {
      createMessage(name: "Alice", message: "GraphQL is awesome!") {
        ok
        message
      }
    }
    """
    response = app.client.post("http://;/graphql", json={"query": mutation})
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "data": {
            "createMessage": {
                "ok": True,
                "message": "Message from Alice: GraphQL is awesome!",
            }
        }
    }

    # Test graphene error query
    invalid_query = """
    query {
      nonExistentField
    }
    """
    response = app.client.post("http://;/graphql", json={"query": invalid_query})
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "errors" in response.json()
