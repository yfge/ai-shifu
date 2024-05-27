from flask import Flask, request, Response, jsonify
from .common import make_common_response
import json


from ..service.contact import *


def register_contact_handler(app: Flask, path_prefix: str) -> Flask:

    # 得到所有联系人
    @app.route(path_prefix+'/all', methods=['GET'])
    def get_all():
        user_id = request.user.user_id
        name = request.args.get('name', '')
        mobile = request.args.get('mobile', '')
        email = request.args.get('email', '')
        contacts = get_all_contacts(app, user_id, name, mobile, email)

        return make_common_response(contacts)
        # json.dumps(contacts,default=lambda o: o.__json__(),ensure_ascii=False)

    # 根据id 更新联系人信息
    @app.route(path_prefix+'/update', methods=['POST'])
    def update():
        print('-------------------------------update-------------------------')
        user_id = request.user.user_id
        contact_id = request.get_json().get("contact_id")
        name = request.get_json().get("name")
        mobile = request.get_json().get("mobile")
        email = request.get_json().get("email")

        print(contact_id, name, mobile, email)
        update_contact(app, contact_id, name, mobile, email)
        return make_common_response("ok")

    @app.route(path_prefix+'/delete', methods=['POST'])
    def delete():
        print('-------------------------------delete-------------------------')
        user_id = request.user.user_id
        contact_ids = request.get_json().get("contactIds")
        print(contact_ids)
        delete_contact(app, contact_ids)
        return make_common_response("ok")
    return app
