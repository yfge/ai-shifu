
from flask import Flask, g
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from flaskext.markdown import Markdown
import asyncio
from pyppeteer import launch
from ..service.schedule import *
from ..service.contact import add_contact, get_contact
from ..service.document import create_new_document, append_to_document
from ..service.todo import create_new_todo, get_todos_by_user
from ..api.sendcloud import send_email





def get_the_todos_of_date(app,user_id,date,chat_id=None):
    todoList = get_schedule_by_user(app,user_id,date)
    if todoList is None or len(todoList) == 0:
        return "没有待办事项"
    else:
        return json.dumps(todoList,default=lambda o:o.__dict__,ensure_ascii=False)

def add_schedule_item(app, user_id, time, todo_item, end_time=None, details=None, location=None, participants=None,chat_id=None):
    app.logger.info("添加待办事项%s,%s", time, todo_item)
    todo = add_schedule(app, user_id=user_id, description=todo_item, start_time=time,
                        end_time=end_time, details=details, location=location, participants=participants)
    return json.dumps(todo, default=lambda o: o.__dict__, ensure_ascii=False)

def delete_schedule_item(app, user_id, ids,chat_id=None):
    app.logger.info("删除待办事项%s", ids)
    delete_schedule(app, user_id, ids)
    return "删除待办事项成功"

def update_schedule_item(app, user_id, id, time=None, todo_item=None, end_time=None, details=None, location=None, participants=None,chat_id=None):
    app.logger.info("更新待办事项%s,%s", id, todo_item)
    todo = update_schedule(app,user_id=user_id,shedule_id=id,description=todo_item,datetime=time,
                            end_time=end_time,details=details,location=location,participants=participants) 
    return json.dumps(todo, default=lambda o: o.__dict__, ensure_ascii=False)

def enable_schedule(functions):
    functions.append(
        {
            "name": "add_schedule_item",
            "func": add_schedule_item,
            "msg": "添加待办事项",
            "description": """This function is designed for activities, or events that have a specific date and time associated with them. 
            This is particularly useful for time-bound tasks such as appointments, meetings, or any other events that need to occur at a certain time.
            When using this function, it's important to be aware of the current time to avoid scheduling conflicts. 
            For ease of use, the get_current_time function can be invoked to fetch the current time.
            return with the new schedule item if success else return with the conflict schedule item""",
            "parameters": {
                "type": "object",
                "properties": {
                    "time": {
                        "type": "string",
                        "description": "The time,format is yyyy-mm-dd hh:mm:ss,if not sure of  current time,calling the function get_current_time to get the current time"
                    },
                    "todo_item": {
                        "type": "string",
                        "description": "The schedule item"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "The end time of the schedule item,format is yyyy-mm-dd hh:mm:ss"
                    },
                    "details": {
                        "type": "string",
                        "description": "The details of the schedule item"
                    },
                    "location": {
                        "type": "string",
                        "description": "The location of the schedule item"
                    },
                    "participants": {
                        "type": "string",
                        "description": "The participants of the schedule item"
                    }
                },
                "required": ["time", "todo_item"]
            }
        })
    functions.append(
          {
            "name": "delete_schedule_item",
            "description": "delete the schedule item",
            "func": delete_schedule_item,
            "msg": "删除待办事项",
            "parameters": {
                "type": "object",
                "properties": {
                    "ids":{
                        "type":"string",
                        "description": "The ids of the schedule item to be deleted,should be sure that the ids is correct,calling the function get_the_todos_of_date to get the ids of the schedule item,format is ['id1','id2','id3']"
                    }
                },
                "required": ["ids"]
            }
        })
    functions.append(
           {
            "name": "get_schedule_of_date",
            "func": get_the_todos_of_date,
            "msg": "获取某一天的待办事项",
            "description": "get the schedule of the date",
            "parameters": {
                "type": "object",
                "properties": {
                    "date":{
                        "type":"string",
                        "description": "The date,format is yyyy-mm-dd,if not sure of  current date,calling the function get_current_time to get the current date"
                    }
                }
            }
        })
    functions.append(
        {
            "name": "update_schedule",
            "func": update_schedule_item,
            "msg": "更新待办事项",
            "description": "update the schedule item",
            "parameters": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "The id of the schedule item to be update,should be sure that the ids is correct,calling the function get_the_todos_of_date"

                    },
                    "time": {
                        "type": "string",
                        "description": "The time,format is yyyy-mm-dd hh:mm:ss,if not sure of  current time,calling the function get_current_time to get the current time"
                    },
                    "todo_item": {
                        "type": "string",
                        "description": "The schedule item"
                    },
                    "end_time": {
                        "type": "string",
                        "description": "The end time of the schedule item,format is yyyy-mm-dd hh:mm:ss"
                    },
                    "details": {
                        "type": "string",
                        "description": "The details of the schedule item"
                    },
                    "location": {
                        "type": "string",
                        "description": "The location of the schedule item"
                    },
                    "participants": {
                        "type": "string",
                        "description": "The participants of the schedule item"
                    }
                },
                "required": ["id"]
            }
        })
    
