from backend.api.token.model import Token, TokenUpdate
from backend.api.user.model import User
from backend.databases.db import get_by_filter, get_by_id, insert_row, update_row
from backend.exceptions.model import ObjectNotFoundException
from backend.utils.authentic import create_access_token, create_refresh_token
from backend.utils.constants import Message, TokenType


def get_token(db_session, token_data: Token):
    """Retrieve a token from the database based on user_id and token_type.

    Args:
        db_session: SQLAlchemy database session.
        token_data (Token): Token object containing user_id and token_type to filter.

    Returns:
        Token | None: Token object if found, None otherwise.
    """
    return get_by_filter(
        db_session=db_session,
        table=Token,
        filters=[
            Token.user_id == token_data.user_id,
            Token.token_type == token_data.token_type,
        ],
        first=True,
    )


def generate_access_token(db_session, email, uid, refresh_token):
    """Generate a new access token for a user.

    Args:
        db_session: SQLAlchemy database session.
        email (str): User's email address.
        uid (int): User's ID.
        refresh_token (str): User's current refresh token.

    Returns:
        str: JWT-encoded access token.
    """
    user = get_by_id(db_session, User, uid)
    if not user:
        raise ObjectNotFoundException(message=Message.MESSAGE_USER_NOT_FOUND)

    access_token = create_access_token(
        data={"user_id": uid, "email": email, "refresh_token": refresh_token}
    )
    return access_token


def generate_tokens(db_session, uid, email):
    """Generate access and refresh token pair for user login.

    Args:
        db_session: SQLAlchemy database session.
        uid (int): User's ID.
        email (str): User's email address.

    Returns:
        tuple[str, str]: Tuple containing (refresh_token, access_token).
    """

    token = get_token(
        db_session,
        Token(
            user_id=uid,
            token_type=TokenType.REFRESH.value,
        ),
    )

    # Always generate a new refresh token on login
    refresh_token = create_refresh_token(uid, email)

    if not token:
        # Add a new token to database
        insert_row(
            db_session,
            Token(
                user_id=uid,
                token=refresh_token,
                token_type=TokenType.REFRESH.value,
            ),
        )
    else:
        # Always update the existing token with new refresh token
        update_row(db_session, token, TokenUpdate(token=refresh_token))

    access_token = generate_access_token(db_session, email, uid, refresh_token)
    return refresh_token, access_token
