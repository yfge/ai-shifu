from flask import Flask
from flaskr.service.study.plugin import (
    register_shifu_input_handler,
)
from flaskr.service.order.funs import query_raw_buy_record
from flaskr.service.order.consts import BUY_STATUS_SUCCESS
from flaskr.framework.plugin.plugin_manager import extensible_generic
from flaskr.service.user.models import User
from flaskr.service.shifu.shifu_struct_manager import ShifuOutlineItemDto
from flaskr.service.shifu.adapter import BlockDTO
from langfuse.client import StatefulTraceClient


# @register_input_handler(input_type=INPUT_TYPE_PAY)
@extensible_generic
@register_shifu_input_handler("payment")
def _handle_input_pay(
    app: Flask,
    user_info: User,
    attend_id: str,
    input: str,
    outline_item_info: ShifuOutlineItemDto,
    block_dto: BlockDTO,
    trace_args: dict,
    trace: StatefulTraceClient,
):
    shifu_bid = outline_item_info.shifu_bid
    order = query_raw_buy_record(app, user_info.user_id, shifu_bid)
    if order and order.status == BUY_STATUS_SUCCESS:
        return
    return None
