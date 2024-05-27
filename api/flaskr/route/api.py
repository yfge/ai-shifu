from flask import Flask,request
import json
from .common import make_common_response
from ..plugin import *
from ..service.common import * 
from ..service.user import get_user_info

def register_api_handler(app:Flask,path_prefix:str)->Flask:
    # 调用一个api
    @app.route(path_prefix+'/invoke', methods=['POST'])
    def invoke():
        user_id = request.args.get('user_id')
        if not user_id:
            user_id = request.cookies.get('user_id')
        if not user_id:
            user_id = request.args.get('user_id')
        if not user_id:
            user_id = request.json.get('user_id')
        if not user_id:
            raise_param_error("user_id is not found")
            
        api_name = request.json.get('name')
        if not api_name:
            raise_param_error("name is not found")
        chat_id = request.json.get('chat_id')

        api_parameters = request.json.get('parameters')
        if not api_parameters:
            api_parameters={}
        available_functions = GetAvaliableFuncs(app,user_id)
        fuction_to_call = available_functions[api_name]["func"]
        if not fuction_to_call:
            raise_param_error("api_name is not found")
        function_args = {} 
        if type(api_parameters) == str:
            function_args = json.loads(api_parameters,strict=False)   
        else:
            function_args = api_parameters 
        # function_args = json.loads(args,strict=False)
        # get_user_info(app,user_id)
        function_response = fuction_to_call(
            app,
            user_id,
            chat_id = chat_id,
            **function_args,
        )
        return make_common_response(function_response)
    return app