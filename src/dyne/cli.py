import os
import sys

import click
import uvicorn

__version__ = "2.0.4"


def parse_app_import(app_path: str | None) -> str:
    if not app_path:
        return "app:app"
    if ":" not in app_path:
        return f"{app_path}:app"
    return app_path


def resolve_reload(debug: bool, reload_flag: bool | None) -> bool:
    if reload_flag is not None:
        return reload_flag
    return debug


@click.group()
@click.version_option(version=__version__)
@click.option(
    "--app",
    "-a",
    envvar="DYNE_APP",
    help="The Dyne app to run, e.g. 'myapp:app'. Defaults to DYNE_APP env var.",
)
@click.option("--debug", is_flag=True, help="Enable debug mode.")
@click.option("--host", default="127.0.0.1", help="The interface to bind to.")
@click.option("--port", default=8000, type=int, help="The port to bind to.")
@click.option("--reload/--no-reload", default=None, help="Enable/disable reload.")
@click.pass_context
def cli(ctx, app, debug, host, port, reload):
    # Ensure current directory is in path for imports
    project_root = os.getcwd()
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    ctx.ensure_object(dict)

    ctx.obj["app"] = parse_app_import(app)
    ctx.obj["host"] = host
    ctx.obj["port"] = port
    ctx.obj["debug"] = debug
    ctx.obj["reload"] = resolve_reload(debug, reload)

    if debug:
        os.environ["DEBUG"] = "true"


@cli.command()
@click.pass_context
def run(ctx):
    config = ctx.obj
    app = config["app"]
    host = config["host"]
    port = config["port"]
    debug = config["debug"]
    reload = config["reload"]
    log_level = "debug" if debug else "info"

    click.echo("")
    click.secho(f"🚀 Launching Dyne {__version__}", fg="cyan", bold=True)
    click.echo(f"App: {app}")
    click.echo(f"URL: http://{host}:{port}")
    click.echo(f"Debug: {debug}")
    click.echo(f"Reload: {reload}")
    click.echo("")

    try:
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            log_level=log_level,
        )
    except Exception as exc:
        click.secho(f"Error: {exc}", fg="red")
        sys.exit(1)
