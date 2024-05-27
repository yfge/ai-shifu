from flask import Flask
from ...dao import db
import uuid
import datetime
from .models import Todo


class TodoDTO:
    def __init__(self, todo_id: str, title: str, description: str, is_done: bool, created: str, updated: str, deadline: str):
        self.todo_id = todo_id
        self.title = title
        self.description = description
        self.is_done = is_done
        self.created = created
        self.updated = updated
        self.deadline = deadline

    def __json__(self):
        return {
            'todo_id': self.todo_id,
            'title': self.title,
            'description': self.description,
            "deadline": self.deadline,
            'is_done': self.is_done,
            'deadline': self.deadline,
        }


def create_new_todo(app: Flask, user_id: str, title: str, description: str, deadline: str) -> TodoDTO:
    with app.app_context():
        id = str(uuid.uuid4()).replace('-', '')
        new_todo = Todo(todo_id=id, user_id=user_id, title=title,
                        description=description, deadline=deadline)
        db.session.add(new_todo)
        db.session.commit()
        return TodoDTO(new_todo.todo_id, new_todo.title, new_todo.description, new_todo.is_done, new_todo.created, new_todo.updated, new_todo.deadline)


def get_todos_by_user(app: Flask, user_id: str, title: str, is_done: str, start_date: str, end_date: str) -> list:
    start_datetime = start_date if start_date+' 00:00:00' else ''
    end_datetime = end_date if end_date+' 23:59:59' else ''

    with app.app_context():
        if start_datetime == '' and end_datetime == '':
            todos = db.session.query(Todo).filter_by(user_id=user_id, is_done=is_done).filter(
                Todo.title.like(
                    '%'+title+'%'
                )).all()
        else:
            todos = db.session.query(Todo).filter_by(user_id=user_id, is_done=is_done).filter(
                Todo.title.like(
                    '%'+title+'%'
                ), Todo.deadline >= start_datetime, Todo.deadline <= end_datetime).all()
        return [TodoDTO(todo.todo_id, todo.title, todo.description, todo.is_done, todo.created, todo.updated, todo.deadline) for todo in todos]


def mark_todo_as_done(app: Flask, todo_id: str):
    with app.app_context():
        app.logger.info('mark_todo_as_done ' + todo_id)
        todo = db.session.query(Todo).filter_by(todo_id=todo_id).first()
        if todo:
            todo.is_done = 1
            todo.completed_at = datetime.datetime.now()
            db.session.commit()


def update_todo_by_id(app: Flask, todo_id: str, title: str, description: str, deadline: str):
    with app.app_context():
        todo = db.session.query(Todo).filter_by(todo_id=todo_id).first()
        if todo:
            todo.title = title
            todo.description = description
            todo.deadline = deadline
            db.session.commit()


def delete_todo_by_id(app: Flask, todo_id: str):
    with app.app_context():
        todo = db.session.query(Todo).filter_by(todo_id=todo_id).first()
        if todo:
            db.session.delete(todo)
            db.session.commit()
