
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


def get_contact_info(app: Flask, user_id, user="owner",chat_id=None):
    app.logger.info("查询联系人信息:{}".format(user))
    from ..service.contact import get_contact
    user_Info = get_contact(app, user_id, user)
    if user_Info is None:
        return "没有联系人信息"
    return "联系人信息:{},手机:{},邮件:{},喜好：{}".format(user_Info.name, user_Info.mobile, user_Info.email, "打篮球,看电影，听音乐")


def add_contact_info(app: Flask, user_id, name, phone=None, email=None,chat_id=None):
    add_contact(app, user_id, name, phone, email)
    return "添加联系人成功"


def enable_contact(functions: List):
    functions.append({
        "name": "add_contact_info",
        "description": "add info of user's contract,including phone number,email,",
        "func": add_contact_info,
        "msg": "添加联系人信息",
        "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The contact user"
                    },
                    "phone": {
                        "type": "string",
                        "description": "The phone number"
                    },
                    "email": {
                        "type": "string",
                        "description": "The email",
                    },
                }
        },
        "required": ["name", "phone", "email"]
    })
    functions.append({
        "name": "get_contact_info",
        "func": get_contact_info,
        "msg": "查询联系人信息",
        "description": "get contact info,including phone number,email. if you want to get the contact info of the current user,calling the function get_current_user. ",
        "parameters": {
                "type": "object",
                "properties": {
                    "user": {
                        "type": "string",
                        "description": "The contact user "
                    }
                }
        }
    })
