from backend.api.token.model import Token, TokenUpdate
from backend.api.user.model import User
from backend.databases.db import get_by_filter, get_by_id, insert_row, update_row
from backend.utils.authentic import create_access_token, create_refresh_token
from backend.utils.constants import Message, TokenType
from backend.utils.error_message import InvalidRequestException


def get_token(db_session, token_data: Token):
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
    user = get_by_id(db_session, User, uid)
    if not user:
        raise InvalidRequestException(message=Message.USER_NOT_FOUND)

    access_token = create_access_token(
        {"user_id": uid, "email": email, "refresh_token": refresh_token}
    )
    return access_token


def generate_tokens(db_session, uid, email):
    """
    Generate access token code when user login with 3rd authentication
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
