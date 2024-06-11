import random
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from ...dao import db,redis_client as redis
from ...api.sendcloud import send_email
import uuid
from .models import User, UserConversion
import hashlib
from ..common import USER_NOT_FOUND,USER_PASSWORD_ERROR,USER_ALREADY_EXISTS,USER_TOKEN_EXPIRED,USER_NOT_LOGIN,OLD_PASSWORD_ERROR,RESET_PWD_CODE_EXPIRED,RESET_PWD_CODE_ERROR
import jwt
import time

class UserInfo:
    def __init__(self, user_id, username, name, email, mobile,model):
        self.user_id = user_id
        self.username = username
        self.name = name
        self.email = email
        self.mobile = mobile
        self.model = model
    def __json__(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "name": self.name,
            "email": self.email,
            "mobile": self.mobile,
        }
    def __html__(self):
        return self.__json__()

class UserToken:
    def __init__(self,userInfo:UserInfo, token):
        self.userInfo = userInfo
        self.token = token
    def __json__(self):
        return {
            "userInfo": self.userInfo,
            "token": self.token,
        }



def create_new_user(app:Flask, username: str, name: str, raw_password: str, email: str, mobile: str)->UserToken:
    with app.app_context():
        user = User.query.filter((User.username == username) | (User.email == email) | (User.mobile == mobile)).first()
        if user:
            raise USER_ALREADY_EXISTS
        user_id = str(uuid.uuid4()).replace('-', '')
        password_hash = hashlib.md5((user_id + raw_password).encode()).hexdigest()
        new_user = User(user_id=user_id, username=username, name=name, password_hash=password_hash, email=email, mobile=mobile,default_model=app.config["OPENAI_DEFAULT_MODEL"])
        db.session.add(new_user)
        db.session.commit()
        token = generate_token(app,user_id=user_id)
        return UserToken(UserInfo(user_id=user_id, username=username, name=name, email=email, mobile=mobile,model=new_user.default_model),token=token)

def generate_temp_user(app:Flask,temp_id:str,user_source = 'web')->UserToken:
    with app.app_context():
        convert_user = UserConversion.query.filter(UserConversion.conversion_id==temp_id,UserConversion.conversion_source == user_source).first()
        if not convert_user:
            user_id = str(uuid.uuid4()).replace('-', '')
            new_convert_user = UserConversion(user_id=user_id,conversion_uuid=temp_id, conversion_id=temp_id, conversion_source=user_source, conversion_status=0)
            new_user = User(user_id=user_id)
            db.session.add(new_convert_user)
            db.session.add(new_user)
            db.session.commit()

            token = generate_token(app,user_id=user_id)
            return UserToken(UserInfo(user_id=user_id, username="", name="", email="", mobile="",model=new_user.default_model),token=token)
        else:
            user = User.query.filter_by(user_id=convert_user.user_id).first()
            token = generate_token(app,user_id=user.user_id)
            return UserToken(UserInfo(user_id=user.user_id, username=user.username, name=user.name, email=user.email, mobile=user.mobile,model=user.default_model),token=token)     



def generate_token(app:Flask, user_id: str) -> str:
    with app.app_context():
        token = jwt.encode({'user_id': user_id,"time_stamp": time.time()}, app.config['SECRET_KEY'], algorithm='HS256')
        redis.set(app.config["REDIS_KEY_PRRFIX_USER"] + user_id, token,ex=app.config['TOKEN_EXPIRE_TIME'])
        return token

def verify_user(app:Flask, login: str, raw_password: str) ->UserToken:
    with app.app_context():
        user = User.query.filter((User.username == login) | (User.email == login) | (User.mobile == login)).first()
        if user:
            password_hash = hashlib.md5((user.user_id + raw_password).encode()).hexdigest()
            if password_hash == user.password_hash:
                token = generate_token(app,user_id=user.user_id)  
                return UserToken(UserInfo(user_id=user.user_id, username=user.username, name=user.name, email=user.email, mobile=user.mobile,model=user.default_model),token=token)
            else:
                raise USER_PASSWORD_ERROR
        else:
            raise USER_NOT_FOUND
def validate_user(app:Flask, token: str) -> UserInfo:
    with app.app_context():
        if(token == None):
            raise USER_NOT_LOGIN
        try:
            user_id = jwt.decode(token, app.config['SECRET_KEY'], algorithms=['HS256'])['user_id']
            redis_token = redis.get(app.config["REDIS_KEY_PRRFIX_USER"] + user_id);
            if(redis_token == None):
                raise USER_TOKEN_EXPIRED 
            set_token = str(redis.get(app.config["REDIS_KEY_PRRFIX_USER"] + user_id),encoding="utf-8")
            if set_token == token:
                user = User.query.filter_by(user_id=user_id).first()
                if user:
                    return UserInfo(user_id=user.user_id, username=user.username, name=user.name, email=user.email, mobile=user.mobile,model=user.default_model)
                else:
                    raise USER_TOKEN_EXPIRED
            else:
                raise USER_TOKEN_EXPIRED 
        except (jwt.exceptions.ExpiredSignatureError):
            raise USER_TOKEN_EXPIRED
        except (jwt.exceptions.DecodeError):
            raise USER_NOT_FOUND

def update_user_info(app:Flask,user:UserInfo,name,email=None,mobile=None)->UserInfo:
    with app.app_context():
        if user:
            dbuser = User.query.filter_by(user_id=user.user_id).first()
            dbuser.name = name
            if(email != None):
                dbuser.email = email
            if(mobile != None):
                dbuser.mobile = mobile
            db.session.commit()
            return UserInfo(user_id=user.user_id, username=user.username, name=user.name, email=user.email, mobile=user.mobile,model=dbuser.default_model)
        else:
            raise USER_NOT_FOUND

def change_user_passwd(app:Flask,user:UserInfo,oldpwd,newpwd)->UserInfo:
    with app.app_context():
        if user:
            user = User.query.filter_by(user_id=user.user_id).first()
            password_hash = hashlib.md5((user.user_id + oldpwd).encode()).hexdigest()
            if password_hash == user.password_hash:
                user.password_hash = hashlib.md5((user.user_id + newpwd).encode()).hexdigest()
                db.session.commit()
                return UserInfo(user_id=user.user_id, username=user.username, name=user.name, email=user.email, mobile=user.mobile,model=user.default_model)
            else:
                raise OLD_PASSWORD_ERROR
        else:
            raise USER_NOT_FOUND
def get_user_info(app:Flask,user_id:str)->UserInfo:
    with app.app_context():
        user = User.query.filter_by(user_id=user_id).first()
        if user:
            return UserInfo(user_id=user.user_id, username=user.username, name=user.name, email=user.email, mobile=user.mobile,model=user.default_model)
        else:
            raise USER_NOT_FOUND


def require_reset_pwd_code(app:Flask,login:str):
    with app.app_context():
        user = User.query.filter((User.username == login) | (User.email == login) | (User.mobile == login)).first()
        if user:
            code = random.randint(0,9999) 
            redis.set(app.config["REDIS_KEY_PRRFIX_RESET_PWD"] + user.user_id, code,ex=app.config['RESET_PWD_CODE_EXPIRE_TIME'])
            send_email(app,'小卡AI助理',user.email,user.email,"重置密码","您的重置密码验证码为："+str(code))
            return True
        else:
            raise USER_NOT_FOUND
        
def reset_pwd(app:Flask,login:str,code:int,newpwd:str):

    with app.app_context():
        user = User.query.filter((User.username == login) | (User.email == login) | (User.mobile == login)).first()
        if user:
            redis_code = redis.get(app.config["REDIS_KEY_PRRFIX_RESET_PWD"] + user.user_id);
            if(redis_code == None):
                raise RESET_PWD_CODE_EXPIRED 
            set_code = int(str(redis_code,encoding="utf-8"))
            app.logger.info("code:"+str(code)+" set_code:"+str(set_code))
            if str(set_code) == str(code):
                app.logger.info("code:"+str(code)+" set_code:"+str(set_code))
                user.password_hash = hashlib.md5((user.user_id + newpwd).encode()).hexdigest()
                db.session.commit()
                app.logger.info("update password")
                return True
            else:
                raise RESET_PWD_CODE_ERROR 
        else:
            raise USER_NOT_FOUND 