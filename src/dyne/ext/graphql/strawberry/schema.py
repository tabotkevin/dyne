try:
    import strawberry
    from strawberry.types import ExecutionResult
except ImportError as exc:
    raise RuntimeError(
        "Strawberry is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[strawberry]\n"
    ) from exc

from ..base import GraphQLSchema


class Schema(GraphQLSchema):
    backend = "strawberry"

    def __init__(self, *, query=None, mutation=None, subscription=None, **kwargs):
        self._schema = strawberry.Schema(
            query=query,
            mutation=mutation,
            subscription=subscription,
            **kwargs,
        )

    async def execute(
        self, query, variables, operation_name, context
    ) -> ExecutionResult:
        return await self._schema.execute(
            query,
            variable_values=variables,
            operation_name=operation_name,
            context_value=context,
        )
