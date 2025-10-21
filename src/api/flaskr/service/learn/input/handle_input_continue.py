from flask import Flask
from flaskr.service.learn.const import ROLE_STUDENT
from flaskr.service.learn.plugin import (
    SHIFU_CONTINUE_HANDLER_MAP,
)
from flaskr.service.learn.utils import generation_attend, get_script_ui_label
from flaskr.dao import db
from flaskr.framework.plugin.plugin_manager import extensible_generic
from flaskr.service.user.models import User
from flaskr.service.shifu.shifu_struct_manager import ShifuOutlineItemDto
from flaskr.service.shifu.adapter import BlockDTO
from langfuse.client import StatefulTraceClient
from flaskr.service.learn.plugin import register_shifu_continue_handler
from flaskr.i18n import _
from typing import Generator
from flaskr.service.shifu.dtos import ButtonDTO


@register_shifu_continue_handler("continue")
@extensible_generic
def _handle_input_continue(
    app: Flask,
    user_info: User,
    attend_id: str,
    input: str,
    outline_item_info: ShifuOutlineItemDto,
    block_dto: BlockDTO,
    trace_args: dict,
    trace: StatefulTraceClient,
    is_preview: bool = False,
) -> Generator[str, None, None]:
    if block_dto.block_content:
        # The continue button has a non-default label
        default = _("server.common.continue")
        button_label: ButtonDTO = block_dto.block_content
        if input != default and attend_id:
            log_script = generation_attend(
                app, user_info, attend_id, outline_item_info, block_dto
            )
            log_script.generated_content = get_script_ui_label(app, button_label.label)
            log_script.role = ROLE_STUDENT
            db.session.add(log_script)
        span = trace.span(name="user_continue", input=input)
        span.end()
        db.session.flush()

    continue_func = SHIFU_CONTINUE_HANDLER_MAP.get(block_dto.type, None)

    if continue_func:
        app.logger.info(f"continue_func: {continue_func.__name__}")
        continue_func(
            app,
            user_info,
            attend_id,
            outline_item_info,
            block_dto,
            trace,
            trace_args,
            is_preview,
        )
