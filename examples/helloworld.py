import dyne

app = dyne.App()


@app.route("/{greeting}")
async def greet_world(req, resp, *, greeting):
    resp.text = f"{greeting}, world!"


if __name__ == "__main__":
    app.run()
