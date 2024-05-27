
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



# 将内容保存为markdown格式的文件,输入有标题，内容，文件名
def save_as_markdown(app:Flask,user_id,title,content,chat_id=None):
    # app.logger.info("保存为markdown格式的文件,标题:{},内容:{},文件名:{}".format(title,content,file_name))
    create_new_document(app,user_id,title,content)
    return "保存成功,文件标题为:{},可以在文档功能中找到".format(title)


# 将内容续写到markdown格式的文件中，输入有标题，内容，文件名

def append_to_markdown(app:Flask,user_id,title,content,chat_id=None):
    append_to_document(app,user_id,title,content)
    return "保存成功,文件标题为:{},可以在文档功能中找到".format(title)

def enable_document(functions:List):
    functions.append(
           {
            "name": "save_as_markdown",
            "func": save_as_markdown,
            "msg": "保存为markdown格式的文件",
            "description": "save the content as markdown（如果用户要求你输出一些文档，材料性的内容，你应该直接调用这个函数）",
            "parameters": {
                "type": "object",
                "properties": {
                    "content":{
                        "type":"string",
                        "description": "The content"
                    },
                    "title":{
                        "type":"string",
                        "description": "The title of the markdown"
                    }
                },
                "required": ["content","title"]
            },
        })
    functions.append(
        {
            "name": "append_to_markdown",
            "description": "append the content to the markdown",
            "func": append_to_markdown,
            "msg": "将内容续写到markdown格式的文件中",
            "parameters": {
                "type": "object",
                "properties": {
                    "content":{
                        "type":"string",
                        "description": "The content"
                    },
                    "title":{
                        "type":"string",
                        "description": "The file name"
                    }
                },
                "required": ["content","title"]
            }
        })