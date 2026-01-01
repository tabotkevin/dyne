import strawberry

import dyne
from dyne.ext.graphql import GraphQLView
from dyne.ext.graphql.strawberry import Schema

app = dyne.App()


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


if __name__ == "__main__":
    app.run()
