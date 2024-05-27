from ..service.todo import *
from functools import wraps
from .common import make_common_response
from flask import Flask, request


def register_todo_handler(app: Flask, path_prefix: str) -> Flask:
    @app.route(path_prefix+'/create', methods=['POST'])
    def create_todo():
        user_id = request.user.user_id
        title = request.get_json().get('title', '')
        description = request.get_json().get('description', '')
        create_new_todo(app, user_id, title, description)
        return make_common_response('ok')

    @app.route(path_prefix+'/all', methods=['GET'])
    def list_all_todo():
        user_id = request.user.user_id
        title = request.args.get('title', '')
        is_done = request.args.get('is_done', '')
        start_date = request.args.get('start_date', '')
        end_date = request.args.get('end_date', '')
        todos = get_todos_by_user(
            app, user_id, title, is_done, start_date, end_date)
        return make_common_response(todos)

    @app.route(path_prefix+'/done', methods=['POST'])
    def mark_todo_done():
        todo_id = request.get_json().get('todo_id', '')
        print('------------------------------------------------------mark_todo_done-----------------------------------')
        print(todo_id)
        mark_todo_as_done(app, todo_id)
        return make_common_response('ok')

    @app.route(path_prefix+'/update', methods=['POST'])
    def update_todo():

        todo_id = request.get_json().get('todo_id', '')
        print(todo_id)
        title = request.get_json().get('title', '')
        description = request.get_json().get('description', '')
        deadline = request.get_json().get('deadline', '')
        update_todo_by_id(app, todo_id, title, description, deadline)
        return make_common_response('ok')

    @app.route(path_prefix+'/delete', methods=['POST'])
    def delete_todo():
        todo_id = request.get_json().get('todo_id', '')
        delete_todo_by_id(app, todo_id)
        return make_common_response('ok')

    # @app.route(path_prefix+'/create', methods=['POST'])
    # def create_todo():
    #     title = request.get_json().get('title', '')
    #     description = request.get_json().get('description', '')
    #     deadline = request.get_json().get('deadline', '')
    #     create_todo(app, title, description, deadline)
    #     return make_common_response('ok')

    return app
