import json
import os
import time
import logging
from flask import Flask, Response, g,request,send_from_directory,make_response
from flask_cors import CORS
from . import api 
from . import dao

from pyppdf import patch_pyppeteer
import pymysql
pymysql.install_as_MySQLdb()
from .common import *





def create_app(test_config=None):

    # 在程序开始时调用 patch_pyppeteer()
    patch_pyppeteer.patch_pyppeteer()
    app = Flask(__name__, instance_relative_config=True)

  
    
    CORS(app, resources={r"/*": {"supports_credentials": True}})
    app.logger.info('config: {}'.format(test_config))
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'flaskr.sqlite'),
    )

    app.logger.info('create_app is called')
    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        app.logger.info('test_config is not None, load the '+test_config+'_config.py')
        # load the test config if passed in
        app.config.from_pyfile(test_config+'_config.py', silent=True)
    init_log(app)
    api.init_langfuse(app)
    dao.init_db(app)
    dao.init_redis(app)
    # dao.init_milvus(app)
  
    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass
    from . import route

    prefix = app.config['PATH_PREFIX']
    # chat with the bot using sse
    app = route.register_common_handler(app)
    app = route.register_user_handler(app,prefix+'/user')
    app = route.register_chat_route(app,prefix+'/chat')
    app = route.register_resource_route(app,prefix+'/resource')
    app = route.register_contact_handler(app,prefix+'/contact')
    app = route.register_document_handler(app,prefix+'/document')
    app = route.register_schedule_handler(app,prefix+'/schedule')
    app = route.register_todo_handler(app,prefix+'/todo')
    app = route.register_api_handler(app,prefix+'/api')
    app = route.register_lesson_handler(app,prefix+'/lesson')
    app = route.register_study_handler(app,prefix+'/study')
    return app