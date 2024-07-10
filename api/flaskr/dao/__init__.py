from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from redis import Redis
from pymilvus import connections

db = SQLAlchemy()
def init_db(app : Flask):
    global db
    db.init_app(app)
    
def init_redis(app:Flask):
    global redis_client
    app.logger.info('init redis {} {} {} {}'
                    .format(app.config['REDIS_HOST'], app.config['REDIS_PORT'], app.config['REDIS_DB'], app.config['REDIS_PASSWORD']))
    if app.config['REDIS_PASSWORD'] != '' and app.config['REDIS_PASSWORD'] != None:
        redis_client = Redis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=app.config['REDIS_DB'],password=app.config['REDIS_PASSWORD'],username=app.config.get('REDIS_USER',None))
    else:
        app.logger.info('init redis with no pwd {} {} {}'.format(app.config['REDIS_HOST'], app.config['REDIS_PORT'], app.config['REDIS_DB']))
        redis_client = Redis(host=app.config['REDIS_HOST'], port=app.config['REDIS_PORT'], db=app.config['REDIS_DB'])


def run_with_redis(ctx,key,timeout:int,func):
    with ctx:
        global redis_client
        lock = redis_client.lock(key, timeout=timeout, blocking_timeout=timeout)
        if lock.acquire(blocking=False):
            try:
                return func()
            finally:
                lock.release()
        else:
            app.logger.info('run_with_redis lock failed')
            return None