from flask import Flask
from flaskr.service.study.input_funcs import BreakException
from flaskr.service.study.const import ROLE_STUDENT
from flaskr.service.study.plugin import (
    register_shifu_input_handler,
)
from flaskr.service.study.utils import (
    generation_attend,
    get_script_ui_label,
    make_script_dto,
)
from flaskr.dao import db
from flaskr.framework.plugin.plugin_manager import extensible_generic
from flaskr.service.shifu.shifu_struct_manager import ShifuOutlineItemDto
from flaskr.service.shifu.adapter import BlockDTO
from langfuse.client import StatefulTraceClient
from flaskr.service.user.models import User


@register_shifu_input_handler("login")
@extensible_generic
def _handle_input_login(
    app: Flask,
    user_info: User,
    attend_id: str,
    input: str,
    outline_item_info: ShifuOutlineItemDto,
    block_dto: BlockDTO,
    trace_args: dict,
    trace: StatefulTraceClient,
):
    log_script = generation_attend(
        app, user_info, attend_id, outline_item_info, block_dto
    )
    log_script.script_content = get_script_ui_label(app, block_dto.block_content)
    log_script.script_role = ROLE_STUDENT  # type: ignore
    db.session.add(log_script)
    if user_info.user_state != 0:
        yield make_script_dto("text", "", block_dto.bid, outline_item_info.bid)
    else:
        raise BreakException
