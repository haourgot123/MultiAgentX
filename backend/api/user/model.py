from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, Column, DateTime, Integer, String, UnicodeText
from sqlalchemy.orm import relationship

from backend.databases.db import Base
from backend.utils.authentic import get_hash_password, verify_password


class User(Base):
    __tablename__ = "User"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(UnicodeText, unique=True, index=True)
    password = Column(String, default=None)
    full_name = Column(UnicodeText, default=None)
    username = Column(UnicodeText, unique=True, index=True)
    first_login = Column(DateTime(timezone=True), nullable=True, default=None)
    last_login = Column(DateTime(timezone=True), nullable=True, default=None)
    deleted = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)

    def set_password(self, password: str):
        self.password = get_hash_password(password)

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password)

    token = relationship("Token", back_populates="user")


class UserRegisterRequest(BaseModel):
    email: EmailStr = Field(..., description="Email")
    password: str = Field(..., description="Password")
    full_name: str = Field(..., description="Full Name")
    username: str = Field(..., description="Username")


class UserRegisterResponse(BaseModel):
    id: int = Field(..., description="ID")
    email: EmailStr = Field(..., description="Email")
    full_name: Optional[str] = Field(None, description="Full Name")
    username: Optional[str] = Field(None, description="Username")
    first_login: Optional[datetime] = Field(None, description="First Login")
    last_login: Optional[datetime] = Field(None, description="Last Login")
    deleted: bool = Field(..., description="Deleted")
    created_at: datetime = Field(..., description="Created At")
    updated_at: datetime = Field(..., description="Updated At")


class UserResponse(BaseModel):
    id: int = Field(..., description="ID")
    email: EmailStr = Field(..., description="Email")
    full_name: Optional[str] = Field(None, description="Full Name")
    username: Optional[str] = Field(None, description="Username")
    first_login: Optional[datetime] = Field(None, description="First Login")
    last_login: Optional[datetime] = Field(None, description="Last Login")
    deleted: bool = Field(..., description="Deleted")
    created_at: datetime = Field(..., description="Created At")
    updated_at: datetime = Field(..., description="Updated At")


class UserUpdateRequest(BaseModel):
    email: Optional[EmailStr] = Field(None, description="Email")
    full_name: Optional[str] = Field(None, description="Full Name")
    username: Optional[str] = Field(None, description="Username")
    password: Optional[str] = Field(None, description="Password")


class LoginRequest(BaseModel):
    username: str = Field(..., description="Username")
    password: str = Field(..., description="Password")
