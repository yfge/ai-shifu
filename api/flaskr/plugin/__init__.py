import json
from flask import Flask
from .basic import enable_basic
from .contact import enable_contact
from .document import enable_document
from .schedule import enable_schedule
from .tasktodo import enable_tasktodo
from .email import enable_email
from .image import enable_image
from .vector import enable_search


def get_allfuctions(app:Flask, user_id):
    ret = []
    enable_basic(ret)
    enable_contact(ret)
    enable_document(ret)
    enable_schedule(ret)
    enable_tasktodo(ret)
    enable_email(ret)
    enable_image(ret)
    enable_search(ret)
    return ret

def GetFuncs(app:Flask, user_id):
    ret =  [{"type":"function","function":{"name":item["name"],"description":item["description"],"parameters":json.dumps(item["parameters"])}}  for item in get_allfuctions(app, user_id)]
    app.logger.info("get funcs")
    app.logger.info(ret)
    return ret
def GetAvaliableFuncs(app:Flask, user_id):
     return {item["name"]:{"func":item["func"],"msg":item["msg"]}  for item in get_allfuctions(app, user_id)}

