from flask import Flask

from flaskr.service.learn.const import INPUT_TYPE_PHONE
from flaskr.service.learn.plugin import register_shifu_output_handler
from flaskr.service.user.models import User
from flaskr.service.learn.utils import get_script_ui_label
from flaskr.i18n import _
from flaskr.service.shifu.shifu_struct_manager import ShifuOutlineItemDto
from flaskr.service.shifu.adapter import BlockDTO
from langfuse.client import StatefulTraceClient
from flaskr.service.shifu.dtos import PhoneDTO
from flaskr.service.learn.dtos import ScriptDTO


@register_shifu_output_handler("phone")
def _handle_output_phone(
    app: Flask,
    user_info: User,
    attend_id: str,
    outline_item_info: ShifuOutlineItemDto,
    block_dto: BlockDTO,
    trace_args: dict,
    trace: StatefulTraceClient,
    is_preview: bool = False,
) -> ScriptDTO:
    phone: PhoneDTO = block_dto.block_content
    msg = get_script_ui_label(app, phone.label)
    if not msg:
        msg = _("module.backend.common.phone")
    return ScriptDTO(
        INPUT_TYPE_PHONE,
        msg,
        outline_item_info.bid,
        block_dto.bid,
    )
