from typing import Any, Dict, List
from sqlalchemy import JSON, Column, ForeignKey, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from visualization.backend.db.config import settings
from sqlalchemy.orm import sessionmaker, relationship
import asyncio


class Base(DeclarativeBase):
    pass


class Entity(Base):
    __tablename__ = "entities"
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    file = Column(Text, nullable=False)
    start_line = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)
    comments = Column(JSON, nullable=False, default=[])

    inherits = relationship(
        "Inherit", back_populates="child", cascade="all, delete-orphan"
    )
    calls_made = relationship(
        "Call",
        back_populates="caller",
        cascade="all, delete-orphan",
        foreign_keys="Call.caller_id",
    )
    calls_received = relationship(
        "Call",
        back_populates="callee",
        cascade="all, delete-orphan",
        foreign_keys="Call.callee_id",
    )
    methods = relationship(
        "Method", back_populates="klass", cascade="all, delete-orphan"
    )


class Inherit(Base):
    __tablename__ = "inherits"
    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Text, ForeignKey("entities.id"), nullable=False)
    parent_id = Column(Text, nullable=False)  # can be entity.id or plain name

    child = relationship("Entity", back_populates="inherits")


class Call(Base):
    __tablename__ = "calls"
    id = Column(Integer, primary_key=True, autoincrement=True)
    caller_id = Column(Text, ForeignKey("entities.id"), nullable=False)
    callee_id = Column(Text, nullable=False)

    caller = relationship(
        "Entity", back_populates="calls_made", foreign_keys=[caller_id]
    )
    callee = relationship(
        "Entity", back_populates="calls_received", foreign_keys=[callee_id]
    )


class Method(Base):
    __tablename__ = "methods"
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Text, ForeignKey("entities.id"), nullable=False)
    method_id = Column(Text, nullable=False)

    klass = relationship("Entity", back_populates="methods")


async def create_all_tables():
    async_engine = create_async_engine(settings.DATABASE_URL, echo=True)
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    asyncio.run(create_all_tables())
