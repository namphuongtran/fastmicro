"""CQRS / Mediator pattern for enterprise microservices.

This package provides Command-Query Responsibility Segregation (CQRS)
building blocks with a Mediator for dispatching commands and queries
to their respective handlers, plus a composable pipeline for
cross-cutting concerns (logging, validation, timing, …).

Quick start::

    from dataclasses import dataclass
    from shared.cqrs import (
        Command, CommandHandler, Query, QueryHandler, Mediator,
    )

    @dataclass(frozen=True)
    class CreateUser(Command[str]):
        email: str
        name: str

    class CreateUserHandler(CommandHandler[CreateUser, str]):
        async def handle(self, command: CreateUser) -> str:
            user = await repo.add(User(email=command.email, name=command.name))
            return user.id

    @dataclass(frozen=True)
    class GetUserById(Query[UserDTO | None]):
        user_id: str

    class GetUserByIdHandler(QueryHandler[GetUserById, UserDTO | None]):
        async def handle(self, query: GetUserById) -> UserDTO | None:
            return await repo.get(query.user_id)

    mediator = Mediator()
    mediator.register_command_handler(CreateUser, CreateUserHandler())
    mediator.register_query_handler(GetUserById, GetUserByIdHandler())

    user_id = await mediator.send(CreateUser(email="a@b.com", name="Alice"))
    user    = await mediator.send(GetUserById(user_id=user_id))
"""

from __future__ import annotations

from shared.cqrs.bus import MessageBus
from shared.cqrs.commands import Command, CommandBus, CommandHandler
from shared.cqrs.mediator import Mediator
from shared.cqrs.pipeline import (
    LoggingBehavior,
    PipelineBehavior,
    TimingBehavior,
    ValidationBehavior,
)
from shared.cqrs.queries import Query, QueryBus, QueryHandler

__all__ = [
    # Generic bus
    "MessageBus",
    # Commands
    "Command",
    "CommandHandler",
    "CommandBus",
    # Queries
    "Query",
    "QueryHandler",
    "QueryBus",
    # Mediator
    "Mediator",
    # Pipeline behaviors
    "PipelineBehavior",
    "LoggingBehavior",
    "TimingBehavior",
    "ValidationBehavior",
]
