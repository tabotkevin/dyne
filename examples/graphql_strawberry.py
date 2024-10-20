import strawberry

import dyne
from dyne.ext.graphql import GraphQLView

api = dyne.API()


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


schema = strawberry.Schema(query=Query, mutation=Mutation)
view = GraphQLView(api=api, schema=schema)

api.add_route("/graphql", view)


if __name__ == "__main__":
    api.run()
