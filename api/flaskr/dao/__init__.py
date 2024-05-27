from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from redis import Redis
from pymilvus import connections

db = SQLAlchemy()
def init_db(app : Flask):
    global db
    # app.logger.info('init db {}'.format(app.config['SQLALCHEMY_DATABASE_URI']))
    # db = SQLAlchemy(app)

    db.init_app(app)
    
def init_redis(app:Flask):
    global redis_client
    app.logger.info('init redis {} {} {} {}'
                    .format(app.config['REDIS_HOST'], app.config['REDIS_PORT'], app.config['REDIS_DB'], app.config['REDIS_PASSWORD']))
    if app.config['REDIS_PASSWORD'] != '' and app.config['REDIS_PASSWORD'] != None:
        redis_client = Redis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=app.config['REDIS_DB'],password=app.config['REDIS_PASSWORD'])
    else:
        app.logger.info('init redis with no pwd {} {} {}'.format(app.config['REDIS_HOST'], app.config['REDIS_PORT'], app.config['REDIS_DB']))
        redis_client = Redis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=app.config['REDIS_DB'])
# def init_milvus(app:Flask):
    # global milvus
    # #milvus = connections.connect(
    # #  alias="default",
    # #  user='username',
    # #  password='password',
    # #  host='localhost',
    # #  port='19530'
    # #)
    # milvus = connections.connect(
    #     alias=app.config['MILVUS_ALIAS'],
    #     host=app.config['MILVUS_HOST'],
    #     port=app.config['MILVUS_PORT'],
    #     user=app.config['MILVUS_USER'],
    #     password=app.config['MILVUS_PASSWORD'])
