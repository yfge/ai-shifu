from datetime import datetime
import pytz


from ...dao import db
from .models import Active, ActiveUserRecord
from ...util import generate_id


def create_active(
    app,
    course_id,
    active_name,
    active_desc,
    active_start_time,
    active_end_time,
    active_price,
):
    active = Active()
    active.active_id = generate_id(app)
    active.active_name = active_name
    active.active_desc = active_desc
    active.active_status = 1
    active.active_start_time = active_start_time
    active.active_end_time = active_end_time
    active.active_price = active_price
    active.active_filter = str({"course_id": course_id})
    active.active_course = course_id
    db.session.add(active)
    db.session.commit()
    return active.active_id


def create_active_user_record(
    app, active_id, user_id, price, order_id, status, active_name
) -> ActiveUserRecord:
    active_user_record = ActiveUserRecord()
    active_user_record.record_id = generate_id(app)
    active_user_record.active_id = active_id
    active_user_record.user_id = user_id
    active_user_record.price = price
    active_user_record.order_id = order_id
    active_user_record.status = status
    active_user_record.active_name = active_name
    db.session.add(active_user_record)
    return active_user_record


def query_and_join_active(app, course_id, user_id, order_id) -> list[ActiveUserRecord]:
    app.logger.info("find active for course:{} and user:{}".format(course_id, user_id))
    bj_time = pytz.timezone("Asia/Shanghai")
    now = datetime.now(bj_time)
    active_infos = Active.query.filter(
        Active.active_course == course_id,
        Active.active_status == 1,
        Active.active_start_time <= now,
        Active.active_end_time >= now,
    ).all()
    if not active_infos:
        app.logger.info(
            "no active for course:{} and user:{}".format(course_id, user_id)
        )
        return []
    active_user_records = []
    for active_info in active_infos:
        app.logger.info("active info:{}".format(active_info.active_name))
        active_user_record = ActiveUserRecord.query.filter(
            ActiveUserRecord.active_id == active_info.active_id,
            ActiveUserRecord.user_id == user_id,
        ).first()
        if active_user_record:
            active_user_records.append(active_user_record)
        else:
            active_user_records.append(
                create_active_user_record(
                    app,
                    active_info.active_id,
                    user_id,
                    active_info.active_price,
                    order_id,
                    0,
                    active_info.active_name,
                )
            )
    return active_user_records


def query_active(app, active_id) -> Active:
    return Active.query.filter(Active.active_id == active_id).first()


def query_active_record(app, order_id) -> list[ActiveUserRecord]:
    return ActiveUserRecord.query.filter(ActiveUserRecord.order_id == order_id).all()
