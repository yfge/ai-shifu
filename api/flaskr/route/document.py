from flask import Flask,request,Response,jsonify
from .common import make_common_response
import json

from ..service.document import *

def register_document_handler(app:Flask,path_prefix:str)->Flask:
    # 得到用户文档列表
    @app.route(path_prefix+'/all', methods=['GET'])
    def get_all_documents():
        user_id = request.user.user_id
        documents = get_documents_by_user(app,user_id)
        return make_common_response(documents)
    # 得到一个文档的详情
    @app.route(path_prefix+'/detail', methods=['GET'])
    def get_detail():
        user_id = request.user.user_id
        document_id = request.args.get('id')
        document = get_document_by_id(app,user_id,document_id)
        return make_common_response(document)
    return app