from click.testing import CliRunner
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from starlette.requests import Request

from backend.cli import downgrade_database, upgrade_database

database_router = APIRouter(prefix="/revision", tags=["Revision"])


@database_router.post("/upgrade")
async def upgrade_database_api(
    request: Request,
    tag: str = None,
    sql: bool = False,
    revision: str = "head",
):
    # is_admin(request)
    try:
        # Construct the command with the relevant options
        runner = CliRunner()
        command_args = ["--revision", revision]

        # if tag:
        #     command_args.extend(["--tag", tag])
        # if sql:
        #     command_args.append("--sql")

        result = runner.invoke(upgrade_database, command_args)

        if result.exit_code != 0:
            return JSONResponse(content={"error": result.output}, status_code=400)

        return JSONResponse(
            content={"message": result.output, "status": "success"},
            status_code=200,
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@database_router.post("/downgrade")
async def downgrade_database_api(
    request: Request, tag: str = None, sql: bool = False, revision: str = "-1"
):
    # is_admin(request)
    try:
        # Construct the command with the relevant options for downgrade
        runner = CliRunner()
        command_args = ["--revision", revision]

        # if tag:
        #     command_args.extend(["--tag", tag])
        # if sql:
        #     command_args.append("--sql")

        result = runner.invoke(downgrade_database, command_args)

        if result.exit_code != 0:
            return JSONResponse(content={"error": result.output}, status_code=400)

        return JSONResponse(
            content={"message": result.output, "status": "success"},
            status_code=200,
        )
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
