import datetime
import decimal
import json
from typing import List


from flaskr.service.order.consts import (
    ORDER_STATUS_INIT,
    ORDER_STATUS_SUCCESS,
    ORDER_STATUS_TO_BE_PAID,
    ORDER_STATUS_TIMEOUT,
    ORDER_STATUS_VALUES,
)
from flaskr.service.common.dtos import USER_STATE_PAID, USER_STATE_REGISTERED
from flaskr.service.user.models import User, UserConversion
from flaskr.service.active import (
    query_active_record,
    query_and_join_active,
    query_to_failure_active,
)
from flaskr.common.swagger import register_schema_to_swagger
from flaskr.api.doc.feishu import send_notify
from .models import Order, PingxxOrder
from flask import Flask
from ...dao import db, redis_client
from ..common.models import (
    raise_error,
)
from ...util.uuid import generate_id as get_uuid
from .pingxx_order import create_pingxx_order
from flaskr.service.promo.models import Coupon, CouponUsage as CouponUsageModel
import pytz
from flaskr.service.lesson.funcs import get_course_info
from flaskr.service.lesson.funcs import AICourseDTO
from flaskr.service.promo.consts import COUPON_TYPE_FIXED, COUPON_TYPE_PERCENT
from flaskr.service.order.query_discount import query_discount_record
from flaskr.common.config import get_config


@register_schema_to_swagger
class AICourseLessonAttendDTO:
    """
    AICourseLessonAttendDTO
    """

    attend_id: str
    lesson_id: str
    course_id: str
    user_id: str
    status: int
    index: int

    def __init__(self, attend_id, lesson_id, course_id, user_id, status, index):
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
            "index": self.index,
        }


@register_schema_to_swagger
class PayItemDto:
    """
    PayItemDto
    """

    name: str
    price_name: str
    price: str
    is_discount: bool
    discount_code: str

    def __init__(self, name, price_name, price, is_discount, discount_code):
        self.name = name
        self.price_name = price_name
        self.price = price
        self.is_discount = is_discount
        self.discount_code = discount_code

    def __json__(self):
        return {
            "name": self.name,
            "price_name": self.price_name,
            "price": str(self.price),
            "is_discount": self.is_discount,
        }


@register_schema_to_swagger
class AICourseBuyRecordDTO:
    """
    AICourseBuyRecordDTO
    """

    order_id: str
    user_id: str
    course_id: str
    price: decimal.Decimal
    status: int
    discount: str
    active_discount: str
    value_to_pay: str
    price_item: List[PayItemDto]

    def __init__(
        self, record_id, user_id, course_id, price, status, discount, price_item
    ):
        self.order_id = record_id
        self.user_id = user_id
        self.course_id = course_id
        self.price = price
        self.status = status
        self.discount = discount
        self.value_to_pay = str(decimal.Decimal(price) - decimal.Decimal(discount))
        self.price_item = price_item

    def __json__(self):
        def format_decimal(value):
            if isinstance(value, str):
                formatted_value = value  # Convert to string with two decimal places
            else:
                formatted_value = "{0:.2f}".format(value)
            # If the decimal part is .00, remove it
            if formatted_value.endswith(".00"):
                return formatted_value[:-3]
            return formatted_value

        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "course_id": self.course_id,
            "price": format_decimal(self.price),
            "status": self.status,
            "status_desc": ORDER_STATUS_VALUES[self.status],
            "discount": format_decimal(self.discount),
            "value_to_pay": format_decimal(self.value_to_pay),
            "price_item": [item.__json__() for item in self.price_item],
        }


# to do : add to plugins
def send_order_feishu(app: Flask, record_id: str):
    order_info = query_buy_record(app, record_id)
    if order_info is None:
        return
    user_info: User = User.query.filter(User.user_id == order_info.user_id).first()
    if not user_info:
        return
    course_info: AICourseDTO = get_course_info(app, order_info.course_id)
    if not course_info:
        return

    title = "购买课程通知"
    msgs = []
    msgs.append("手机号：{}".format(user_info.mobile))
    msgs.append("昵称：{}".format(user_info.name))
    msgs.append("课程名称：{}".format(course_info.course_name))
    msgs.append("实付金额：{}".format(order_info.price))
    user_convertion = UserConversion.query.filter(
        UserConversion.user_id == order_info.user_id
    ).first()
    channel = ""
    if user_convertion:
        channel = user_convertion.conversion_source
    msgs.append("渠道：{}".format(channel))
    for item in order_info.price_item:
        msgs.append("{}-{}-{}".format(item.name, item.price_name, item.price))
        if item.is_discount:
            msgs.append("优惠码：{}".format(item.discount_code))
    user_count = User.query.filter(User.user_state == USER_STATE_PAID).count()
    msgs.append("总付费用户数：{}".format(user_count))
    user_reg_count = User.query.filter(User.user_state >= USER_STATE_REGISTERED).count()
    msgs.append("总注册用户数：{}".format(user_reg_count))
    user_total_count = User.query.count()
    msgs.append("总访客数：{}".format(user_total_count))
    send_notify(app, title, msgs)


def is_order_has_timeout(app: Flask, origin_record: Order):
    pay_order_expire_time = app.config.get("PAY_ORDER_EXPIRE_TIME")
    if pay_order_expire_time is None:
        return False
    pay_order_expire_time = int(pay_order_expire_time)
    bj_time = pytz.timezone("Asia/Shanghai")
    aware_created = bj_time.localize(origin_record.created_at)
    created_timestamp = int(aware_created.timestamp())
    current_timestamp = int(datetime.datetime.now().timestamp())
    if current_timestamp > (created_timestamp + pay_order_expire_time):
        # Order timeout
        # Update the order status
        origin_record.status = ORDER_STATUS_TIMEOUT
        db.session.commit()
        # Check if there are discount coupons in the order. If there are, rollback the discount coupons
        from flaskr.service.promo.funcs import timeout_coupon_code_rollback

        timeout_coupon_code_rollback(
            app, origin_record.user_bid, origin_record.order_bid
        )
        return True
    return False


def init_buy_record(app: Flask, user_id: str, course_id: str, active_id: str = None):
    with app.app_context():
        order_timeout_make_new_order = False
        find_active_id = None
        course_info: AICourseDTO = get_course_info(app, course_id)
        app.logger.info(f"course_info: {course_info}")
        if not course_info:
            raise_error("server.shifu.courseNotFound")
        origin_record = (
            Order.query.filter(
                Order.user_bid == user_id,
                Order.shifu_bid == course_id,
                Order.status != ORDER_STATUS_TIMEOUT,
            )
            .order_by(Order.id.asc())
            .first()
        )
        print("price: ", course_info.course_price)
        if origin_record:
            if origin_record.status != ORDER_STATUS_SUCCESS:
                order_timeout_make_new_order = is_order_has_timeout(app, origin_record)
            if order_timeout_make_new_order:
                # Check if there are any coupons in the order. If there are, make them failure
                find_active_id = query_to_failure_active(
                    app, origin_record.user_bid, origin_record.order_bid
                )
        else:
            order_timeout_make_new_order = True
            find_active_id = None
        if (not order_timeout_make_new_order) and origin_record and active_id is None:
            return query_buy_record(app, origin_record.order_bid)
        # raise_error("module.backend.order.orderNotFound")
        order_id = str(get_uuid(app))
        if order_timeout_make_new_order:
            buy_record = Order()
            buy_record.user_bid = user_id
            buy_record.shifu_bid = course_id
            buy_record.payable_price = decimal.Decimal(course_info.course_price)
            buy_record.status = ORDER_STATUS_INIT
            buy_record.order_bid = order_id
            buy_record.payable_price = course_info.course_price
            print("buy_record: ", buy_record.payable_price)
        else:
            buy_record = origin_record
            order_id = origin_record.order_bid
        if find_active_id:
            active_id = find_active_id
        active_records = query_and_join_active(
            app, course_id, user_id, order_id, active_id
        )
        price_items = []
        price_items.append(
            PayItemDto("商品", "基础价格", buy_record.payable_price, False, None)
        )
        discount_value = decimal.Decimal(0.00)
        if active_records:
            for active_record in active_records:
                discount_value = decimal.Decimal(discount_value) + decimal.Decimal(
                    active_record.price
                )
                price_items.append(
                    PayItemDto(
                        "活动",
                        active_record.active_name,
                        active_record.price,
                        True,
                        None,
                    )
                )
        print("discount_value: ", discount_value)
        buy_record.paid_price = buy_record.payable_price - discount_value
        db.session.merge(buy_record)
        db.session.commit()
        return AICourseBuyRecordDTO(
            buy_record.order_bid,
            buy_record.user_bid,
            buy_record.shifu_bid,
            buy_record.payable_price,
            buy_record.status,
            discount_value,
            price_items,
        )


@register_schema_to_swagger
class BuyRecordDTO:
    """
    BuyRecordDTO
    """

    order_id: str
    user_id: str  # 用户id
    price: str  # 价格
    channel: str  # 支付渠道
    qr_url: str  # 二维码地址

    def __init__(self, record_id, user_id, price, channel, qr_url):
        self.order_id = record_id
        self.user_id = user_id
        self.price = price
        self.channel = channel
        self.qr_url = qr_url

    def __json__(self):
        return {
            "order_id": self.order_id,
            "user_id": self.user_id,
            "price": str(self.price),
            "channel": self.channel,
            "qr_url": self.qr_url,
        }


def generate_charge(
    app: Flask, record_id: str, channel: str, client_ip: str
) -> BuyRecordDTO:
    """
    Generate charge
    """
    with app.app_context():
        app.logger.info(
            "generate charge for record:{} channel:{}".format(record_id, channel)
        )

        buy_record: Order = Order.query.filter(
            Order.order_bid == record_id,
            Order.status != ORDER_STATUS_TIMEOUT,
        ).first()
        if not buy_record:
            raise_error("server.order.orderNotFound")
        course: AICourseDTO = get_course_info(app, buy_record.shifu_bid)
        if not course:
            raise_error("server.shifu.courseNotFound")
        app.logger.info("buy record found:{}".format(buy_record))
        if buy_record.status == ORDER_STATUS_SUCCESS:
            app.logger.warning("buy record:{} status is not init".format(record_id))
            return BuyRecordDTO(
                buy_record.order_bid,
                buy_record.user_bid,
                buy_record.paid_price,
                channel,
                "",
            )
            # raise_error("module.backend.order.orderHasPaid")
        amount = int(buy_record.paid_price * 100)
        product_id = course.course_id
        subject = course.course_name
        body = course.course_name
        order_no = str(get_uuid(app))
        qr_url = None
        pingpp_id = get_config("PINGXX_APP_ID")
        if amount == 0:
            success_buy_record(app, buy_record.order_bid)
            return BuyRecordDTO(
                buy_record.order_bid,
                buy_record.user_bid,
                buy_record.paid_price,
                channel,
                qr_url,
            )
        if channel == "wx_pub_qr":  # wxpay scan
            extra = dict({"product_id": product_id})
            charge = create_pingxx_order(
                app,
                order_no,
                pingpp_id,
                channel,
                amount,
                client_ip,
                subject,
                body,
                extra,
            )
            qr_url = charge["credential"]["wx_pub_qr"]
        elif channel == "alipay_qr":  # alipay scan
            extra = dict({})
            charge = create_pingxx_order(
                app,
                order_no,
                pingpp_id,
                channel,
                amount,
                client_ip,
                subject,
                body,
                extra,
            )
            qr_url = charge["credential"]["alipay_qr"]
        elif channel == "wx_pub":  # wxpay JSAPI
            user = User.query.filter(User.user_id == buy_record.user_bid).first()
            extra = dict({"open_id": user.user_open_id})
            charge = create_pingxx_order(
                app,
                order_no,
                pingpp_id,
                channel,
                amount,
                client_ip,
                subject,
                body,
                extra,
            )
            qr_url = charge["credential"]["wx_pub"]
        elif channel == "wx_wap":  # wxpay H5
            extra = dict({})
            charge = create_pingxx_order(
                app,
                order_no,
                pingpp_id,
                channel,
                amount,
                client_ip,
                subject,
                body,
                extra,
            )
        else:
            app.logger.error("channel:{} not support".format(channel))
            raise_error("server.pay.payChannelNotSupport")
        app.logger.info("charge created:{}".format(charge))
        buy_record.status = ORDER_STATUS_TO_BE_PAID
        pingxxOrder = PingxxOrder()
        pingxxOrder.order_bid = order_no
        pingxxOrder.user_bid = buy_record.user_bid
        pingxxOrder.shifu_bid = buy_record.shifu_bid
        pingxxOrder.order_bid = buy_record.order_bid
        pingxxOrder.transaction_no = charge["transaction_no"]
        pingxxOrder.app_id = charge["app"]
        pingxxOrder.channel = charge["channel"]
        pingxxOrder.channel = charge["channel"]
        pingxxOrder.amount = amount
        pingxxOrder.currency = charge["currency"]
        pingxxOrder.subject = charge["subject"]
        pingxxOrder.body = charge["body"]
        pingxxOrder.transaction_no = charge["order_no"]
        pingxxOrder.client_ip = charge["client_ip"]
        pingxxOrder.extra = str(charge["extra"])
        pingxxOrder.charge_id = charge["id"]
        pingxxOrder.status = 0
        pingxxOrder.charge_object = str(charge)
        db.session.add(pingxxOrder)
        db.session.commit()
        return BuyRecordDTO(
            buy_record.order_bid,
            buy_record.user_bid,
            buy_record.paid_price,
            channel,
            qr_url,
        )


def success_buy_record_from_pingxx(app: Flask, charge_id: str, body: dict):
    """
    Success buy record from pingxx
    """
    with app.app_context():
        pingxx_order = PingxxOrder.query.filter(
            PingxxOrder.charge_id == charge_id
        ).first()
        if not pingxx_order:
            return
        lock = redis_client.lock(
            "success_buy_record_from_pingxx" + charge_id,
            timeout=10,
            blocking_timeout=10,
        )

        if not lock:
            app.logger.error('lock failed for charge:"{}"'.format(charge_id))
        if lock.acquire(blocking=True):
            try:
                app.logger.info(
                    'success buy record from pingxx charge:"{}"'.format(charge_id)
                )
                pingxx_order: PingxxOrder = PingxxOrder.query.filter(
                    PingxxOrder.charge_id == charge_id
                ).first()
                if not pingxx_order:
                    lock.release()
                    return None
                pingxx_order.update = datetime.datetime.now()
                pingxx_order.status = 1
                pingxx_order.charge_object = json.dumps(body)
                if pingxx_order:
                    buy_record: Order = Order.query.filter(
                        Order.order_bid == pingxx_order.order_bid,
                    ).first()

                    if buy_record and buy_record.status == ORDER_STATUS_TO_BE_PAID:
                        try:
                            user_info = User.query.filter(
                                User.user_id == buy_record.user_bid
                            ).first()
                            if not user_info:
                                app.logger.error(
                                    "user:{} not found".format(buy_record.user_bid)
                                )
                            else:
                                user_info.user_state = USER_STATE_PAID
                        except Exception as e:
                            app.logger.error("update user state error:{}".format(e))
                        buy_record.status = ORDER_STATUS_SUCCESS
                        db.session.commit()
                        send_order_feishu(app, buy_record.order_bid)
                        return query_buy_record(app, buy_record.order_bid)
                    else:
                        app.logger.error(
                            "record:{} not found".format(pingxx_order.order_bid)
                        )
                else:
                    app.logger.error("charge:{} not found".format(charge_id))
                return None
            except Exception as e:
                app.logger.error(
                    'success buy record from pingxx charge:"{}" error:{}'.format(
                        charge_id, e
                    )
                )
            finally:
                lock.release()


def success_buy_record(app: Flask, record_id: str):
    """
    Success buy record
    """
    with app.app_context():
        app.logger.info('success buy record:"{}"'.format(record_id))
        buy_record = Order.query.filter(Order.order_bid == record_id).first()
        if buy_record:
            user_info = User.query.filter(User.user_id == buy_record.user_bid).first()
            if not user_info:
                app.logger.error("user:{} not found".format(buy_record.user_bid))
            else:
                user_info.user_state = USER_STATE_PAID
            buy_record.status = ORDER_STATUS_SUCCESS
            db.session.commit()
            send_order_feishu(app, buy_record.order_bid)
            return query_buy_record(app, record_id)
        else:
            app.logger.error("record:{} not found".format(record_id))
        return None


def query_raw_buy_record(app: Flask, user_id, course_id) -> Order:
    """
    Query raw buy record
    """
    with app.app_context():
        buy_record = Order.query.filter(
            Order.shifu_bid == course_id,
            Order.user_bid == user_id,
            Order.status != ORDER_STATUS_TIMEOUT,
            Order.deleted == 0,
        ).first()
        if buy_record:
            return buy_record
        return None


class DiscountInfo:
    discount_value: str
    items: list[PayItemDto]

    def __init__(self, discount_value, items):
        self.discount_value = discount_value
        self.items = items


def calculate_discount_value(
    app: Flask,
    price: str,
    active_records: list,
    discount_records: list[CouponUsageModel],
) -> DiscountInfo:
    """
    Calculate discount value
    """
    discount_value = 0
    items = []
    if active_records is not None and len(active_records) > 0:
        for active_record in active_records:
            discount_value += active_record.price
            items.append(
                PayItemDto(
                    "活动", active_record.active_name, active_record.price, True, None
                )
            )
    if discount_records is not None and len(discount_records) > 0:
        discount_ids = [i.coupon_bid for i in discount_records]
        coupons: list[Coupon] = Coupon.query.filter(
            Coupon.coupon_bid.in_(discount_ids)
        ).all()
        coupon_maps: dict[str, Coupon] = {i.coupon_bid: i for i in coupons}
        for discount_record in discount_records:
            discount = coupon_maps.get(discount_record.coupon_bid, None)
            if discount:
                if discount.discount_type == COUPON_TYPE_FIXED:
                    discount_value += discount.value
                elif discount.discount_type == COUPON_TYPE_PERCENT:
                    discount_value += discount.value * price / 100
                items.append(
                    PayItemDto(
                        "优惠",
                        discount.channel,
                        discount.value,
                        True,
                        discount.channel,
                    )
                )
    if discount_value > price:
        discount_value = price
    return DiscountInfo(discount_value, items)


def query_buy_record(app: Flask, record_id: str) -> AICourseBuyRecordDTO:
    with app.app_context():
        app.logger.info('query buy record:"{}"'.format(record_id))
        buy_record: Order = Order.query.filter(Order.order_bid == record_id).first()
        print("buy_record: ", buy_record.payable_price, buy_record.paid_price)
        if buy_record:
            item = []
            item.append(
                PayItemDto("商品", "基础价格", buy_record.payable_price, False, None)
            )
            recaul_discount = buy_record.status != ORDER_STATUS_SUCCESS
            if buy_record.payable_price > 0:
                aitive_records = query_active_record(app, record_id, recaul_discount)
                discount_records = query_discount_record(
                    app, record_id, recaul_discount
                )
                discount_info = calculate_discount_value(
                    app, buy_record.payable_price, aitive_records, discount_records
                )
                if (
                    recaul_discount
                    and discount_info.discount_value != buy_record.payable_price
                ):
                    app.logger.info(
                        "update discount value for buy record:{}".format(record_id)
                    )
                    # buy_record.payable_price = discount_info.discount_value
                    buy_record.paid_price = (
                        buy_record.payable_price - discount_info.discount_value
                    )
                    buy_record.updated_at = datetime.datetime.now()
                    db.session.commit()
                item = discount_info.items

            return AICourseBuyRecordDTO(
                buy_record.order_bid,
                buy_record.user_bid,
                buy_record.shifu_bid,
                buy_record.payable_price,
                buy_record.status,
                buy_record.payable_price - buy_record.paid_price,
                item,
            )

        raise_error("server.order.orderNotFound")
