from abc import ABC, abstractmethod

try:
    from graphql import ExecutionResult
except ImportError as exc:
    raise RuntimeError(
        "graphql is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[graphql]\n"
    ) from exc


class GraphQLSchema(ABC):
    backend: str

    @abstractmethod
    async def execute(
        self,
        query: str,
        variables: dict | None,
        operation_name: str | None,
        context: dict,
    ) -> ExecutionResult: ...
