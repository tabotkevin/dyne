from marshmallow import Schema, fields

import dune

api = dune.API()


@api.schema("Pet")
class PetSchema(Schema):
    name = fields.Str()


@api.route("/")
def route(req, resp):
    """A cute furry animal endpoint.
    ---
    get:
        description: Get a random pet
        responses:
            200:
                description: A pet to be returned
                content:
                    application/json:
                        schema:
                            $ref: '#/components/schemas/Pet'
    """
    resp.media = PetSchema().dump({"name": "little orange"})


if __name__ == "__main__":
    api.run()
