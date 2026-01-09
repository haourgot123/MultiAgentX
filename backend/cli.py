import os
from pathlib import Path

import click
import uvicorn

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig
from backend.config.settings import _settings
from backend.databases.db import Base, engine

BASE_DIR = Path(__file__).resolve().parent.parent  # MultiAgentX/
ALEMBIC_PATH = BASE_DIR / "alembic.ini"

db = _settings.postgres


@click.group()
def chatfile_cli():
    """Command-line interface to Chatbot."""
    pass


@chatfile_cli.group("database")
def chatfile_database():
    """Command-line interface to Chatbot database commands."""
    click.secho(
        f"Connecting to database {db.database} with host {db.host} and port {db.port}...",
        fg="red",
    )


@chatfile_cli.group("server")
def chatfile_server():
    """Command-line interface to Chatbot server commands."""
    pass


@chatfile_server.command("start")
def server_start():
    uvicorn.run("app.main:app", port=8300, host="0.0.0.0")


@chatfile_server.command("develop")
def server_develop():
    uvicorn.run("app.main:socket_app", reload=True, port=8000, host="0.0.0.0")


@chatfile_database.command("init")
def init_database():
    """Initializes a new database."""
    Base.metadata.create_all(engine)
    alembic_path = os.path.join(ALEMBIC_PATH)
    alembic_cfg = AlembicConfig(alembic_path)
    alembic_command.stamp(alembic_cfg, "head")
    click.secho("Success.", fg="green")


@chatfile_database.command("revision")
@click.option("-m", "--message", default=None, help="Revision message")
@click.option(
    "--autogenerate",
    is_flag=True,
    help=(
        "Populate revision script with candidate migration "
        "operations, based on comparison of database to model"
    ),
)
@click.option(
    "--sql",
    is_flag=True,
    help=("Don't emit SQL to database - dump to standard output " "instead"),
)
def revision_database(message, autogenerate, sql):
    alembic_path = os.path.join(ALEMBIC_PATH)
    alembic_cfg = AlembicConfig(alembic_path)
    alembic_command.revision(
        config=alembic_cfg, message=message, autogenerate=autogenerate, sql=sql
    )
    click.secho("Success.", fg="green")


@chatfile_database.command("upgrade")
@click.option(
    "--tag",
    default=None,
    help="Arbitrary 'tag' name - can be used by custom env.py scripts.",
)
@click.option(
    "--sql",
    is_flag=True,
    default=False,
    help="Don't emit SQL to database - dump to standard output instead.",
)
@click.option("--revision", nargs=1, default="head", help="Revision identifier.")
def upgrade_database(tag, sql, revision):
    """Upgrades database schema to newest version."""
    from alembic import migration

    alembic_path = os.path.join(ALEMBIC_PATH)
    alembic_cfg = AlembicConfig(alembic_path)

    conn = engine.connect()
    context = migration.MigrationContext.configure(conn)
    current_rev = context.get_current_revision()
    if not current_rev:
        Base.metadata.create_all(engine)
        alembic_command.stamp(alembic_cfg, "head")
    else:
        alembic_command.upgrade(alembic_cfg, revision, sql=sql, tag=tag)
        click.secho(f"{alembic_path}", fg="red")

    click.secho("Success.", fg="green")


@chatfile_database.command("downgrade")
@click.option(
    "--tag",
    default=None,
    help="Arbitrary 'tag' name - can be used by custom env.py scripts.",
)
@click.option(
    "--sql",
    is_flag=True,
    default=False,
    help="Don't emit SQL to database - dump to standard output instead.",
)
@click.option("--revision", nargs=1, default="head", help="Revision identifier.")
def downgrade_database(tag, sql, revision):
    """Downgrades database schema to next newest version."""
    alembic_path = os.path.join(ALEMBIC_PATH)
    alembic_cfg = AlembicConfig(alembic_path)

    if sql and revision == "-1":
        revision = "head:-1"

    alembic_command.downgrade(alembic_cfg, revision, sql=sql, tag=tag)
    click.secho("Success.", fg="green")


def entrypoint():
    """The entry that the CLI is executed from"""
    try:
        chatfile_cli()
    except Exception as e:
        click.secho(f"ERROR: {e}", bold=True, fg="red")


if __name__ == "__main__":
    entrypoint()
