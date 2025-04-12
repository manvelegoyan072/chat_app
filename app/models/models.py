from sqlalchemy import Column, Integer, String, Enum, ForeignKey, Table, DateTime, Boolean
from sqlalchemy.orm import relationship, declarative_base
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum as PyEnum
from datetime import datetime

Base = declarative_base()

# Типы чатов
class ChatType(PyEnum):
    PERSONAL = "personal"
    GROUP = "group"

# Типы ролей
class UserRole(PyEnum):
    USER = "user"
    ADMIN = "admin"

# Таблица связей для участников группы
group_participants = Table(
    "group_participants",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("groups.id"), primary_key=True),
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True)
)

# Модель пользователя
# Модель для refresh-токенов
class RefreshToken(Base):
    __tablename__ = "refresh_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String(512), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    user = relationship("User", back_populates="refresh_tokens")

# Модель пользователя
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)  # Новое поле
    created_groups = relationship("Group", back_populates="creator")
    groups = relationship("Group", secondary=group_participants, back_populates="participants")
    messages = relationship("Message", back_populates="sender")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")

# Модель чата
class Chat(Base):
    __tablename__ = "chats"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    type = Column(Enum(ChatType), default=ChatType.PERSONAL, nullable=False)
    messages = relationship("Message", back_populates="chat")
    group = relationship("Group", back_populates="chat", uselist=False)

# Модель группы
class Group(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    chat_id = Column(Integer, ForeignKey("chats.id"), unique=True, nullable=False)
    creator = relationship("User", back_populates="created_groups")
    participants = relationship("User", secondary=group_participants, back_populates="groups")
    chat = relationship("Chat", back_populates="group")

# Модель сообщения
class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(Integer, ForeignKey("chats.id"), index=True, nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String(2000), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    uuid = Column(String(36), unique=True, nullable=False)  # Для предотвращения дублирования
    chat = relationship("Chat", back_populates="messages")
    sender = relationship("User", back_populates="messages")