def test_custom_encoding(app, session):
    data = "hi alex!"

    @app.route("/", methods=["POST"])
    async def route(req, resp):
        req.encoding = "ascii"
        resp.text = await req.text

    r = session.post(app.url_for(route), content=data)
    assert r.text == data


def test_bytes_encoding(app, session):
    data = b"hi lenny!"

    @app.route("/", methods=["POST"])
    async def route(req, resp):
        resp.text = (await req.content).decode("utf-8")

    r = session.post(app.url_for(route), content=data)
    assert r.content == data
