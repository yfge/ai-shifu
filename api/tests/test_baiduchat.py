import requests
from flask import Flask
from flaskr import create_app
import pytest




@pytest.fixture
def app():
    app = create_app()
    yield app


# from ..dao import redis_client
from flaskr.api.llm.baiduchat import get_access_token
def test_get_access_token(app:Flask):
    access_token = get_access_token()
    app.logger.info(access_token)
    assert get_access_token() != ''
    
from flaskr.api.llm.baiduchat import get_chat_response
def test_chat(app):
    get_chat_response(app,"你好")