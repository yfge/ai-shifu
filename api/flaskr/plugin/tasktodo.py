
from flask import Flask,g 
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
from flaskext.markdown import Markdown
import asyncio
from pyppeteer import launch
from ..service.schedule import * 
from ..service.contact import add_contact,get_contact
from ..service.document import create_new_document,append_to_document
from ..service.todo import create_new_todo,get_todos_by_user
from ..api.sendcloud import send_email


def add_todo_item(app,user_id,todo_item,description="",deadline=None,chat_id=None):
    app.logger.info("添加待办事项%s,%s",todo_item,description)
    todo = create_new_todo(app,user_id,todo_item,description,deadline)
    return "添加待办事项成功"


def enable_tasktodo(functions:List):
    functions.append(
         {
            "func": add_todo_item,
            "name": "add_todo_item",
            "msg": "添加待办事项",
            "description": "This function is used to track tasks or activities that need to be completed, irrespective of time. They can be generic tasks that need to be remembered but don't have a specific timing or deadline associated with them. These tasks might include chores, errands, or activities that can be accomplished at any convenient time.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_item":{
                        "type":"string",
                        "description": "The todo item"
                    },
                    "description":{
                        "type":"string",
                        "description": "The description of the todo item"
                    },
                    "deadline":{
                        "type":"string",
                        "description": "The deadline of the todo item"
                    }
                },
                "required": ["todo_item"]
            
            }

        });
