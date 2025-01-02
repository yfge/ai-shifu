import time

from flask import Flask

from flaskr.service.study.models import AICourseLessonAttendScript
from flaskr.api.llm import invoke_llm
from flaskr.api.check import (
    check_text,
    CHECK_RESULT_PASS,
    CHECK_RESULT_REJECT,
)
from flaskr.service.study.utils import generation_attend, get_model_setting
from flaskr.service.check_risk import add_risk_control_result
from flaskr.service.lesson.models import AILessonScript, AILesson
from flaskr.service.order.models import AICourseLessonAttend
from flaskr.service.study.const import (
    ROLE_TEACHER,
)
from flaskr.dao import db
from flaskr.service.study.utils import make_script_dto


class BreakException(Exception):
    pass


def check_text_with_llm_response(
    app: Flask,
    user_id: str,
    log_script: AICourseLessonAttendScript,
    input: str,
    span,
    lesson: AILesson,
    script_info: AILessonScript,
    attend: AICourseLessonAttend,
):
    res = check_text(app, log_script.log_id, input, user_id)
    span.event(name="check_text", input=input, output=res)
    add_risk_control_result(
        app,
        log_script.log_id,
        user_id,
        input,
        res.provider,
        res.check_result,
        str(res.raw_data),
        1 if res.check_result == CHECK_RESULT_PASS else 0,
        "check_text",
    )
    if res.check_result == CHECK_RESULT_REJECT:
        labels = res.risk_labels
        model_setting = get_model_setting(app, script_info)
        prompt = "你是一名在线老师,要回答学生的相应提问，目前学生的问题有一些不合规不合法的地方，请找一个合适的理由拒绝学生，当前的教学内容为:{},学生的问题为：{},拒绝的理由为：{}".format(
            script_info.script_prompt, input, ", ".join(labels)
        )
        res = invoke_llm(
            app,
            span,
            message=prompt,
            model=model_setting.model_name,
            json=False,
            stream=True,
            generation_name="check_text_reject_"
            + lesson.lesson_no
            + "_"
            + str(script_info.script_index)
            + "_"
            + script_info.script_name,
            **model_setting.model_args,
        )
        response_text = ""
        for i in res:
            yield make_script_dto("text", i.result, script_info.script_id)
            response_text += i.result
            time.sleep(0.01)
        log_script = generation_attend(app, attend, script_info)
        log_script.script_content = response_text
        log_script.script_role = ROLE_TEACHER
        db.session.add(log_script)
        db.session.flush()
        yield make_script_dto("text_end", "", script_info.script_id)
    else:
        app.logger.info(f"check_text_by_{res.provider} is None")
        return
