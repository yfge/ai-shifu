
from ...dao import db
from sqlalchemy import Column, String, Integer,DateTime,Boolean, TIMESTAMP, Text, Index, text
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime,timedelta


class ToDoModel(db.Model):
    __tablename__ = 'todo_list'
    id = Column(BIGINT, primary_key=True, comment='Unique ID', autoincrement=True)
    todo_id = Column(String(36), nullable=False, default='', comment='Todo UUID')
    user_id = Column(String(36), nullable=False, default='', comment='User UUID')
    datetime = Column(DateTime, nullable=False, comment='Time of the todo event')
    end_time = Column(DateTime, nullable=False, comment='End time of the todo event')
    location = Column(String(255), nullable=False, default='', comment='Location of the todo event')
    participants = Column(String(255), nullable=False, default='', comment='Participants in the todo event')
    description = Column(Text, nullable=False, comment='Description of the todo event')
    completed = Column(Boolean, nullable=False, default=False, comment='Whether the todo event is completed')
    created = Column(TIMESTAMP, nullable=False, default=func.now(), comment='Creation time')
    updated = Column(TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now(), comment='Update time')
    details = Column(Text, nullable=False, comment='Details of the todo event')
    def __init__(self, todo_id,user_id, datetime, end_time,location, participants, description, completed, details,**kwargs):
        self.todo_id = todo_id
        self.user_id = user_id
        self.datetime = datetime
        self.location = location
        self.end_time = end_time      
        if participants is None or participants == "":
            self.participants = ""
        else:
            self.participants = participants
        if description is None or description == "":
            self.description = ""
        else:
            self.description = description
        self.completed = completed
        if details is None or details == "":
            self.details = ""
        else:
            self.details = details