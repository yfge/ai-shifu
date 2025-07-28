from flask import Flask

from flaskr.service.study.plugin import register_shifu_output_handler
from flaskr.service.study.const import INPUT_TYPE_CONTINUE
from flaskr.service.user.models import User
from flaskr.i18n import _
from flaskr.service.study.utils import get_script_ui_label
from flaskr.service.shifu.shifu_struct_manager import ShifuOutlineItemDto
from flaskr.service.shifu.adapter import BlockDTO
from langfuse.client import StatefulTraceClient
from flaskr.service.shifu.dtos import ButtonDTO
from flaskr.service.study.dtos import ScriptDTO


@register_shifu_output_handler("continue")
def handle_output_continue(
    app: Flask,
    user_info: User,
    attend_id: str,
    outline_item_info: ShifuOutlineItemDto,
    block_dto: BlockDTO,
    trace_args: dict,
    trace: StatefulTraceClient,
) -> ScriptDTO:

    msg = ""
    if block_dto.block_content:
        btn: ButtonDTO = block_dto.block_content
        msg = get_script_ui_label(app, btn.label)
    display = bool(msg)  # Set display based on whether msg has content
    if not msg:
        msg = _("COMMON.CONTINUE")  # Assign default message if msg is empty

    msg = get_script_ui_label(app, msg)
    if not msg:
        msg = _("COMMON.CONTINUE")

    btn = [
        {
            "label": msg,
            "value": msg,
            "type": INPUT_TYPE_CONTINUE,
            "display": display,
        }
    ]

    return ScriptDTO(
        "buttons",
        {"buttons": btn},
        outline_item_info.bid,
        outline_item_info.bid,
    )
