import json
from http import HTTPStatus

try:
    from graphql.error.graphql_error import format_error
except ImportError as exc:
    raise RuntimeError(
        "graphql is not installed.\n\n"
        "Install it with:\n"
        "  pip install dyne[graphql]\n"
    ) from exc

from .base import GraphQLSchema
from .templates import GRAPHIQL


class GraphQLView:
    def __init__(self, *, app, schema: GraphQLSchema):
        self.app = app

        if not hasattr(schema, "execute"):
            raise TypeError(
                "GraphQLView expects a Dyne GraphQLSchema instance.\n"
                "Import Schema from dyne.ext.graphql.<backend>"
            )

        self.schema = schema

    @staticmethod
    async def _resolve_graphql_query(req):
        # TODO: Get variables and operation_name from form data, params, request text?

        if "json" in req.mimetype:
            json_media = await req.media("json")
            return (
                json_media["query"],
                json_media.get("variables"),
                json_media.get("operationName"),
            )

        # Support query/q in params.
        if "query" in req.params:
            return req.params["query"], None, None
        if "q" in req.params:
            return req.params["q"], None, None

        # Support query/q in form data.
        if "query" in req.media("form"):
            return req.media("form")["query"], None, None
        if "q" in req.media("form"):
            return req.media("form")["q"], None, None

        # Otherwise, the request text is used (typical).
        # TODO: Make some assertions about content-type here.
        return req.text, None, None

    async def graphql_response(self, req, resp):
        show_graphiql = req.method == "get" and req.accepts("text/html")

        if show_graphiql:
            resp.content = self.app.templates.render_string(
                GRAPHIQL, endpoint=req.url.path
            )
            return

        query, variables, operation_name = await self._resolve_graphql_query(req)
        context = {"request": req, "response": resp}

        response_data = {}

        result = await self.schema.execute(
            query=query,
            variables=variables,
            operation_name=operation_name,
            context=context,
        )

        if result.data:
            response_data["data"] = result.data
        if result.errors:
            resp.status_code = HTTPStatus.BAD_REQUEST
            response_data["errors"] = [format_error(error) for error in result.errors]

        resp.media = json.loads(json.dumps(response_data))
        return query, response_data

    async def on_request(self, req, resp):
        await self.graphql_response(req, resp)

    async def __call__(self, req, resp):
        await self.on_request(req, resp)
