from pydantic import BaseModel
from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, UnicodeText
from sqlalchemy.orm import relationship

from backend.databases.db import Base
from backend.utils.constants import TokenType


class TimeStampMixin:
    created_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=True)


class Token(Base, TimeStampMixin):
    __tablename__ = "Token"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("User.id"), nullable=False)
    token = Column(UnicodeText, nullable=False)
    token_type = Column(Integer, nullable=False, default=TokenType.REFRESH.value)
    user = relationship("User", back_populates="token")

    __table_args__ = (
        Index("token_idx_token", "token", "token_type", postgresql_using="btree"),
    )


class TokenUpdate(BaseModel):
    token: str
