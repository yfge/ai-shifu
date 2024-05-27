from flask import Flask,request
import json

from flaskr.service.common.models import raise_param_error
from .common import make_common_response,bypass_token_validation
from ..service.common.dicts import get_all_dicts


def register_dict_handler(app:Flask,path_prefix:str)->Flask:
    @app.route(path_prefix+'/dicts', methods=['GET'])
    @bypass_token_validation
    def get_dicts():
        return make_common_response(get_all_dicts(app)) 
    return app