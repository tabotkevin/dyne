try:
    import graphene
    from graphene.types.schema import ExecutionResult
except ImportError as exc:
    raise RuntimeError(
        "Graphene is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[graphene]\n"
    ) from exc

from ..base import GraphQLSchema


class Schema(GraphQLSchema):
    backend = "graphene"

    def __init__(self, *, query=None, mutation=None, subscription=None, **kwargs):
        self._schema = graphene.Schema(
            query=query,
            mutation=mutation,
            subscription=subscription,
            **kwargs,
        )

    async def execute(
        self, query, variables, operation_name, context
    ) -> ExecutionResult:
        return await self._schema.execute_async(
            query,
            variables=variables,
            operation_name=operation_name,
            context=context,
        )
