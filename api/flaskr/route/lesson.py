from flask import Flask,request
import json

from flaskr.service.common.models import raise_param_error
from flaskr.service.lesson.const import LESSON_TYPE_NORMAL
from .common import bypass_token_validation, make_common_response
from ..service.lesson import update_lesson_info,get_lessons

from ..api.feishu import get_document_info,list_records

def register_lesson_handler(app:Flask,path_prefix:str)->Flask:

    @app.route(path_prefix+'/update_lesson', methods=['GET'])
    @bypass_token_validation
    def update_lesson():
        doc_id = request.args.get('doc_id')
        table_id = request.args.get('table_id')
        title = request.args.get('title')
        index = request.args.get('index')
        view_id = request.args.get('view_id')
        lesson_type = request.args.get('lesson_type',LESSON_TYPE_NORMAL)
        if not doc_id:
            raise_param_error("doc_id is not found")
        if not table_id:
            raise_param_error("table_id is not found")
        if not title:
            raise_param_error("title is not found")
        if not index:
            raise_param_error("index is not found")
        
        return make_common_response(update_lesson_info(app,doc_id,table_id,view_id,title,index,lesson_type))
    @app.route(path_prefix+'/get_lesson_tree', methods=['GET'])
    def get_lesson_tree():
        course_id = request.args.get('course_id')
        if not course_id:
            raise_param_error("doc_id is not found")
        return make_common_response(get_lessons(app,None,course_id))
    
    return app