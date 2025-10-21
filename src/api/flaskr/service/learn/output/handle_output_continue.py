from flask import Flask

from flaskr.service.learn.plugin import register_shifu_output_handler
from flaskr.service.learn.const import INPUT_TYPE_CONTINUE
from flaskr.service.user.models import User
from flaskr.i18n import _
from flaskr.service.learn.utils import get_script_ui_label
from flaskr.service.shifu.shifu_struct_manager import ShifuOutlineItemDto
from flaskr.service.shifu.adapter import BlockDTO
from langfuse.client import StatefulTraceClient
from flaskr.service.shifu.dtos import ButtonDTO
from flaskr.service.learn.dtos import ScriptDTO


@register_shifu_output_handler("continue")
def _handle_output_continue(
    app: Flask,
    user_info: User,
    attend_id: str,
    outline_item_info: ShifuOutlineItemDto,
    block_dto: BlockDTO,
    trace_args: dict,
    trace: StatefulTraceClient,
    is_preview: bool = False,
) -> ScriptDTO:
    msg = ""
    if isinstance(block_dto.block_content, ButtonDTO):
        msg = get_script_ui_label(app, block_dto.block_content.label)
    display = bool(msg)  # Set display based on whether msg has content
    if not msg:
        msg = _("server.common.continue")  # Assign default message if msg is empty

    msg = get_script_ui_label(app, msg)
    if not msg:
        msg = _("server.common.continue")
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
        block_dto.bid,
    )
