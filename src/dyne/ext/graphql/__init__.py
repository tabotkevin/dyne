import json

from graphql.error.graphql_error import format_error

from .templates import GRAPHIQL


class GraphQLView:
    def __init__(self, *, api, schema):
        self.api = api
        self.schema = schema  # schema, could be either graphene or strawberry

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
            resp.content = self.api.templates.render_string(
                GRAPHIQL, endpoint=req.url.path
            )
            return

        query, variables, operation_name = await self._resolve_graphql_query(req)
        context = {"request": req, "response": resp}

        response_data = {}

        if hasattr(self.schema, "execute_async"):  # Graphene schema
            result = await self.schema.execute_async(
                query,
                variables=variables,
                operation_name=operation_name,
                context=context,
            )

        else:  # Assume it's Strawberry schema
            result = await self.schema.execute(
                query,
                variable_values=variables,
                operation_name=operation_name,
                context_value=context,
            )

        if result.data:
            response_data["data"] = result.data
        if result.errors:
            resp.status_code = 400
            response_data["errors"] = [format_error(error) for error in result.errors]

        resp.media = json.loads(json.dumps(response_data))
        return query, response_data

    async def on_request(self, req, resp):
        await self.graphql_response(req, resp)

    async def __call__(self, req, resp):
        await self.on_request(req, resp)
