from click.testing import CliRunner
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from loguru import logger
from sqlalchemy.orm import Session
from starlette.requests import Request

from backend.cli import downgrade_database, upgrade_database
from backend.utils.constants import Message, RoleType
from backend.utils.dependency import get_current_user, get_db

database_router = APIRouter(
    prefix="/revision", tags=["Revision"], dependencies=[Depends(get_current_user)]
)


def _check_admin_permission(request: Request, db_session: Session):
    """Check if the current user has admin permissions.
    
    Args:
        request: FastAPI request object containing user state.
        db_session: Database session for querying user roles.
        
    Raises:
        HTTPException: If user doesn't have admin role.
    """
    from backend.api.user.service import user_service
    
    roles = user_service.get_user_roles_by_id(db_session, request.state.user_id)
    role_ids = [role.id for role in roles]
    if RoleType.ADMIN.value not in role_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=Message.MESSAGE_PERMISSION_DENIED,
        )


@database_router.post("/upgrade")
async def upgrade_database_api(
    request: Request,
    revision: str = "head",
    db_session: Session = Depends(get_db),
):
    """Upgrade database to a specific revision.
    
    Args:
        request: FastAPI request object.
        revision: Target revision (default: "head" for latest).
        db_session: Database session.
        
    Returns:
        JSONResponse with upgrade result.
    """
    _check_admin_permission(request, db_session)
    
    logger.info(f"User {request.state.user_id} initiating database upgrade to revision: {revision}")
    
    try:
        runner = CliRunner()
        command_args = ["--revision", revision]
        result = runner.invoke(upgrade_database, command_args)

        if result.exit_code != 0:
            logger.error(f"Database upgrade failed: {result.output}")
            return JSONResponse(content={"error": result.output}, status_code=400)

        logger.info(f"Database upgrade completed successfully: {result.output}")
        return JSONResponse(
            content={"message": result.output, "status": "success"},
            status_code=200,
        )
    except PermissionError as e:
        logger.error(f"Permission error during database upgrade: {str(e)}")
        return JSONResponse(
            content={"error": "Permission denied for database operation"},
            status_code=403,
        )
    except FileNotFoundError as e:
        logger.error(f"File not found during database upgrade: {str(e)}")
        return JSONResponse(
            content={"error": "Migration file not found"},
            status_code=404,
        )
    except Exception as e:
        logger.exception(f"Unexpected error during database upgrade: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@database_router.post("/downgrade")
async def downgrade_database_api(
    request: Request,
    revision: str = "-1",
    db_session: Session = Depends(get_db),
):
    """Downgrade database to a specific revision.
    
    Args:
        request: FastAPI request object.
        revision: Target revision (default: "-1" for one step back).
        db_session: Database session.
        
    Returns:
        JSONResponse with downgrade result.
    """
    _check_admin_permission(request, db_session)
    
    logger.warning(
        f"User {request.state.user_id} initiating database downgrade to revision: {revision}"
    )
    
    try:
        runner = CliRunner()
        command_args = ["--revision", revision]
        result = runner.invoke(downgrade_database, command_args)

        if result.exit_code != 0:
            logger.error(f"Database downgrade failed: {result.output}")
            return JSONResponse(content={"error": result.output}, status_code=400)

        logger.info(f"Database downgrade completed successfully: {result.output}")
        return JSONResponse(
            content={"message": result.output, "status": "success"},
            status_code=200,
        )
    except PermissionError as e:
        logger.error(f"Permission error during database downgrade: {str(e)}")
        return JSONResponse(
            content={"error": "Permission denied for database operation"},
            status_code=403,
        )
    except FileNotFoundError as e:
        logger.error(f"File not found during database downgrade: {str(e)}")
        return JSONResponse(
            content={"error": "Migration file not found"},
            status_code=404,
        )
    except Exception as e:
        logger.exception(f"Unexpected error during database downgrade: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)
