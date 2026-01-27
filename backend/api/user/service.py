from loguru import logger
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.api.token.service import generate_tokens
from backend.api.user.model import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    LoginResponse,
    Role,
    SelfUserInformationUpdateRequest,
    SelfUserInformationUpdateResponse,
    User,
    UserCreateRequest,
    UserUpdateRequest,
)
from backend.databases.db import get_by_id, get_utc_now, insert_row
from backend.exceptions.model import InvalidRequestException, ObjectNotFoundException
from backend.utils.constants import Message


class UserService:
    """Service class for managing user-related operations."""

    def get_user_by_email(self, db_session: Session, email: str):
        """Retrieve a user by their email address.

        Args:
            db_session (Session): SQLAlchemy database session.
            email (str): Email address to search for (case-insensitive).

        Returns:
            User | None: User object if found, None otherwise.
        """
        user = db_session.query(User).filter(User.email == email.lower()).first()
        if not user:
            raise ObjectNotFoundException(message=Message.MESSAGE_USER_NOT_FOUND)
        return user

    def get_user_by_username(self, db_session: Session, username: str):
        """Retrieve a user by their username.

        Args:
            db_session (Session): SQLAlchemy database session.
            username (str): Username to search for (case-insensitive).

        Returns:
            User | None: User object if found, None otherwise.
        """
        user = db_session.query(User).filter(User.username == username.lower()).first()
        if not user:
            raise ObjectNotFoundException(message=Message.MESSAGE_USER_NOT_FOUND)
        return user

    def get_user_by_id(self, db_session: Session, user_id: int):
        """Retrieve a user by their ID.

        Args:
            db_session (Session): SQLAlchemy database session.
            user_id (int): User's unique identifier.

        Returns:
            User | None: User object if found, None otherwise.
        """
        user = get_by_id(db_session, User, user_id)
        if not user:
            raise ObjectNotFoundException(message=Message.MESSAGE_USER_NOT_FOUND)
        return user

    def get_user_roles_by_id(self, db_session: Session, user_id: int):
        """Retrieve the roles assigned to a user.

        Args:
            db_session (Session): SQLAlchemy database session.
            user_id (int): User's unique identifier.

        Returns:
            list: List of roles assigned to the user.
        """
        user = self.get_user_by_id(db_session, user_id)
        return user.roles

    def create_new_user(self, db_session: Session, user_in: UserCreateRequest):
        """Create a new user in the database.

        Args:
            db_session (Session): SQLAlchemy database session.
            user_in (UserCreateRequest): User creation request with email, username, full_name, password, and roles.

        Returns:
            User: Newly created user object.
        """
        # Check if email or username already exists
        existing_user_email = (
            db_session.query(User).filter(User.email == user_in.email.lower()).first()
        )
        if existing_user_email:
            raise InvalidRequestException(
                message=Message.MESSAGE_USER_EMAIL_ALREADY_EXISTS
            )

        existing_user_username = (
            db_session.query(User)
            .filter(User.username == user_in.username.lower())
            .first()
        )
        if existing_user_username:
            raise InvalidRequestException(
                message=Message.MESSAGE_USERNAME_ALREADY_EXISTS
            )
        # Create new user
        new_user = User(
            email=user_in.email,
            full_name=user_in.full_name,
            username=user_in.username,
            date_of_birth=user_in.date_of_birth,
            phone_number=user_in.phone_number,
            country=user_in.country,
            gender=user_in.gender,
        )
        new_user.set_password(user_in.password)

        roles = db_session.query(Role).filter(Role.id.in_(user_in.roles)).all()
        new_user.roles = roles
        new_user.created_at = get_utc_now()
        new_user.updated_at = get_utc_now()
        try:
            new_user = insert_row(db_session, new_user)
            return new_user
        except PermissionError as e:
            db_session.rollback()
            raise e
        except SQLAlchemyError as e:
            db_session.rollback()
            raise e

    def update_user_by_id(
        self, db_session: Session, user_id: int, user_update: UserUpdateRequest
    ):
        """Update an existing user's information.

        Args:
            db_session (Session): SQLAlchemy database session.
            user_id (int): ID of the user to update.
            user_update (UserUpdateRequest): Update request with optional password, full_name, username, and deleted fields.

        Returns:
            User: Updated user object.
        """

        logger.info(f"Updating user by id: {user_update}")

        user = self.get_user_by_id(db_session, user_id)

        # Update password if provided
        if user_update.password:
            user.change_password(user_update.password)

        # Update fullname if provided
        if user_update.full_name:
            user.full_name = user_update.full_name

        # Update deleted if provided
        if user_update.deleted:
            user.deleted = user_update.deleted

        # Update username if provided
        if user_update.username:
            # Check if username already exists (excluding current user)
            existing_user = (
                db_session.query(User)
                .filter(
                    User.username == user_update.username.lower(), User.id != user_id
                )
                .first()
            )
            if existing_user:
                raise InvalidRequestException(
                    message=Message.MESSAGE_USERNAME_ALREADY_EXISTS
                )
            user.username = user_update.username.lower()

        # Update updated_at
        user.updated_at = get_utc_now()

        try:
            db_session.commit()
            db_session.refresh(user)
            return user
        except PermissionError as e:
            db_session.rollback()
            raise e
        except SQLAlchemyError as e:
            db_session.rollback()
            raise e

    def delete_user_by_id(self, db_session: Session, user_id: int):
        """Soft delete a user by setting their deleted flag to True.

        Args:
            db_session (Session): SQLAlchemy database session.
            user_id (int): ID of the user to delete.

        Returns:
            User: Updated user object with deleted flag set to True.
        """
        user = self.get_user_by_id(db_session, user_id)
        user.deleted = True
        try:
            db_session.commit()
            db_session.refresh(user)
            return user
        except PermissionError as e:
            db_session.rollback()
            raise e
        except SQLAlchemyError as e:
            db_session.rollback()
            raise e

    def login_user(self, db_session: Session, login_request: LoginRequest):
        """Authenticate a user and generate access tokens.

        Args:
            db_session (Session): SQLAlchemy database session.
            login_request (LoginRequest): Login request with username (or email) and password.

        Returns:
            LoginResponse: Response object containing user, refresh_token, and access_token.
        """
        # Try to find user by username first, then by email
        try:
            user = self.get_user_by_username(db_session, login_request.username)
        except ObjectNotFoundException:
            try:
                user = self.get_user_by_email(db_session, login_request.username)
            except ObjectNotFoundException:
                raise ObjectNotFoundException(message=Message.MESSAGE_USER_NOT_FOUND)
        if not user.check_password(login_request.password):
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_PASSWORD)
        if not user.first_login:
            user.first_login = get_utc_now()
        user.last_login = get_utc_now()
        refresh_token, access_token = generate_tokens(db_session, user.id, user.email)
        try:
            db_session.commit()
            db_session.refresh(user)
            return LoginResponse(
                user=user, refresh_token=refresh_token, access_token=access_token
            )
        except PermissionError as e:
            db_session.rollback()
            raise e
        except SQLAlchemyError as e:
            db_session.rollback()
            raise e

    def logout_user(self, db_session: Session, user_id: int):
        """Log out a user by updating their last login timestamp.

        Args:
            db_session (Session): SQLAlchemy database session.
            user_id (int): ID of the user to log out.

        Returns:
            User: Updated user object.
        """
        user = self.get_user_by_id(db_session, user_id)
        user.last_login = get_utc_now()
        try:
            # Commit transaction
            db_session.commit()
            # Refresh user
            db_session.refresh(user)
            return user
        except PermissionError as e:
            # Rollback transaction
            db_session.rollback()
            raise e
        except SQLAlchemyError as e:
            db_session.rollback()
            raise e

    def change_password_user(
        self,
        db_session: Session,
        user_id: int,
        change_password_request: ChangePasswordRequest,
    ):
        """Change a user's password after validating the old password.

        Args:
            db_session (Session): SQLAlchemy database session.
            user_id (int): ID of the user changing their password.
            change_password_request (ChangePasswordRequest): Request with old_password and new_password.

        Returns:
            ChangePasswordResponse: Response object containing success message.
        """

        user = self.get_user_by_id(db_session, user_id)
        if user.check_password(change_password_request.old_password):
            user.change_password(change_password_request.new_password)
            try:
                db_session.commit()
                db_session.refresh(user)
                return ChangePasswordResponse(
                    message=Message.MESSAGE_PASSWORD_CHANGED_SUCCESSFULLY
                )
            except PermissionError as e:
                db_session.rollback()
                raise e
            except SQLAlchemyError as e:
                db_session.rollback()
                raise e
        else:
            raise InvalidRequestException(message=Message.MESSAGE_INVALID_PASSWORD)

    def update_self_user_information(
        self,
        db_session: Session,
        user_id: int,
        user_update_request: SelfUserInformationUpdateRequest,
    ):
        """Update self user information.

        Args:
            db_session (Session): SQLAlchemy database session.
            user_id: int,
            user_update_request: SelfUserInformationUpdateRequest,

        Returns:
            SelfUserInformationUpdateResponse: Response object containing success message.
        """
        user = self.get_user_by_id(db_session, user_id)

        if user.deleted:
            raise InvalidRequestException(message=Message.MESSAGE_USER_DELETED)

        if user_update_request.full_name:
            user.full_name = user_update_request.full_name
        if user_update_request.date_of_birth:
            user.date_of_birth = user_update_request.date_of_birth
        if user_update_request.gender:
            user.gender = user_update_request.gender
        if user_update_request.country:
            user.country = user_update_request.country
        if user_update_request.phone_number:
            user.phone_number = user_update_request.phone_number

        try:
            db_session.commit()
            db_session.refresh(user)
            return SelfUserInformationUpdateResponse(
                message=Message.MESSAGE_USER_INFORMATION_UPDATED_SUCCESSFULLY
            )
        except PermissionError as e:
            db_session.rollback()
            raise e
        except SQLAlchemyError as e:
            db_session.rollback()
            raise e


user_service = UserService()
