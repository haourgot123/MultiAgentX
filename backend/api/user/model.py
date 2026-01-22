from datetime import datetime
from typing import Literal, Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    UnicodeText,
)
from sqlalchemy.orm import relationship

from backend.databases.db import Base
from backend.exceptions.model import IvalidRequestException
from backend.utils.authentic import get_hash_password, verify_password
from backend.utils.utils import validate_and_normalize_phone

user_roles = Table(
    "User_Roles",
    Base.metadata,
    Column(
        "user_id", Integer, ForeignKey("User.id", ondelete="CASCADE"), primary_key=True
    ),
    Column(
        "role_id", Integer, ForeignKey("Role.id", ondelete="CASCADE"), primary_key=True
    ),
)


class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(UnicodeText, unique=True, index=True)
    password = Column(String, default=None)
    full_name = Column(UnicodeText, default=None)
    username = Column(UnicodeText, unique=True, index=True)
    date_of_birth = Column(DateTime(timezone=True), nullable=True, default=None)
    phone_number = Column(UnicodeText, nullable=True, default=None)
    country = Column(UnicodeText, nullable=True, default=None)
    gender = Column(UnicodeText, nullable=True, default=None)
    first_login = Column(DateTime(timezone=True), nullable=True, default=None)
    last_login = Column(DateTime(timezone=True), nullable=True, default=None)
    deleted = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    def set_password(self, password: str):
        self.password = get_hash_password(password)

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password)

    def change_password(self, password: str):
        self.password = get_hash_password(password)

    token = relationship("Token", back_populates="user")

    roles = relationship("Role", secondary=user_roles, back_populates="users")


class Role(Base):
    __tablename__ = "Role"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(UnicodeText, unique=True, index=True)
    description = Column(UnicodeText, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)
    users = relationship("User", secondary=user_roles, back_populates="roles")


class RoleResponse(BaseModel):
    id: int = Field(..., description="ID")
    name: str = Field(..., description="Name")
    description: Optional[str] = Field(None, description="Description")
    created_at: Optional[datetime] = Field(None, description="Created At")
    updated_at: Optional[datetime] = Field(None, description="Updated At")

    model_config = ConfigDict(from_attributes=True)


class UserCreateRequest(BaseModel):
    email: EmailStr = Field(..., description="Email")
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
    full_name: Optional[str] = Field(None, description="Full Name")
    date_of_birth: Optional[datetime] = Field(None, description="Date of Birth")
    phone_number: Optional[str] = Field(None, description="Phone Number")
    country: Optional[str] = Field(None, description="Country")
    gender: Optional[str] = Field(None, description="Gender")
    roles: Optional[list[int]] = Field(None, description="Role IDs")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if len(v) < 8:
            raise IvalidRequestException(message="Invalid password")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, v):
        if v is not None and v > datetime.now():
            raise IvalidRequestException(message="Invalid date of birth")
        return v

    @model_validator(mode="after")
    def validate_phone_number(self):
        if self.phone_number:
            if not self.country:
                raise IvalidRequestException(message="Country is required")
            self.phone_number = validate_and_normalize_phone(
                self.phone_number, self.country
            )
        return self


class UserUpdateRequest(BaseModel):
    email: Optional[str] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Full Name")
    date_of_birth: Optional[datetime] = Field(None, description="Date of Birth")
    phone_number: Optional[str] = Field(None, description="Phone Number")
    country: Optional[str] = Field(None, description="Country")
    gender: Optional[str] = Field(None, description="Gender")
    deleted: Optional[bool] = Field(False, description="Deleted")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password")
    roles: Optional[list[int]] = Field(None, description="Role IDs")

    @field_validator("password")
    @classmethod
    def validate_password(cls, v):
        if v is None:
            return v
        if len(v) < 8:
            raise IvalidRequestException(message="Invalid password")
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, v):
        if v is not None and v > datetime.now():
            raise IvalidRequestException(message="Invalid date of birth")
        return v

    @model_validator(mode="after")
    def validate_phone_number(self):
        if self.phone_number:
            if not self.country:
                raise IvalidRequestException(message="Country is required")
            self.phone_number = validate_and_normalize_phone(
                self.phone_number, self.country
            )
        return self


class UserResponse(BaseModel):
    id: int = Field(..., description="ID")
    email: str = Field(..., description="Email")
    full_name: Optional[str] = Field(None, description="Full Name")
    username: Optional[str] = Field(None, description="Username")
    date_of_birth: Optional[datetime] = Field(None, description="Date of Birth")
    phone_number: Optional[str] = Field(None, description="Phone Number")
    country: Optional[str] = Field(None, description="Country")
    gender: Optional[str] = Field(None, description="Gender")
    roles: Optional[list[RoleResponse]] = Field(None, description="Roles")
    first_login: Optional[datetime] = Field(None, description="First Login")
    last_login: Optional[datetime] = Field(None, description="Last Login")
    deleted: bool = Field(..., description="Deleted")
    created_at: datetime = Field(..., description="Created At")
    updated_at: datetime = Field(..., description="Updated At")

    model_config = ConfigDict(from_attributes=True)


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")


class LoginResponse(BaseModel):
    user: UserResponse = Field(..., description="User")
    refresh_token: str = Field(..., description="Refresh Token")
    access_token: str = Field(..., description="Access Token")


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., description="Old Password")
    new_password: str = Field(..., description="New Password")


class ChangePasswordResponse(BaseModel):
    message: str = Field(..., description="Message")


class SelfUserInformationUpdateRequest(BaseModel):
    full_name: Optional[str] = Field(None, description="Full Name")
    date_of_birth: Optional[datetime] = Field(None, description="Date of Birth")
    phone_number: Optional[str] = Field(None, description="Phone Number")
    country: Optional[str] = Field(None, description="Country")
    gender: Optional[Literal["male", "female", "other"]] = Field(
        None, description="Gender"
    )

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, v):
        if v is not None and v > datetime.now():
            raise IvalidRequestException(message="Invalid date of birth")
        return v

    @model_validator(mode="after")
    def validate_phone_number(self):
        if self.phone_number:
            if not self.country:
                raise IvalidRequestException(message="Country is required")
            self.phone_number = validate_and_normalize_phone(
                self.phone_number, self.country
            )
        return self


class SelfUserInformationUpdateResponse(BaseModel):
    message: str = Field(..., description="Message")
