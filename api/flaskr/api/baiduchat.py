import requests
# from ..dao import redis_client
from flask import Flask 
import json

APP_ID = "39320262"
APP_KEY = "TQWXOHq4WwrGEX8W7h69hjRs"
SECRECT_KEY = "dnsP9oxdG51U3Gxq3dmDQyMTKY0KDwti"


def get_access_token():
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": APP_KEY,
        "client_secret": SECRECT_KEY
    }
    response = requests.post(url, params=params)
    return response.json()["access_token"]


def test_get_access_token():
    print(get_access_token())
    assert get_access_token() != ''

def get_token():
    return get_access_token()
def get_chat_response(app,msg):
    url = "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/eb-instant"
    params = {
        "access_token": get_access_token()
    }
    data = {"messages":[{
        "role": "user",
        "content": msg
    }],"stream":False}
    response = requests.post(url, params=params, json = data)
    app.logger.info(response.json())
