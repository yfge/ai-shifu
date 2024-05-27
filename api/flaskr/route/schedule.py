from flask import Flask, request, Response, jsonify
from .common import make_common_response
import json

from ..service.schedule import *


def register_schedule_handler(app: Flask, path_prefix: str) -> Flask:
    # 得到用户日程列表
    @app.route(path_prefix+'/all', methods=['GET'])
    def get_all_schedules():
        user_id = request.user.user_id
        date_str = request.args.get('start')
        end_str = request.args.get('end')
        schedules = get_schedule_by_user(app, user_id, date_str, end_str)
        return make_common_response(schedules)
    # 添加一个日程

    @app.route(path_prefix+'/add', methods=['POST'])
    def add_schedule():
        user_id = request.user.user_id
        description = request.get_json().get('description', '')
        datetime = request.get_json().get('datetime', '')
        location = request.get_json().get('location', '')
        participants = request.get_json().get('participants', '')
        schedule = add_schedule(app, user_id, description,
                                datetime, location, participants)
        return make_common_response(schedule)

    # 查询日程详情
    @app.route(path_prefix+'/detail', methods=['GET'])
    def get_schedule_detail():
        user_id = request.user.user_id
        schedule_id = request.args.get('schedule_id')
        app.logger.info("schedule_id is {}".format(schedule_id))
        schedule = get_schedule(app, user_id, schedule_id)
        return make_common_response(schedule)
    # 更新日程

    @app.route(path_prefix+'/update', methods=['POST'])
    def update_schedule_byid():
        user_id = request.user.user_id
        schedule_id = request.get_json().get('schedule_id', '')
        description = request.get_json().get('description', '')
        datetime = request.get_json().get('starttime', '')
        endtime = request.get_json().get('endtime', '')
        location = request.get_json().get('location', '')
        participants = request.get_json().get('participants', '')
        details = request.get_json().get('details', '')
        schedule = update_schedule(
            app, user_id, schedule_id, description, datetime, endtime, location, participants, details)
        return make_common_response(schedule)

    @app.route(path_prefix+'/delete', methods=['POST'])
    def delete_schedule_byid():
        user_id = request.user.user_id
        schedule_id = request.get_json().get('schedule_id', '')
        schedule = delete_schedule(app, user_id, schedule_id)
        return make_common_response(schedule)
    return app
