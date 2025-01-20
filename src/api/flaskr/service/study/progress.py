from flask import Flask
from .models import AICourseStudyProgress, AILessonStudyProgress
from ...service.lesson.models import AICourse, AILesson, AILessonScript
from ...service.lesson.const import LESSON_TYPE_BRANCH_HIDDEN, LESSON_TYPE_TRIAL
from ...dao import db
from ...util.uuid import generate_id


class LessonInfo:
    lesson_id: str
    lesson_no: str
    lesson_type: str
    lesson_name: str
    script_count: int
    sublessons: list["LessonInfo"]

    def __init__(
        self,
        lesson_id: str,
        lesson_no: str,
        lesson_type: str,
        lesson_name: str,
        script_count: int,
        sublessons: list["LessonInfo"],
    ):
        self.lesson_id = lesson_id
        self.lesson_no = lesson_no
        self.lesson_type = lesson_type
        self.lesson_name = lesson_name
        self.script_count = script_count
        self.sublessons = sublessons

    def __str__(self):
        return f"""LessonInfo(lesson_id={self.lesson_id},
        lesson_no={self.lesson_no},
        lesson_type={self.lesson_type},
        lesson_name={self.lesson_name},
        script_count={self.script_count},
        sublessons={self.sublessons})"""

    def __repr__(self):
        return f"""LessonInfo(lesson_id={self.lesson_id},
        lesson_no={self.lesson_no},
        lesson_type={self.lesson_type},
        lesson_name={self.lesson_name},
        script_count={self.script_count},
        sublessons={self.sublessons})"""

    def __json__(self):
        return {
            "lesson_id": self.lesson_id,
            "lesson_no": self.lesson_no,
            "lesson_type": self.lesson_type,
            "lesson_name": self.lesson_name,
            "script_count": self.script_count,
            "sublessons": [i.__json__() for i in self.sublessons],
        }


# @lru_cache(maxsize=1000)
def get_course_info(course_id: str):
    lessons = AILesson.query.filter(
        AILesson.course_id == course_id,
        AILesson.lesson_type != LESSON_TYPE_BRANCH_HIDDEN,
        AILesson.status == 1,
    ).all()
    lesson_ids = [i.lesson_id for i in lessons]
    lesson_scripts = (
        AILessonScript.query.with_entities(
            AILessonScript.lesson_id, AILessonScript.script_id
        )
        .filter(
            AILessonScript.lesson_id.in_(lesson_ids),
            AILessonScript.status == 1,
        )
        .all()
    )
    lesson_script_map = {i.lesson_id: len(i) for i in lesson_scripts}
    lessons = sorted(lessons, key=lambda x: x.lesson_no)
    ret = []
    for lesson in lessons:
        if len(lesson.lesson_no) == 2:
            ret.append(
                LessonInfo(
                    lesson_id=lesson.lesson_id,
                    lesson_no=lesson.lesson_no,
                    lesson_type=lesson.lesson_type,
                    lesson_name=lesson.lesson_name,
                    script_count=lesson_script_map.get(lesson.lesson_id, 0),
                    sublessons=[],
                )
            )
        else:
            lesson_info = [i for i in ret if lesson.lesson_no.startswith(i.lesson_no)]
            if len(lesson_info) == 0:
                print(f"parent lesson not found: {lesson.lesson_no}")
                continue
            lesson_info[0].sublessons.append(
                LessonInfo(
                    lesson_id=lesson.lesson_id,
                    lesson_no=lesson.lesson_no,
                    lesson_type=lesson.lesson_type,
                    lesson_name=lesson.lesson_name,
                    script_count=lesson_script_map.get(lesson.lesson_id, 0),
                    sublessons=[],
                )
            )

    for i in ret:
        for j in i.sublessons:
            j.script_count = lesson_script_map.get(j.lesson_id, 0)
        i.script_count = sum([j.script_count for j in i.sublessons])

    return ret


def init_study_progress(app: Flask, user_id: str, course_id: str):
    with app.app_context():
        progress = AICourseStudyProgress.query.filter_by(
            user_id=user_id, course_id=course_id
        ).first()
        if not progress:
            lessons = get_course_info(course_id)
            progress_id = generate_id(app)
            progress = AICourseStudyProgress(
                progress_id=progress_id,
                user_id=user_id,
                course_id=course_id,
                chapter_count=len(lessons),
                chapter_completed_count=0,
                chapter_reset_count=0,
                is_paid=0,
                is_completed=0,
            )
            db.session.add(progress)
            for lesson in [ls for ls in lessons if ls.lesson_type == LESSON_TYPE_TRIAL]:
                lesson_progress = AILessonStudyProgress(
                    progress_id=progress_id,
                    lesson_id=lesson.lesson_id,
                    sublesson_count=len(lesson.sublessons),
                    sublesson_completed_count=0,
                    script_index=0,
                    script_count=lesson.script_count,
                )
                for sublesson in lesson.sublessons:
                    sublesson_progress = AILessonStudyProgress(
                        progress_id=progress_id,
                        lesson_id=sublesson.lesson_id,
                        sublesson_count=len(sublesson.sublessons),
                        sublesson_completed_count=0,
                        script_index=0,
                        script_count=sublesson.script_count,
                    )
                    db.session.add(sublesson_progress)
                db.session.add(lesson_progress)
            db.session.commit()


def init_study_progress_after_paid(app: Flask, user_id: str, course_id: str):
    with app.app_context():
        progress = AICourseStudyProgress.query.filter_by(
            user_id=user_id, course_id=course_id
        ).first()
        if progress:
            progress.is_paid = 1

        lessons = get_course_info(course_id)
        for lesson in lessons:
            for lesson in [ls for ls in lessons if ls.lesson_type != LESSON_TYPE_TRIAL]:
                lesson_progress = AILessonStudyProgress(
                    progress_id=progress.progress_id,
                    lesson_id=lesson.lesson_id,
                    sublesson_count=len(lesson.sublessons),
                    sublesson_completed_count=0,
                    script_index=0,
                    script_count=lesson.script_count,
                )
                db.session.add(lesson_progress)
                for sublesson in lesson.sublessons:
                    sublesson_progress = AILessonStudyProgress(
                        progress_id=progress.progress_id,
                        lesson_id=sublesson.lesson_id,
                        sublesson_count=len(sublesson.sublessons),
                        sublesson_completed_count=0,
                        script_index=0,
                        script_count=sublesson.script_count,
                    )
                    db.session.add(sublesson_progress)
        db.session.flush()


class LessonProgress:
    lesson_id: str
    lesson_no: str
    lesson_type: str
    lesson_name: str
    script_count: int
    sublesson_count: int
    sublesson_completed_count: int
    script_index: int
    script_count: int
    reset_count: int
    lesson_is_updated: int
    is_completed: int
    completed_time: str
    sublessons: list["LessonProgress"]

    def __init__(
        self,
        lesson_id: str,
        lesson_no: str,
        lesson_type: str,
        lesson_name: str,
        script_count: int,
        sublesson_count: int,
        sublesson_completed_count: int,
        script_index: int,
        reset_count: int,
        lesson_is_updated: int,
        is_completed: int,
        completed_time: str,
        sublessons: list["LessonProgress"],
    ):
        self.lesson_id = lesson_id
        self.lesson_no = lesson_no
        self.lesson_type = lesson_type
        self.lesson_name = lesson_name
        self.script_count = script_count
        self.sublesson_count = sublesson_count
        self.sublesson_completed_count = sublesson_completed_count
        self.script_index = script_index
        self.reset_count = reset_count
        self.lesson_is_updated = lesson_is_updated
        self.is_completed = is_completed
        self.completed_time = completed_time
        self.sublessons = sublessons

    def __json__(self):
        return {
            "lesson_id": self.lesson_id,
            "lesson_no": self.lesson_no,
            "lesson_type": self.lesson_type,
            "lesson_name": self.lesson_name,
            "script_count": self.script_count,
            "sublesson_count": self.sublesson_count,
            "sublesson_completed_count": self.sublesson_completed_count,
            "script_index": self.script_index,
            "reset_count": self.reset_count,
            "lesson_is_updated": self.lesson_is_updated,
            "is_completed": self.is_completed,
            "completed_time": self.completed_time,
            "sublessons": [i.__json__() for i in self.sublessons],
        }


class StudyProgress:
    chapter_count: int
    chapter_completed_count: int
    chapter_reset_count: int
    is_paid: int
    is_completed: int
    lessons: list[LessonProgress]


def get_study_progress(app: Flask, user_id: str, course_id: str) -> StudyProgress:
    with app.app_context():
        progress = AICourseStudyProgress.query.filter_by(
            user_id=user_id, course_id=course_id
        ).first()
        if not progress:
            init_study_progress(app, user_id, course_id)
            progress = AICourseStudyProgress.query.filter_by(
                user_id=user_id, course_id=course_id
            ).first()
        lesson_progress = AILessonStudyProgress.query.filter_by(
            progress_id=progress.progress_id
        ).all()
        lessons_infos = AILesson.query.filter(
            AILesson.lesson_id.in_([i.lesson_id for i in lesson_progress])
        ).all()
        lesson_map = {i.lesson_id: i for i in lessons_infos}
        lessons = []
        for lesson_progress in lesson_progress:
            lesson = lesson_map.get(lesson_progress.lesson_id)
            if lesson:
                lessons.append(
                    LessonProgress(
                        lesson_id=lesson.lesson_id,
                        lesson_no=lesson.lesson_no,
                        lesson_type=lesson.lesson_type,
                        lesson_name=lesson.lesson_name,
                        sublesson_count=lesson_progress.sublesson_count,
                        sublesson_completed_count=lesson_progress.sublesson_completed_count,
                        script_index=lesson_progress.script_index,
                        script_count=lesson_progress.script_count,
                        reset_count=lesson_progress.reset_count,
                        lesson_is_updated=lesson_progress.lesson_is_updated,
                        is_completed=lesson_progress.is_completed,
                        completed_time=lesson_progress.completed_time,
                        sublessons=[],
                    )
                )

        sorted_lessons = sorted(lessons, key=lambda x: x.lesson_no)
        return_lessons = []
        for lesson in sorted_lessons:
            if len(lesson.lesson_no) == 2:
                return_lessons.append(lesson)
            else:
                return_lessons[-1].sublessons.append(lesson)
        return StudyProgress(
            chapter_count=progress.chapter_count,
            chapter_completed_count=progress.chapter_completed_count,
            chapter_reset_count=progress.chapter_reset_count,
            is_paid=progress.is_paid,
            is_completed=progress.is_completed,
            lessons=return_lessons,
        )


def get_study_progress_by_user_id(app: Flask, user_id: str) -> list[StudyProgress]:
    with app.app_context():
        progress = AICourseStudyProgress.query.filter_by(user_id=user_id).all()
        if not progress:
            return []
        lesson_progress = AILessonStudyProgress.query.filter(
            AILessonStudyProgress.progress_id.in_([i.progress_id for i in progress])
        ).all()
        course_infos = AICourse.query.filter(
            AICourse.course_id.in_([i.course_id for i in progress])
        ).all()
        lessons = AILesson.query.filter(
            AILesson.course_id.in_([i.course_id for i in course_infos])
        ).all()
        for course_info in course_infos:
            lesson_map = {i.lesson_id: i for i in lessons}
            lessons = []
            for lesson_progress in lesson_progress:
                lesson = lesson_map.get(lesson_progress.lesson_id)
            if lesson:
                lessons.append(
                    LessonProgress(
                        lesson_id=lesson.lesson_id,
                        lesson_no=lesson.lesson_no,
                        lesson_type=lesson.lesson_type,
                        lesson_name=lesson.lesson_name,
                        sublesson_count=lesson_progress.sublesson_count,
                        sublesson_completed_count=lesson_progress.sublesson_completed_count,
                        script_index=lesson_progress.script_index,
                        script_count=lesson_progress.script_count,
                        reset_count=lesson_progress.reset_count,
                        lesson_is_updated=lesson_progress.lesson_is_updated,
                        is_completed=lesson_progress.is_completed,
                        completed_time=lesson_progress.completed_time,
                        sublessons=[],
                    )
                )

        sorted_lessons = sorted(lessons, key=lambda x: x.lesson_no)

        return_lessons = []
        for lesson in sorted_lessons:
            if len(lesson.lesson_no) == 2:
                return_lessons.append(lesson)
            else:
                return_lessons[-1].sublessons.append(lesson)
        return StudyProgress(
            chapter_count=progress.chapter_count,
            chapter_completed_count=progress.chapter_completed_count,
            chapter_reset_count=progress.chapter_reset_count,
            is_paid=progress.is_paid,
            is_completed=progress.is_completed,
            lessons=return_lessons,
        )
