import datetime
from flask import Flask, request, jsonify, make_response
from ..service.common import AppException
import json
import traceback
def register_common_handler(app:Flask)->Flask:
    @app.errorhandler(AppException)
    def handle_invalid_usage(error:AppException):
        response = jsonify({'code': error.code, 'message': error.message})
        response.status_code = 200
        return response
    
    @app.errorhandler(Exception)
    def handle_invalid_exception(error:Exception):
        app.logger.error(traceback.format_exc())
        response = jsonify({'code': -1, 'message':"系统异常"})
        response.status_code = 200
        return response
    return app
    


def fmt(o):
    if isinstance(o, datetime.datetime):
        return o.isoformat()
    else:
        return o.__json__()

def make_common_response(data):
    response = json.dumps({'code':0,'message': 'success','data': data},default=fmt,ensure_ascii=False)
    return response