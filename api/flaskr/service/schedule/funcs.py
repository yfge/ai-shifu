from ast import List
from operator import and_, or_
from .model import ToDoModel
from flask import Flask
from ...dao import db
import uuid
from datetime import datetime, timedelta
from sqlalchemy import func
from sqlalchemy import text

class TodoList:
    def __init__(self, todo):
        self.todo_id = todo.todo_id
        self.datetime = str(todo.datetime)
        self.end_time = str(todo.end_time)
        self.location = todo.location
        self.participants = todo.participants
        self.description = todo.description
        self.completed = todo.completed
        self.details = todo.details


    def __json__(self):
        return {
            'id': self.todo_id,
            'start': self.datetime,
            'end': self.end_time,
            'title': self.description,
        }


class TodoDetail:
    def __init__(self, todo):
        self.todo_id = todo.todo_id
        self.datetime = str(todo.datetime)
        self.end_time = str(todo.end_time)
        self.location = todo.location
        self.participants = todo.participants
        self.description = todo.description
        self.completed = todo.completed
        self.details = todo.details

    def __json__(self):
        return {
            'id': self.todo_id,
            'start': self.datetime,
            'end': self.end_time,
            'location': self.location,
            'participants': self.participants,
            'description': self.description,
            'details': self.details
        }


def get_schedule_by_user(app: Flask, user_id: str, date_str: str = None, end_str=None):
    with app.app_context():

        filter = ToDoModel.query.filter(ToDoModel.user_id == user_id)
        if date_str:
            start = datetime.strptime(date_str, '%Y-%m-%d').date()
            filter = filter.filter(ToDoModel.datetime >= start)
        else:
            start = datetime.now().date()
            filter = filter.filter(ToDoModel.datetime >= start)
        if end_str:
            end = datetime.strptime(end_str, '%Y-%m-%d').date()
            filter = filter.filter(ToDoModel.datetime <= end)
        else:
            end = start + timedelta(days=1)
            filter = filter.filter(ToDoModel.datetime < end)
            # end是start的后一天
        todos = filter.all()
        return [TodoList(todo) for todo in todos]


class AddScheduleResult:
    def __init__(self, success, todos: List):
        self.success = success
        self.todos = todos

    def __json__(self):
        return {
            'success': self.success,
            'todos': self.todos
        }


def add_schedule(app: Flask, user_id: str, description: str, start_time: str, end_time: str = "", location: str = "", participants: str = "", details: str = ""):
    if end_time is None or end_time == "":
        # 增加一小时
        datetime_val = datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S')
        datetime_val = datetime_val + timedelta(hours=1)
        # 格式化
        end_time = datetime_val.strftime('%Y-%m-%d %H:%M:%S')
    with app.app_context():
        todo_id = str(uuid.uuid4()).replace('-', '')
        sql = text("""select * from todo_list
                    where user_id = :user_id 
                        and (
                                (datetime < :start_time and end_time > :start_time) 
                                or (datetime < :end_time and end_time > :end_time) 
                                or (datetime >= :start_time and end_time <= :end_time)
                                or (datetime <= :start_time and end_time >= :end_time)
                            )""")


        reseult = db.session.execute(sql, {"user_id": user_id, "start_time": start_time, "end_time": end_time}).fetchall()

        if len(reseult) > 0:
            return AddScheduleResult(False, [TodoList(ToDoModel(**dict(row._mapping))) for row in reseult])

        new_todo = ToDoModel(
            todo_id=todo_id,
            user_id=user_id,
            datetime=start_time,
            location=location,
            participants=participants,
            description=description,
            end_time=end_time,
            details=details,
            completed=False
        )
        db.session.add(new_todo)
        db.session.commit()
        return AddScheduleResult(True, [TodoList(new_todo)])


def delete_schedule(app: Flask, user_id, idsStr):
    ids = []#idsStr.split(',')
    print(ids)
    if isinstance(idsStr, list):
        ids = idsStr
    else:
        ids = idsStr.split(',')

    with app.app_context():
        for id in ids:
            todo = ToDoModel.query.filter(
                ToDoModel.user_id == user_id, ToDoModel.todo_id == id).first()
            if todo is None:
                continue
            db.session.delete(todo)
        db.session.commit()
        return True


def update_schedule(app: Flask, user_id: str, shedule_id, description: str = "", datetime: str = "", end_time: str = "", location: str = "", participants: str = "", details: str = ""):
    with app.app_context():
        schedule = ToDoModel.query.filter(
            ToDoModel.user_id == user_id, ToDoModel.todo_id == shedule_id).first()
        if schedule is None:
            app.logger.info("is null")
            return False
        if description and description != "" and description != schedule.description:
            schedule.description = description
        if datetime and datetime != "" and datetime != schedule.datetime:
            schedule.datetime = datetime
        if end_time and end_time != "" and end_time != schedule.end_time:
            schedule.end_time = end_time
        if location and location != "" and location != schedule.location:
            schedule.location = location
        if participants and participants != "" and participants != schedule.participants:
            schedule.participants = participants
        if details and details != "" and details != schedule.details:
            schedule.details = details
        db.session.commit()
        return TodoDetail(schedule)


def get_schedule(app: Flask, user_id: str, schedule_id: str):
    with app.app_context():
        schedule = ToDoModel.query.filter(
            ToDoModel.user_id == user_id, ToDoModel.todo_id == schedule_id).first()
        if schedule is None:
            return None
        return TodoDetail(schedule)
