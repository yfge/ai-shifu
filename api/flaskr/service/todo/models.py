
from ...dao import db
from sqlalchemy import Column, String, Integer,DateTime,Boolean, TIMESTAMP, Text, Index, text
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base


class Todo(db.Model):
    __tablename__ = 'todo'

    id = Column(BIGINT, primary_key=True, comment='Unique ID', autoincrement=True)
    todo_id = Column(String(36), nullable=False, default='', comment='Todo UUID')
    user_id = Column(String(36), nullable=False, default='', comment='User UUID')
    title = Column(String(255), nullable=False, default='', comment='Todo title')
    description = Column(Text, nullable=False, comment='Todo description')
    is_done = Column(Integer, nullable=False, default=0, comment='Status of the todo, 0 for not done, 1 for done')
    created = Column(TIMESTAMP, nullable=False, default=func.now(), comment='Creation time')
    updated = Column(TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now(), comment='Update time')
    deadline = Column(DateTime, nullable=True, default=func.now(), comment='Deadline of the todo')
    completed_at = Column(DateTime, nullable=True, default=func.now(), comment='Completion time')
    def __init__(self, todo_id, user_id, title, description, deadline=None, completed_at=None):
        self.todo_id = todo_id
        self.user_id = user_id
        self.title = title
        self.description = description
        self.deadline = deadline
        self.completed_at = completed_at
