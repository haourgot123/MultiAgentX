from sqlalchemy.orm import Session
from loguru import logger
from backend.api.user.model import (
    LoginRequest,
    User,
    UserRegisterRequest,
    UserUpdateRequest,
    LoginResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
)
from backend.databases.db import get_by_id, get_utc_now, insert_row
from backend.api.token.service import generate_tokens
from backend.utils.constants import Message
from backend.exceptions.model import (
    UserNotFoundException,
    UserEmailAlreadyExistsException,
    UserNameAlreadyExistsException,
    InvalidPasswordException,
    InvalidFullNameException
)



class UserService:
    def __init__(self):
        pass
    
    def get_user_by_email(self, db_session: Session, email: str):
        """ Get user by email from database """
        user = db_session.query(User).filter(User.email == email.lower()).first()
        return user
    
    def get_user_by_username(self, db_session: Session, username: str):
        """ Get user by username from database """
        user = db_session.query(User).filter(User.username == username.lower()).first()
        return user

    def get_user_by_id(self, db_session: Session, user_id: int):
        """ Get user by id from database """
        user = get_by_id(db_session, User, user_id)
        return user

    def create_new_user(self, db_session: Session, user_in: UserRegisterRequest):
        """ Create new user in database """
        # Check email and username are already exists
        if self.get_user_by_email(db_session, user_in.email):
            raise UserEmailAlreadyExistsException()
        if self.get_user_by_username(db_session, user_in.username):
            raise UserNameAlreadyExistsException()
        
        # Create new user
        new_user = User(
            email=user_in.email.lower(),
            full_name=user_in.full_name,
            username=user_in.username.lower(),
        )
        new_user.set_password(user_in.password)
        
        new_user.created_at = get_utc_now()
        new_user.updated_at = get_utc_now()
        new_user = insert_row(db_session, new_user)
        return new_user
    
    def update_user_by_id(self, db_session: Session, user_id: int, user_update: UserUpdateRequest):
        """ Update user by id in database """
        
        logger.info(f"Updating user by id: {user_update}")

        user = self.get_user_by_id(db_session, user_id)
        if not user:
            raise UserNotFoundException()
        
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
            is_username_exists = self.get_user_by_username(db_session, user_update.username)
            if is_username_exists:
                raise UserNameAlreadyExistsException()
            user.username = user_update.username.lower()
        
        # Update updated_at
        user.updated_at = get_utc_now()
        
        db_session.commit()
        db_session.refresh(user)
        return user

    def delete_user_by_id(self, db_session: Session, user_id: int):
        """ Delete user by id in database """
        user = self.get_user_by_id(db_session, user_id)
        if not user:
            raise UserNotFoundException()
        user.deleted = True
        db_session.commit()
        db_session.refresh(user)
        return user
    
    def login_user(self, db_session: Session, login_request: LoginRequest):
        """ Login user in database """
        user = self.get_user_by_username(db_session, login_request.username) or self.get_user_by_email(db_session, login_request.username)
        if not user:
            raise UserNotFoundException()
        if not user.check_password(login_request.password):
            raise InvalidPasswordException()
        if not user.first_login:
            user.first_login = get_utc_now()
        user.last_login = get_utc_now()
        refresh_token, access_token = generate_tokens(db_session, user.id, user.email)
        db_session.commit()
        db_session.refresh(user)
        return LoginResponse(user=user, refresh_token=refresh_token, access_token=access_token)
    
    
    def logout_user(self, db_session: Session, user_id: int):
        """ Logout user in database """
        user = self.get_user_by_id(db_session, user_id)
        if not user:
            raise UserNotFoundException()
        user.last_login = get_utc_now()
        db_session.commit()
        db_session.refresh(user)
        return user
    
    def change_password_user(self, db_session: Session, user_id: int, change_password_request: ChangePasswordRequest):
        """ Change password user in database """
        
        user = self.get_user_by_id(db_session, user_id)
        if not user:
            raise UserNotFoundException()
        if user.check_password(change_password_request.old_password):
            user.change_password(change_password_request.new_password)
            db_session.commit()
            db_session.refresh(user)
            return ChangePasswordResponse(user=user, message=Message.PASSWORD_CHANGED_SUCCESSFULLY)
        else:
            raise InvalidPasswordException()

    
user_service = UserService()

