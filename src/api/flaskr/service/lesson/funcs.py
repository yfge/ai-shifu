from flaskr.common.swagger import register_schema_to_swagger
from flaskr.service.common.models import raise_error
from .models import AICourse, AILesson, AILessonScript
from .const import (
    ASK_MODE_DEFAULT,
    CONTENT_TYPE_TEXT,
    CONTENT_TYPES,
    LESSON_TYPE_NORMAL,
    SCRIPT_TYPE_FIX,
    SCRIPT_TYPES,
    UI_TYPE_EMPTY,
    UI_TYPE_SELECTION,
    UI_TYPES,
)
from flask import Flask
from ...dao import db
from flaskr.api.doc.feishu import list_records
from flaskr.util.uuid import generate_id
from sqlalchemy import func, text
import json
from flaskr.service.shifu.models import PublishedShifu, DraftShifu
from typing import Union
from flaskr.service.shifu.utils import get_shifu_res_url


@register_schema_to_swagger
class AICourseDTO:
    """
    AICourseDTO
    """

    def __init__(
        self,
        course_id,
        course_name,
        course_desc,
        course_price,
        course_feishu_id,
        status,
        course_teacher_avatar,
        course_keywords,
    ):
        self.course_id = course_id
        self.course_name = course_name
        self.course_desc = course_desc
        self.course_price = course_price
        self.course_feishu_id = course_feishu_id
        self.status = status
        self.course_teacher_avatar = course_teacher_avatar
        self.course_keywords = course_keywords

    def __json__(self):
        return {
            "course_id": self.course_id,
            "course_name": self.course_name,
            "course_desc": self.course_desc,
            "course_price": str(self.course_price),
            "course_feishu_id": self.course_feishu_id,
            "status": self.status,
            "course_teacher_avatar": self.course_teacher_avatar,
            "course_keywords": self.course_keywords,
        }


@register_schema_to_swagger
class AILessonDTO:
    """
    AILessonDTO
    """

    def __init__(
        self,
        lesson_id,
        course_id,
        lesson_name,
        lesson_desc,
        lesson_no,
        lesson_index,
        lesson_feishu_id,
        lesson_status,
        status,
    ):
        self.lesson_id = lesson_id
        self.course_id = course_id
        self.lesson_name = lesson_name
        self.lesson_desc = lesson_desc
        self.lesson_no = lesson_no
        self.lesson_index = lesson_index
        self.lesson_feishu_id = lesson_feishu_id
        self.lesson_status = lesson_status
        self.status = status


@register_schema_to_swagger
class AILessonInfoDTO:
    """
    AILessonInfoDTO
    """

    def __init__(
        self,
        lesson_no: str,
        lesson_name: str,
        lesson_id: str,
        feishu_id: str,
        lesson_type,
    ) -> None:
        self.lesson_no = lesson_no
        self.lesson_name = lesson_name
        self.lesson_id = lesson_id
        self.feishu_id = feishu_id
        self.lesson_type = lesson_type

    def __json__(self):
        return {
            "lesson_no": self.lesson_no,
            "lesson_name": self.lesson_name,
            "lesson_id": self.lesson_id,
            "feishu_id": self.feishu_id,
            "lesson_type": self.lesson_type,
        }


@register_schema_to_swagger
class AICourseDetailDTO:
    """
    AICourseDetailDTO
    """

    def __init__(
        self,
        course_id: str,
        course_name: str,
        course_desc: str,
        course_price: str,
        course_status: str,
        course_feishu_id: str,
        status: int,
        lesson_list: list[AILessonInfoDTO],
    ):
        self.course_id = course_id
        self.course_name = course_name
        self.course_desc = course_desc
        self.course_price = course_price
        self.course_status = course_status
        self.course_feishu_id = course_feishu_id
        self.status = status
        self.lesson_list = lesson_list

    def __json__(self):
        return {
            "course_id": self.course_id,
            "course_name": self.course_name,
            "course_desc": self.course_desc,
            "course_price": str(self.course_price),
            "course_status": self.course_status,
            "course_feishu_id": self.course_feishu_id,
            "status": self.status,
            "lesson_list": [lesson.__json__() for lesson in self.lesson_list],
        }


@register_schema_to_swagger
class AILessonDetailDTO:
    """
    AILessonDetailDTO
    """

    def __init__(
        self,
        lesson_id: str,
        lesson_name: str,
        lesson_desc: str,
        lesson_no: str,
        lesson_index: int,
        lesson_feishu_id: str,
        lesson_status: int,
        status: int,
        lesson_type: int,
        lesson_summary: str,
        lesson_language: str,
        lesson_name_multi_language: str,
        ask_count_limit: int,
        ask_model: str,
        ask_prompt: int,
        pre_lesson_no: str,
        created_user_id: str,
        updated_user_id: str,
        created: str,
        updated: str,
    ):
        self.lesson_id = lesson_id
        self.lesson_name = lesson_name
        self.lesson_desc = lesson_desc
        self.lesson_no = lesson_no
        self.lesson_index = lesson_index
        self.lesson_feishu_id = lesson_feishu_id
        self.lesson_status = lesson_status
        self.status = status
        self.lesson_type = lesson_type
        self.lesson_summary = lesson_summary
        self.lesson_language = lesson_language
        self.lesson_name_multi_language = lesson_name_multi_language
        self.ask_count_limit = ask_count_limit
        self.ask_model = ask_model
        self.ask_prompt = ask_prompt
        self.pre_lesson_no = pre_lesson_no
        self.created_user_id = created_user_id
        self.updated_user_id = updated_user_id
        self.created = created
        self.updated = updated

    def __json__(self):
        return {
            "lesson_id": self.lesson_id,
            "lesson_name": self.lesson_name,
            "lesson_desc": self.lesson_desc,
            "lesson_no": self.lesson_no,
            "lesson_index": self.lesson_index,
            "lesson_feishu_id": self.lesson_feishu_id,
            "lesson_status": self.lesson_status,
            "status": self.status,
            "lesson_type": self.lesson_type,
            "lesson_summary": self.lesson_summary,
            "lesson_language": self.lesson_language,
            "lesson_name_multi_language": self.lesson_name_multi_language,
            "ask_count_limit": self.ask_count_limit,
            "ask_model": self.ask_model,
            "ask_prompt": self.ask_prompt,
            "pre_lesson_no": self.pre_lesson_no,
            "created_user_id": self.created_user_id,
            "updated_user_id": self.updated_user_id,
            "created": self.created,
            "updated": self.updated,
        }


class AIScriptDTO:
    """
    AIScriptDTO
    """

    def __init__(
        self,
        script_id,
        lesson_id,
        script_name,
        script_desc,
        script_index,
        script_feishu_id,
        script_version,
        script_no,
        script_type,
        script_content_type,
        script_prompt,
        script_model,
        script_profile,
        script_media_url,
        script_ui_type,
        script_ui_content,
        script_check_prompt,
        script_check_flag,
        script_ui_profile,
        script_end_action,
        script_other_conf,
        status,
    ):
        self.script_id = script_id
        self.lesson_id = lesson_id
        self.script_name = script_name
        self.script_desc = script_desc
        self.script_index = script_index
        self.script_feishu_id = script_feishu_id
        self.script_version = script_version
        self.script_no = script_no
        self.script_type = script_type
        self.script_content_type = script_content_type
        self.script_prompt = script_prompt
        self.script_model = script_model
        self.script_profile = script_profile
        self.script_media_url = script_media_url
        self.script_ui_type = script_ui_type
        self.script_ui_content = script_ui_content
        self.script_check_prompt = script_check_prompt
        self.script_check_flag = script_check_flag
        self.script_ui_profile = script_ui_profile
        self.script_end_action = script_end_action
        self.script_other_conf = script_other_conf
        self.status = status


DB_SAVE_MAP = {
    "剧本简述": "script_name",
    "剧本类型": "script_type",
    "内容格式": "script_content_type",
    "模版内容": "script_prompt",
    "模版变量": "script_profile",
    "检查模版内容": "script_check_prompt",
    "输入成功标识": "script_check_flag",
    "自定义模型": "script_model",
    "解析用户输入内容": "script_ui_profile",
    "媒体URL": "script_media_url",
    "输入框提示": "script_ui_content",
    "按钮组配置": "script_other_conf",
    "后续交互": "script_ui_type",
    "按钮标题": "script_ui_content",
    "跳转配置": "script_other_conf",
    "temperature": "script_temperature",
    "ask_count_history": "ask_with_history",
    "ask_count_limit": "ask_count_limit",
    "ask_model": "ask_model",
}


DB_SAVE_DICT_MAP = {
    "剧本类型": SCRIPT_TYPES,
    "内容格式": CONTENT_TYPES,
    "后续交互": UI_TYPES,
}


def update_lesson_info(
    app: Flask,
    doc_id: str,
    table_id: str,
    view_id: str,
    title: str = "vewlGkI2Jp",
    index: int = None,
    lesson_type: int = LESSON_TYPE_NORMAL,
    app_id: str = None,
    app_secret: str = None,
    course_id: str = None,
    file_name: str = None,
):
    """
    update lesson info
    deprecated, use shifu outline funcs instead
    only used in db migration
    Args:
        app: Flask application instance
        doc_id: Doc ID
        table_id: Table ID
        view_id: View ID
        title: Title
        index: Index
        lesson_type: Lesson type
        app_id: App ID
        app_secret: App secret
        course_id: Course ID
        file_name: File name
    Returns:
        None
    """
    with app.app_context():
        # 检查课程
        # 用飞书的AppId做为课程的唯一标识「
        course = None
        if course_id is not None:
            course = AICourse.query.filter(AICourse.course_id == course_id).first()
        else:
            course = AICourse.query.filter_by(course_feishu_id=doc_id).first()
        if course is None:
            if course_id is None:
                course_id = str(generate_id(app))
            course = AICourse()
            course.course_id = course_id
            course.course_feishu_id = doc_id
            course.status = 1
            course.course_name = "Demo Lesson"
            course.course_desc = "Demo Lesson"
            db.session.add(course)
        course_id = course.course_id
        page_token = None
        lesson = None
        unconf_fields = []

        lessonNo = str(index).zfill(2)
        db.session.execute(
            text(
                "update ai_lesson set status=0 where course_id=:course_id and lesson_no like :lesson_no"
            ),
            {"course_id": course_id, "lesson_no": lessonNo + "%"},
        )
        parent_lesson = AILesson.query.filter(
            AILesson.course_id == course_id,
            AILesson.lesson_no == str(index).zfill(2),
            AILesson.course_id == course_id,
            #    ,AILesson.lesson_feishu_id==table_id,
            func.char_length(AILesson.lesson_no) == 2,
        ).first()
        if parent_lesson is None:
            parent_lesson = AILesson()
            parent_lesson.lesson_id = str(generate_id(app))
            parent_lesson.course_id = course.course_id
            parent_lesson.lesson_name = title
            parent_lesson.lesson_desc = ""
            parent_lesson.status = 1
            parent_lesson.lesson_no = lessonNo
            parent_lesson.lesson_feishu_id = table_id
            parent_lesson.lesson_type = lesson_type
            parent_lesson.parent_id = ""
            if int(index) > 1:
                parent_lesson.pre_lesson_no = str(int(index) - 1).zfill(2)
            else:
                parent_lesson.pre_lesson_no = ""
            db.session.add(parent_lesson)
        else:
            parent_lesson.lesson_name = title
            parent_lesson.lesson_desc = ""
            parent_lesson.status = 1
            parent_lesson.lesson_no = lessonNo
            parent_lesson.status = 1
            parent_lesson.lesson_feishu_id = table_id
            parent_lesson.lesson_type = lesson_type
            parent_lesson.parent_id = ""
            if int(index) > 1:
                parent_lesson.pre_lesson_no = str(int(index) - 1).zfill(2)
            else:
                parent_lesson.pre_lesson_no = ""
        subIndex = 0
        childLessons = [AILesson]
        script_index = 0
        kwargs = {}
        if app_id is not None:
            kwargs["app_id"] = app_id
        if app_secret is not None:
            kwargs["app_secret"] = app_secret
        while True:
            if file_name:
                with open(file_name, "r", encoding="UTF-8") as json_file:
                    json_data = json_file.read()
                    resp = json.loads(json_data)
            else:
                resp = list_records(
                    app,
                    doc_id,
                    table_id,
                    view_id=view_id,
                    page_token=page_token,
                    page_size=100,
                    **kwargs,
                )
                # with open(lessonNo+".json", "w") as f:
                #     json.dump(resp,f, ensure_ascii=False)

            records = resp["data"]["items"]
            app.logger.info("records:" + str(len(records)))
            for record in records:
                if record["fields"].get("小节", None):
                    title = "".join(t["text"] for t in record["fields"]["小节"]).strip()
                    if title is None:
                        app.logger.info("title is None")
                    if title is None or title == "" and lesson is not None:
                        pass
                    else:
                        lesson = next(
                            (
                                tl
                                for tl in childLessons
                                if hasattr(tl, "lesson_name")
                                and tl.lesson_name == title
                            ),
                            None,
                        )
                else:
                    lesson = parent_lesson
                if lesson is None:
                    # 新来的一个小节
                    script_index = 0
                    subIndex = subIndex + 1
                    lesson = AILesson.query.filter(
                        AILesson.course_id == course_id,
                        AILesson.lesson_feishu_id == table_id,
                        AILesson.lesson_name == title,
                    ).first()
                    if lesson is None:
                        lesson = AILesson()
                        lesson.lesson_id = str(generate_id(app))
                        lesson.course_id = course.course_id
                        lesson.lesson_name = title
                        lesson.lesson_desc = ""
                        lesson.status = 1
                        lesson.lesson_feishu_id = table_id
                        lesson.lesson_no = lessonNo + str(subIndex).zfill(2)
                        lesson.lesson_type = lesson_type
                        lesson.parent_id = parent_lesson.lesson_id
                        lesson.lesson_index = subIndex
                        if subIndex > 1:
                            lesson.pre_lesson_no = lessonNo + str(subIndex - 1).zfill(2)
                        else:
                            lesson.pre_lesson_no = ""
                        db.session.add(lesson)
                    else:
                        lesson.lesson_name = title
                        lesson.lesson_desc = ""
                        lesson.status = 1
                        lesson.lesson_feishu_id = table_id
                        lesson.lesson_type = lesson_type
                        lesson.parent_id = parent_lesson.lesson_id
                        lesson.lesson_no = lessonNo + str(subIndex).zfill(2)
                        lesson.lesson_index = subIndex
                        if subIndex > 1:
                            lesson.pre_lesson_no = lessonNo + str(subIndex - 1).zfill(2)
                        else:
                            lesson.pre_lesson_no = ""
                    db.session.execute(
                        text(
                            "update ai_lesson_script set status=0 where lesson_id=:lesson_id"
                        ),
                        {"lesson_id": lesson.lesson_id},
                    )
                    childLessons.append(lesson)
                script_index = script_index + 1
                record_id = record["record_id"]
                scripDb = {}
                scripDb["script_feishu_id"] = str(record_id)
                scripDb["lesson_id"] = lesson.lesson_id
                scripDb["script_desc"] = ""
                scripDb["script_prompt"] = ""
                scripDb["script_ui_profile"] = ""
                scripDb["script_end_action"] = ""
                scripDb["script_other_conf"] = ""
                scripDb["script_profile"] = ""
                scripDb["script_media_url"] = ""
                scripDb["script_ui_content"] = ""
                scripDb["script_check_prompt"] = ""
                scripDb["script_check_flag"] = ""
                scripDb["script_index"] = script_index
                scripDb["script_ui_type"] = UI_TYPE_EMPTY
                scripDb["script_type"] = SCRIPT_TYPE_FIX
                scripDb["script_content_type"] = CONTENT_TYPE_TEXT
                scripDb["script_model"] = ""
                scripDb["status"] = 1
                scripDb["script_temperature"] = 0.4
                scripDb["ask_count_limit"] = 5
                scripDb["ask_mode"] = ASK_MODE_DEFAULT
                scripDb["ask_prompt"] = ""
                scripDb["ask_with_history"] = 5
                scripDb["ask_model"] = ""
                scripDb["script_ui_profile_id"] = ""
                for field in record["fields"]:
                    val_obj = record["fields"][field]
                    db_field = DB_SAVE_MAP.get(field.strip())
                    val = ""
                    if isinstance(val_obj, str):
                        val = val_obj
                    elif isinstance(val_obj, list):
                        val = "".join(
                            t["text"] if isinstance(t, dict) else "[" + t + "]"
                            for t in val_obj
                        )
                    elif isinstance(val_obj, dict):
                        val = val_obj.get("text")
                    else:
                        app.logger.info("val_obj:" + str(val_obj))
                        val = str(val_obj)
                    if db_field:
                        if field in DB_SAVE_DICT_MAP:
                            orig_val = val
                            val = DB_SAVE_DICT_MAP[field.strip()].get(orig_val.strip())
                            if val is None:
                                app.logger.info(
                                    "val is None:" + field + ",value:" + orig_val
                                )
                        if val is not None and val != "":
                            scripDb[db_field] = val
                    else:
                        if unconf_fields.count(field) == 0:
                            unconf_fields.append(field)
                    continue
                scrip = AILessonScript.query.filter(
                    AILessonScript.script_feishu_id == record_id,
                    AILessonScript.lesson_id == lesson.lesson_id,
                ).first()
                if scripDb["script_ui_type"] == UI_TYPE_SELECTION:
                    data = scripDb["script_ui_content"]
                    app.logger.info("data:" + str(data))

                if scrip is None:
                    scripDb["script_id"] = str(generate_id(app))
                    db.session.add(AILessonScript(**scripDb))
                else:
                    for key in scripDb:
                        setattr(scrip, key, scripDb[key])

            if resp["data"]["has_more"]:
                page_token = resp["data"]["page_token"]
            else:
                break
        app.logger.info("unconf_fields:" + str(unconf_fields))
        db.session.commit()
        return


def get_course_info(
    app: Flask, course_id: str, preview_mode: bool = False
) -> AICourseDTO:
    with app.app_context():
        shifu_info: Union[DraftShifu, PublishedShifu] = None
        if preview_mode:
            shifu_info = (
                DraftShifu.query.filter(DraftShifu.shifu_bid == course_id)
                .order_by(DraftShifu.id.desc())
                .first()
            )
        else:
            shifu_info = (
                PublishedShifu.query.filter(PublishedShifu.shifu_bid == course_id)
                .order_by(PublishedShifu.id.desc())
                .first()
            )
        if shifu_info is None:
            raise_error("server.shifu.courseNotFound")
        return AICourseDTO(
            shifu_info.shifu_bid,
            shifu_info.title,
            shifu_info.description,
            shifu_info.price,
            shifu_info.shifu_bid,  # Or a default value if it can be None
            shifu_info.deleted,  # Or a default value if it can be None
            get_shifu_res_url(shifu_info.avatar_res_bid),
            shifu_info.keywords.split(",") if shifu_info.keywords else [],
        )
