import json
from trace import Trace
from flask import Flask
from flaskr.service.profile.funcs import save_user_profiles
from flaskr.service.lesson.models import AILessonScript, AILesson
from flaskr.service.order.models import AICourseLessonAttend
from flaskr.service.study.const import INPUT_TYPE_SELECT, ROLE_STUDENT
from flaskr.service.study.plugin import register_input_handler
from flaskr.service.study.utils import generation_attend, get_profile_array
from flaskr.dao import db


@register_input_handler(input_type=INPUT_TYPE_SELECT)
def handle_input_select(
    app: Flask,
    user_id: str,
    lesson: AILesson,
    attend: AICourseLessonAttend,
    script_info: AILessonScript,
    input: str,
    trace: Trace,
    trace_args,
):
    profile_keys = get_profile_array(script_info.script_ui_profile)
    profile_tosave = {}
    if len(profile_keys) == 0:
        btns = json.loads(script_info.script_other_conf)
        conf_key = btns.get("var_name", "input")
        profile_tosave[conf_key] = input
    for k in profile_keys:
        profile_tosave[k] = input
    save_user_profiles(app, user_id, profile_tosave)
    log_script = generation_attend(app, attend, script_info)
    log_script.script_content = input
    log_script.script_role = ROLE_STUDENT
    db.session.add(log_script)
    span = trace.span(name="user_select", input=input)
    span.end()
    db.session.flush()
