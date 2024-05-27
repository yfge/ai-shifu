

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

def send_message_to_mail(app:Flask,user_id, receiver,mail,title="",message="",chat_id=None):
    app.logger.info("发送{},mail:{},邮件:{},内容:{}".format(receiver,mail,title,message))
    from ..service.user import get_user_info
    user = get_user_info(app,user_id)
    html = Markdown(app).convert(message)
    resp = send_email(app,user.name,user.email,mail,title,html)
    app.logger.info("发送邮件{}".format(resp))
    return resp


def enable_email(functions:List):
    functions.append(
        {
            "name": "send_mail",
            "func": send_message_to_mail,
            "msg": "发送邮件",
            "description": "向联系人发送邮件，不要伪造信息，确认邮件地址为用户提供或是从联系人数据中取得。",
            "parameters": {
                "type": "object",
                "properties": {
                    "receiver":{
                        "type":"string",
                        "description": "the name of the receiver,if not sure of the name of the receiver,calling the function get_contact_info to get the name of the receiver,or you can call the function get_current_user to get the name of the receiver."
                        
                    },
                    "mail":{
                        "type":"string",
                        "description": "The mail address of the receiver,be sure that the mail address is correct ,you can call the function get_contact_info to get the mail address of the receiver or you can call the function get_current_user to get the mail address of the receiver"
                    },
                    "title":{
                        "type":"string",
                        "description": "The title of the message"
                    },
                    "message":{
                        "type":"string",
                        "description": "The message ,written in markdown format,should be accurate and appropriate,and writen by current user"
                    }
                },
                "required":["receiver","mail","title","message"]
            }
        })