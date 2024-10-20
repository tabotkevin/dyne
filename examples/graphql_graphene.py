import graphene

import dyne
from dyne.ext.graphql import GraphQLView

api = dyne.API()


class CreateMessage(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        message = graphene.String(required=True)

    ok = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, message):
        return CreateMessage(ok=True, message=f"Message from {name}: {message}")


class Mutation(graphene.ObjectType):
    create_message = CreateMessage.Field()


class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="stranger"))

    def resolve_hello(self, info, name):
        return f"Hello {name}"


schema = graphene.Schema(query=Query, mutation=Mutation)
view = GraphQLView(api=api, schema=schema)

api.add_route("/graphql", view)


if __name__ == "__main__":
    api.run()
