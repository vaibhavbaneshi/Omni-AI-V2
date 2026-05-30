"""Test data factories (factory_boy + SQLAlchemy)."""

from __future__ import annotations

import factory
from factory.alchemy import SQLAlchemyModelFactory

from app.models.chat_session import ChatSession
from app.models.message import Message
from app.models.user import User
from app.services.auth_service import hash_password


class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    username = factory.Sequence(lambda n: f"testuser{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    password = factory.LazyFunction(lambda: hash_password("test-password"))


class ChatSessionFactory(SQLAlchemyModelFactory):
    class Meta:
        model = ChatSession
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    title = "Test Chat"
    user_id = factory.LazyAttribute(lambda _: UserFactory().id)
    workspace_id = "default"

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        user = kwargs.pop("user", None)
        if user is not None:
            kwargs["user_id"] = user.id
        return super()._create(model_class, *args, **kwargs)


class MessageFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Message
        sqlalchemy_session = None
        sqlalchemy_session_persistence = "commit"

    role = "user"
    content = factory.Sequence(lambda n: f"Message content {n}")
    session_id = 1
    user_id = 1

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        session = kwargs.pop("session", None)
        if session is not None:
            kwargs["session_id"] = session.id
            kwargs["user_id"] = session.user_id
        return super()._create(model_class, *args, **kwargs)


def bind_factories(session) -> None:
    """Attach SQLAlchemy session to all factories for a test."""
    for factory_cls in (UserFactory, ChatSessionFactory, MessageFactory):
        factory_cls._meta.sqlalchemy_session = session
