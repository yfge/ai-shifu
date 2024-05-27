import decimal
from .models import *
from flask import Flask
from ...dao import db
from ..lesson.models import AILesson
from .models import AICourseLessonAttend
from ...util.uuid import generate_id as get_uuid
from ..lesson.const import *


class AICourseLessonAttendDTO:
    def __init__(self, attend_id, lesson_id, course_id, user_id, status,index):
        self.attend_id = attend_id
        self.lesson_id = lesson_id
        self.course_id = course_id
        self.user_id = user_id
        self.status = status
        self.index = index

    def __json__(self):
        return {
            "attend_id": self.attend_id,
            "lesson_id": self.lesson_id,
            "course_id": self.course_id,
            "user_id": self.user_id,
            "status": self.status,
            "index": self.index
        }


def init_buy_record(app: Flask,user_id:str,course_id:str,price:decimal.Decimal):
    with app.app_context():

        origin_record = AICourseBuyRecord.query.filter_by(user_id=user_id,course_id=course_id).first()
        if origin_record:
            return origin_record
        buy_record = AICourseBuyRecord()
        buy_record.user_id = user_id
        buy_record.course_id = course_id
        buy_record.price = price
        buy_record.status = BUY_STATUS_INIT
        buy_record.record_id = str(get_uuid(app))
        db.session.add(buy_record)
        db.session.commit()
        return buy_record


def success_buy_record(app: Flask,record_id:str):
    with app.app_context():
        buy_record = AICourseBuyRecord.query.filter_by(record_id=record_id).first()
        if buy_record:
            buy_record.status = BUY_STATUS_SUCCESS
            lessons = AILesson.query.filter_by(AILesson.course_id==buy_record.course_id,AILesson.lesson_type != LESSON_TYPE_TRIAL,
                                               AILesson.lesson_status==1).all()
            for lesson in lessons:
                attend = AICourseLessonAttend()
                attend.attend_id = str(get_uuid(app))
                attend.course_id = buy_record.course_id
                attend.lesson_id = lesson.lesson_id
                attend.user_id = buy_record.user_id
                attend.status = ATTEND_STATUS_NOT_STARTED
                db.session.add(attend)
            db.session.commit()
            return buy_record
        return None


def init_trial_lesson(app:Flask ,user_id:str,course_id:str)->list[AICourseLessonAttendDTO]:
    app.logger.info('init trial lesson for user:{} course:{}'.format(user_id,course_id))
    response = []
    lessons = AILesson.query.filter(AILesson.course_id==course_id,AILesson.lesson_type == LESSON_TYPE_TRIAL).all()
    app.logger.info('init trial lesson:{}'.format(lessons))

    for lesson in lessons:
       app.logger.info('init trial lesson:{} ,is trail:{}'.format(lesson.lesson_id,lesson.is_final()))
       attend = AICourseLessonAttend.query.filter(AICourseLessonAttend.user_id==user_id,AICourseLessonAttend.lesson_id==lesson.lesson_id).first()
       if attend :
           if lesson.is_final():
               response.append(AICourseLessonAttendDTO(attend.attend_id,attend.lesson_id,attend.course_id,attend.user_id,attend.status,lesson.lesson_index))
           continue
       attend = AICourseLessonAttend()
       attend.attend_id = str(get_uuid(app))
       attend.course_id = course_id
       attend.lesson_id = lesson.lesson_id
       attend.user_id = user_id
       attend.status = ATTEND_STATUS_NOT_STARTED
       db.session.add(attend)
       if  lesson.is_final():
           response.append(AICourseLessonAttendDTO(attend.attend_id,attend.lesson_id,attend.course_id,attend.user_id,attend.status,lesson.lesson_index))
    return response
