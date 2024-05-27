from .models import Document
from flask import Flask
import uuid
from ...dao import db



class DocumentSummary:
    def __init__(self,  title: str,document_id:str):
        self.title = title
        self.document_id = document_id
    def __json__(self):
        return {
            'title': self.title,
            'document_id':self.document_id
        }

class DocumentDetail:
    def __init__(self, id: int, title: str, content: str, created: str, updated: str):
        self.id = id
        self.title = title
        self.content = content
        self.created = created
        self.updated = updated
    def __json__(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'created': self.created,
            'updated': self.updated
        }



def create_new_document(app:Flask, user_id: str, title: str, content: str):
    with app.app_context():
        document_id = str(uuid.uuid4())
        new_document = Document(document_id=document_id, user_id=user_id, title=title, content=content)
        db.session.add(new_document)
        db.session.commit()
        return True
def append_to_document(app: Flask, user_id, title: str, content: str):
    # append content to the document
    with app.app_context():
        document = Document.query.filter(Document.user_id == user_id, Document.title == title).first()
        if document is None:
            return False
        document.content += content
        db.session.commit()
        return True


def get_document_by_id(app: Flask, user_id: str, document_id: str):
    with app.app_context():
        app.logger.info('user_id: %s, document_id: %s', user_id, document_id)
        document = Document.query.filter(Document.user_id == user_id, Document.document_id == document_id).first()
        if document is None:
            return None
        return DocumentDetail(document.id, document.title, document.content, document.created, document.updated)


def get_documents_by_user(app: Flask, user_id: str):
    with app.app_context():
        documents = Document.query.filter(Document.user_id == user_id).all()
        return [DocumentSummary(document.title,document.document_id) for document in documents]

    