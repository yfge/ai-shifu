import json
from flask import Flask, request, jsonify, make_response

from flaskr.service.common.models import raise_param_error
from ..service.user import *
from functools import wraps
from .common import make_common_response,bypass_token_validation,by_pass_login_func


def register_user_handler(app:Flask,path_prefix:str)->Flask:


    @app.route(path_prefix+'/register', methods=['POST'])
    @bypass_token_validation
    def register():
        """
        注册用户
        ---
        tags:
          - 用户
        parameters:
          - in: body
            name: body
            required: true
            schema:
              id: UserInfo 
              required:
                - username
                - password
                - email
                - name
                - mobile
        definitions:
            UserInfo:
                type: object
                properties:
                    user_id:
                        type: string
                        description: 用户ID
                    username:
                        type: string
                        description: 用户名
                    email:
                        type: string
                        description: 邮箱
                    name:
                        type: string
                        description: 姓名
                    mobile:
                        type: string
                        description: 手机号
        """
        app.logger.info("register")
        username = request.get_json().get('username', '')
        password = request.get_json().get('password', '')
        email = request.get_json().get('email', '')
        name = request.get_json().get('name', '')
        mobile = request.get_json().get('mobile', '')
        user_token = create_new_user(app,username,name,password,email,mobile)
        resp = make_response(make_common_response(user_token.userInfo))
        # resp.headers.add('Set-Cookie', 'token={};Path=/'.format(user_token.token))
        # resp.set_cookie('token', user_token.token,path="")
        return resp 
    
    @app.route(path_prefix+'/login', methods=['POST'])
    @bypass_token_validation
    def login():
        """
        用户登录
        ---
        tags:
            -   用户
        parameters:
            -   in: body
                name: body
                required: true
                schema:
                id: login
                required:
                    - username
                    - password
                properties:
                    username:
                    type: string
                    description: 用户名
                    password:
                    type: string
                    description: 密码
        """
        app.logger.info("login")
        username = request.get_json().get('username', '')
        password = request.get_json().get('password', '')
        user_token = verify_user(app,username,password)
        resp = make_response(make_common_response(user_token))
        # resp.headers.add('Set-Cookie', 'token={};Path=/'.format(user_token.token))
        return resp
    
    @app.before_request
    def before_request():
       
        if request.endpoint is None:
            return
        if request.endpoint in ['login', 'register','require_reset_code','reset_password','invoke','update_lesson'] or request.endpoint in by_pass_login_func:
            # 在登录和注册处理函数中绕过登录态验证
            return
            # 检查装饰器标记，跳过Token校验
        
        # 在这里执行登录态验证逻辑
        token = request.cookies.get('token',None)
        if not token:
            token = request.args.get('token',None)
        if not token:
            token = request.headers.get('Token',None)
            # app.logger.info('headers token:'+str(token))
        token = str(token)
        if not token and request.endpoint in by_pass_login_func:
            return
        user = validate_user(app,token)
        request.user = user
    

    @app.route(path_prefix+'/info', methods=['GET'])
    def info():
        return make_common_response(request.user)

    @app.route(path_prefix+'/update_info', methods=['POST'])
    def update_info():
        email = request.get_json().get('email', None)
        name = request.get_json().get('name', '')
        mobile = request.get_json().get('mobile', None)
        return make_common_response(update_user_info(app,request.user,name,email,mobile))
    @app.route(path_prefix+'/update_password', methods=['POST'])
    def update_password():
        old_password = request.get_json().get('old_password', None)
        new_password = request.get_json().get('new_password', None)
        return make_common_response(change_user_passwd(app,request.user,old_password,new_password))
    
    @app.route(path_prefix+'/require_reset_code', methods=['POST'])
    def require_reset_code():
        username = request.get_json().get('username', None)
        return make_common_response(require_reset_pwd_code(app,username))
    @app.route(path_prefix+'/reset_password', methods=['POST'])
    def reset_password():
        username = request.get_json().get('username', None)
        code = request.get_json().get('code', None)
        new_password = request.get_json().get('new_password', None)
        return make_common_response(reset_pwd(app,username,code,new_password))
    
    @app.route(path_prefix+'/require_tmp',methods=['POST'])
    @bypass_token_validation
    def require_tmp():
        tmp_id = request.get_json().get('temp_id',None)
        source = request.get_json().get('source','web')
        if not tmp_id:
            raise_param_error('temp_id')
        user_token = generate_temp_user(app,tmp_id,source)
        resp = make_response(make_common_response(user_token))
        # resp.headers.add('Set-Cookie', 'token={};Path=/'.format(user_token.token))
        return resp

    @app.route(path_prefix+'/generate_chk_code',methods=['POST'])
    @bypass_token_validation
    def generate_chk_code():
        mobile = request.get_json().get('mobile',None)
        if not mobile:
            raise_param_error('mobile')
        return make_common_response(generation_img_chk(app,mobile))
    
    @app.route(path_prefix+'/send_sms_code',methods=['POST'])
    @bypass_token_validation
    def send_sms_code_api():
        mobile = request.get_json().get('mobile',None)
        check_code = request.get_json().get('check_code',None)  
        if not mobile:
            raise_param_error('mobile')
        if not check_code:
            raise_param_error('check_code')
        return make_common_response(send_sms_code(app,mobile,check_code))
    
    @app.route(path_prefix+'/verify_sms_code',methods=['POST'])
    @bypass_token_validation
    def verify_sms_code_api():
        mobile = request.get_json().get('mobile',None)
        sms_code = request.get_json().get('sms_code',None)
        user_id =  None if  getattr(request,'user',None) is None else  request.user.user_id
        if not mobile:
            raise_param_error('mobile')
        if not sms_code:
            raise_param_error('sms_code')
        return make_common_response(verify_sms_code(app,user_id,mobile,sms_code))

    return app


    

