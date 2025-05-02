import os
from typing import List, Dict, Any

from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    Text,
    ForeignKey,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

Base = declarative_base()

class Entity(Base):
    __tablename__ = 'entities'
    id = Column(Text, primary_key=True)
    name = Column(Text, nullable=False)
    type = Column(Text, nullable=False)
    file = Column(Text, nullable=False)
    start_line = Column(Integer, nullable=False)
    start_char = Column(Integer, nullable=False)
    end_line = Column(Integer, nullable=False)
    end_char = Column(Integer, nullable=False)
    comments = Column(JSON, nullable=False, default=[])

    inherits = relationship('Inherit', back_populates='child', cascade='all, delete-orphan')
    calls_made = relationship('Call', back_populates='caller', cascade='all, delete-orphan', foreign_keys='Call.caller_id')
    calls_received = relationship('Call', back_populates='callee', cascade='all, delete-orphan', foreign_keys='Call.callee_id')
    methods = relationship('Method', back_populates='klass', cascade='all, delete-orphan')

class Inherit(Base):
    __tablename__ = 'inherits'
    id = Column(Integer, primary_key=True, autoincrement=True)
    child_id = Column(Text, ForeignKey('entities.id'), nullable=False)
    parent_id = Column(Text, nullable=False)  # can be entity.id or plain name

    child = relationship('Entity', back_populates='inherits')

class Call(Base):
    __tablename__ = 'calls'
    id = Column(Integer, primary_key=True, autoincrement=True)
    caller_id = Column(Text, ForeignKey('entities.id'), nullable=False)
    callee_id = Column(Text, nullable=False)

    caller = relationship('Entity', back_populates='calls_made', foreign_keys=[caller_id])
    callee = relationship('Entity', back_populates='calls_received', foreign_keys=[callee_id])

class Method(Base):
    __tablename__ = 'methods'
    id = Column(Integer, primary_key=True, autoincrement=True)
    class_id = Column(Text, ForeignKey('entities.id'), nullable=False)
    method_id = Column(Text, nullable=False)

    klass = relationship('Entity', back_populates='methods')


def init_db(db_path: str = 'db.sqlite'):
    if db_path != ':memory:' and os.path.exists(db_path):
        pass
    engine = create_engine(f'sqlite:///{db_path}', echo=False)
    Base.metadata.create_all(engine)
    return engine


def save_entities(entities: List[Dict[str, Any]], db_path: str = 'db.sqlite'):
    """
    Сохраняет список сущностей и их связей в SQLite БД.

    entities: список словарей с ключами:
      - id, name, type, file,
        range: {start: {line, char}, end: {line, char}},
      - inherits: [parent1, parent2, ...],
      - relations: {methods: [...], calls: [...]}
    """
    engine = init_db(db_path)
    Session = sessionmaker(bind=engine)
    session = Session()

    for ent in entities:
        # вставка сущности
        ent_id = ent['id']
        range_ = ent.get('range', {})
        start = range_.get('start', {})
        end = range_.get('end', {})
        comments = ent.get("comments", [])
        if ent["type"] in ("class", "function"):
            entity = Entity(
            id=ent_id,
            name=ent.get('name', ''),
            type=ent.get('type', ''),
            file=ent.get('file', ''),
            start_line=start.get('line', 0),
            start_char=start.get('char', 0),
            end_line=end.get('line', 0),
            end_char=end.get('char', 0),
            comments=comments,
            )
            session.merge(entity)

        # наследования
        for parent in ent.get('inherits', []):
            inh = Inherit(child_id=ent_id, parent_id=parent)
            session.add(inh)

        # методы
        for m in ent.get('relations', {}).get('methods', []):
            method = Method(class_id=ent_id, method_id=m)
            session.add(method)

        # вызовы
        for c in ent.get('relations', {}).get('calls', []):
            call = Call(caller_id=ent_id, callee_id=c)
            session.add(call)

    session.commit()
    session.close()
