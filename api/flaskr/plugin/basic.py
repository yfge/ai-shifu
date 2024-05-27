
from flask import Flask,g 
import time
from datetime import datetime, timedelta,timezone

def get_current_time(app,user_id,chat_id=None):
    current_time = datetime.now(timezone(timedelta(hours=8)))
    format_time = current_time.strftime("%Y年%m月%d日 %H:%M %d")
    return format_time
def get_current_user(app:Flask,user_id,chat_id=None):
    from ..service.user import get_user_info
    user = get_user_info(app,user_id)
    return "当前用户是:{},手机:{},邮件:{}".format(user.name,user.mobile,user.email)

def enable_basic(functions):
    functions.append({
        "name": "get_current_time",
        "func": get_current_time,
        "msg": "获取当前时间",
        "description": "get current time",
        "parameters": {
            "type": "object",
            "properties": {
            }
        }
    })
    functions.append({
        "name": "get_current_user",
        "func": get_current_user,
        "msg": "获取当前用户",
        "description": "get the info of user chatting with AI",
        "parameters": {
            "type": "object",
            "properties": {
            }
        }
    })