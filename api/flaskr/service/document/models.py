
from ...dao import db
from sqlalchemy import Column, String, Integer,DateTime,Boolean, TIMESTAMP, Text, Index, text
from sqlalchemy.dialects.mysql import BIGINT
from sqlalchemy.sql import func
from sqlalchemy.ext.declarative import declarative_base

class Document(db.Model):
    __tablename__ = 'document'

    id = Column(BIGINT, primary_key=True, comment='Unique ID', autoincrement=True)
    document_id = Column(String(36), nullable=False, default='', comment='Document UUID')
    user_id = Column(String(36), nullable=False, default='', comment='User UUID')
    title = Column(String(255), nullable=False, default='', comment='Document title')
    content = Column(Text, nullable=False, comment='Document content in Markdown')
    created = Column(TIMESTAMP, nullable=False, default=func.now(), comment='Creation time')
    updated = Column(TIMESTAMP, nullable=False, default=func.now(), onupdate=func.now(), comment='Update time')

    def __init__(self, document_id, user_id, title, content):
        self.document_id = document_id
        self.user_id = user_id
        self.title = title
        self.content = content

