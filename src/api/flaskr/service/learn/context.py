import queue
import threading
from typing import Generator, Union
from enum import Enum
from pydantic import BaseModel
from flask import Flask
from flaskr.dao import db
from flaskr.service.shifu.shifu_struct_manager import ShifuOutlineItemDto, ShifuInfoDto
from flaskr.service.learn.utils import make_script_dto
from flaskr.service.shifu.models import (
    DraftBlock,
    PublishedBlock,
    DraftOutlineItem,
    PublishedOutlineItem,
    DraftShifu,
    PublishedShifu,
)
from flaskr.service.learn.models import LearnProgressRecord, LearnGeneratedBlock
from flaskr.service.shifu.shifu_history_manager import HistoryItem
from flaskr.service.shifu.shifu_struct_manager import get_outline_item_dto
from flaskr.service.shifu.adapter import (
    generate_block_dto_from_model_internal,
    BlockDTO,
    PaymentDTO,
)
from langfuse.client import StatefulTraceClient
from ...api.langfuse import langfuse_client as langfuse, MockClient
from flaskr.service.common import raise_error
from flaskr.service.order.consts import (
    LEARN_STATUS_RESET,
    LEARN_STATUS_IN_PROGRESS,
    LEARN_STATUS_COMPLETED,
    LEARN_STATUS_NOT_STARTED,
    LEARN_STATUS_LOCKED,
)
from flaskr.service.lesson.const import LESSON_TYPE_NORMAL
from flaskr.service.learn.plugin import (
    handle_block_input,
    handle_block_output,
    check_block_continue,
)

from flaskr.service.user.models import User
from flaskr.service.order.consts import get_learn_status_values
from flaskr.service.shifu.struct_utils import find_node_with_parents
from flaskr.util import generate_id
from flaskr.service.shifu.dtos import GotoDTO, GotoConditionDTO
from flaskr.service.profile.funcs import get_user_variable_by_variable_id
from flaskr.service.learn.const import ROLE_TEACHER
from flaskr.service.learn.exceptions import PaidException

context_local = threading.local()


class RunType(Enum):
    INPUT = "input"
    OUTPUT = "output"


class LLMSettings(BaseModel):
    model: str
    temperature: float

    def __str__(self):
        return f"model: {self.model}, temperature: {self.temperature}"

    def __repr__(self):
        return self.__str__()

    def __json__(self):
        return {"model": self.model, "temperature": self.temperature}


# outline update type
# outline is a node when has outline item as children
# outline is a leaf when has block item as children
# outline is a leaf when has no children
class _OutlineUpateType(Enum):
    NODE_COMPLETED = "node_completed"
    NODE_START = "node_start"
    LEAF_COMPLETED = "leaf_completed"
    LEAF_START = "leaf_start"


class _OutlineUpate:
    type: _OutlineUpateType
    outline_item_info: ShifuOutlineItemDto

    def __init__(self, type: _OutlineUpateType, outline_item_info: ShifuOutlineItemDto):
        self.type = type
        self.outline_item_info = outline_item_info


class RunScriptInfo:
    attend: LearnProgressRecord
    outline_item_info: ShifuOutlineItemDto
    block_dto: BlockDTO

    def __init__(
        self,
        attend: LearnProgressRecord,
        outline_item_info: ShifuOutlineItemDto,
        block_dto: BlockDTO,
    ):
        self.attend = attend
        self.outline_item_info = outline_item_info
        self.block_dto = block_dto


class RunScriptContext:
    user_id: str
    attend_id: str
    is_paid: bool
    preview_mode: bool
    _q: queue.Queue
    _outline_item_info: ShifuOutlineItemDto
    _struct: HistoryItem
    _user_info: User
    _is_paid: bool
    _preview_mode: bool
    _shifu_ids: list[str]
    _run_type: RunType
    _app: Flask
    _shifu_model: Union[DraftShifu, PublishedShifu]
    _outline_model: Union[DraftOutlineItem, PublishedOutlineItem]
    _block_model: Union[DraftBlock, PublishedBlock]
    _trace_args: dict
    _shifu_info: ShifuInfoDto
    _trace: Union[StatefulTraceClient, MockClient]
    _input_type: str
    _input: str
    _can_continue: bool

    def __init__(
        self,
        app: Flask,
        shifu_info: ShifuInfoDto,
        struct: HistoryItem,
        outline_item_info: ShifuOutlineItemDto,
        user_info: User,
        is_paid: bool,
        preview_mode: bool,
    ):
        self.app = app
        self._struct = struct
        self._outline_item_info = outline_item_info
        self._user_info = user_info
        self._is_paid = is_paid
        self._preview_mode = preview_mode
        self._shifu_info = shifu_info

        self.shifu_ids = []
        self.outline_item_ids = []
        self.current_outline_item = None
        self._run_type = RunType.INPUT
        self._can_continue = True

        if preview_mode:
            self._outline_model = DraftOutlineItem
            self._block_model = DraftBlock
            self._shifu_model = DraftShifu
        else:
            self._outline_model = PublishedOutlineItem
            self._block_model = PublishedBlock
            self._shifu_model = PublishedShifu
        # get current attend
        self._q = queue.Queue()
        self._q.put(struct)
        while not self._q.empty():
            item = self._q.get()
            if item.bid == outline_item_info.bid:
                self._current_outline_item = item
                break
            if item.children:
                for child in item.children:
                    self._q.put(child)
        # Move _get_current_attend call to run method to handle PaidException properly
        self._current_attend = None

        self._trace_args = {}
        self._trace_args["user_id"] = user_info.user_id
        self._trace_args["session_id"] = (
            ""  # Will be set when _current_attend is initialized
        )
        self._trace_args["input"] = ""
        self._trace_args["name"] = self._outline_item_info.title
        self._trace = langfuse.trace(**self._trace_args)
        self._trace_args["output"] = ""

        context_local.current_context = self

    @staticmethod
    def get_current_context(app: Flask) -> Union["RunScriptContext", None]:
        if not hasattr(context_local, "current_context"):
            return None
        return context_local.current_context

    def _get_current_attend(
        self, outline_item_info: ShifuOutlineItemDto
    ) -> LearnProgressRecord:
        attend_info: LearnProgressRecord = (
            LearnProgressRecord.query.filter(
                LearnProgressRecord.outline_item_bid == outline_item_info.bid,
                LearnProgressRecord.user_bid == self._user_info.user_id,
                LearnProgressRecord.status != LEARN_STATUS_RESET,
            )
            .order_by(LearnProgressRecord.id.desc())
            .first()
        )
        if not attend_info:
            outline_item_info_db: Union[DraftOutlineItem, PublishedOutlineItem] = (
                self._outline_model.query.filter(
                    self._outline_model.outline_item_bid == outline_item_info.bid,
                ).first()
            )
            if not outline_item_info_db:
                raise_error("server.lesson.lessonNotFoundInCourse")
            if outline_item_info_db.type == LESSON_TYPE_NORMAL:
                if (not self._is_paid) and (not self._preview_mode):
                    raise PaidException()
            parent_path = find_node_with_parents(
                self._struct, outline_item_info_db.outline_item_bid
            )
            attend_info = None
            for item in parent_path:
                if item.type == "outline":
                    attend_info = LearnProgressRecord.query.filter(
                        LearnProgressRecord.outline_item_bid == item.bid,
                        LearnProgressRecord.user_bid == self._user_info.user_id,
                        LearnProgressRecord.status != LEARN_STATUS_RESET,
                    ).first()
                    if attend_info:
                        continue
                    attend_info = LearnProgressRecord()
                    attend_info.outline_item_bid = outline_item_info_db.outline_item_bid
                    attend_info.shifu_bid = outline_item_info_db.shifu_bid
                    attend_info.user_bid = self._user_info.user_id
                    attend_info.status = LEARN_STATUS_NOT_STARTED
                    attend_info.progress_record_bid = generate_id(self.app)
                    attend_info.block_position = 0
                    db.session.add(attend_info)
                    db.session.flush()
                    break
        return attend_info

    # outline is a leaf when has block item as children
    # outline is a node when has outline item as children
    # outline is a leaf when has no children
    def _is_leaf_outline_item(self, outline_item_info: ShifuOutlineItemDto) -> bool:
        if outline_item_info.children:
            if outline_item_info.children[0].type == "block":
                return True
            if outline_item_info.children[0].type == "outline":
                return False
        if outline_item_info.type == "outline":
            return True
        return False

    # get the outline items to start or complete
    def _get_next_outline_item(self) -> list[_OutlineUpate]:
        res = []
        q = queue.Queue()
        q.put(self._struct)
        outline_ids = []
        while not q.empty():
            item: HistoryItem = q.get()
            if item.type == "outline":
                outline_ids.append(item.bid)
            if item.children:
                for child in item.children:
                    q.put(child)
        outline_item_info_db: list[tuple[str, bool]] = (
            db.session.query(
                self._outline_model.outline_item_bid,
                self._outline_model.hidden,
            )
            .filter(
                self._outline_model.outline_item_bid.in_(outline_ids),
                self._outline_model.deleted == 0,
            )
            .all()
        )
        outline_item_hidden_map: dict[str, bool] = {
            o[0]: o[1] for o in outline_item_info_db
        }

        def _mark_sub_node_completed(
            outline_item_info: HistoryItem, res: list[_OutlineUpate]
        ):
            q = queue.Queue()
            q.put(self._struct)
            if self._is_leaf_outline_item(outline_item_info):
                res.append(
                    _OutlineUpate(_OutlineUpateType.LEAF_COMPLETED, outline_item_info)
                )
            else:
                res.append(
                    _OutlineUpate(_OutlineUpateType.NODE_COMPLETED, outline_item_info)
                )
            while not q.empty():
                item: HistoryItem = q.get()
                if item.children and outline_item_info.bid in [
                    child.bid for child in item.children
                ]:
                    index = [child.bid for child in item.children].index(
                        outline_item_info.bid
                    )
                    while index < len(item.children) - 1:
                        # not sub node
                        current_node = item.children[index + 1]
                        if outline_item_hidden_map.get(current_node.bid, True):
                            index += 1
                            continue
                        while (
                            current_node.children
                            and current_node.children[0].type == "outline"
                        ):
                            res.append(
                                _OutlineUpate(
                                    _OutlineUpateType.NODE_START, current_node
                                )
                            )
                            current_node = current_node.children[0]
                        res.append(
                            _OutlineUpate(_OutlineUpateType.LEAF_START, current_node)
                        )
                        return
                    if index == len(item.children) - 1 and item.type == "outline":
                        _mark_sub_node_completed(item, res)
                if item.children and item.children[0].type == "outline":
                    for child in item.children:
                        q.put(child)

        def _mark_sub_node_start(
            outline_item_info: HistoryItem, res: list[_OutlineUpate]
        ):
            path = find_node_with_parents(self._struct, outline_item_info.bid)
            for item in path:
                if item.type == "outline":
                    if item.children and item.children[0].type == "outline":
                        res.append(_OutlineUpate(_OutlineUpateType.NODE_START, item))
                    else:
                        res.append(_OutlineUpate(_OutlineUpateType.LEAF_START, item))

        if self._current_attend.block_position >= len(
            self._current_outline_item.children
        ):
            _mark_sub_node_completed(self._current_outline_item, res)
        if self._current_attend.status == LEARN_STATUS_NOT_STARTED:
            _mark_sub_node_start(self._current_outline_item, res)
        return res

    def _get_current_outline_item(self) -> ShifuOutlineItemDto:
        return self._current_outline_item

    def _render_outline_updates(
        self, outline_updates: list[_OutlineUpate], new_chapter: bool = False
    ) -> Generator[str, None, None]:
        attend_status_values = get_learn_status_values()
        shif_bids = [o.outline_item_info.bid for o in outline_updates]
        outline_item_info_db: Union[DraftOutlineItem, PublishedOutlineItem] = (
            self._outline_model.query.filter(
                self._outline_model.outline_item_bid.in_(shif_bids),
                self._outline_model.deleted == 0,
            ).all()
        )
        outline_item_info_map: dict[
            str, Union[DraftOutlineItem, PublishedOutlineItem]
        ] = {o.outline_item_bid: o for o in outline_item_info_db}
        for update in outline_updates:
            self.app.logger.info(
                f"outline update: {update.type} {update.outline_item_info.bid}"
            )
            outline_item_info = outline_item_info_map.get(
                update.outline_item_info.bid, None
            )
            if not outline_item_info:
                continue
            if outline_item_info.hidden:
                continue
            outline_item_info_args = {
                "lesson_no": outline_item_info.position,
                "lesson_name": outline_item_info.title,
            }

            if update.type == _OutlineUpateType.LEAF_START:
                self._current_outline_item = update.outline_item_info
                if (
                    self._current_attend.outline_item_bid
                    == update.outline_item_info.bid
                ):
                    self._current_attend.status = LEARN_STATUS_IN_PROGRESS
                    self._current_attend.outline_item_updated = 0
                    self._current_attend.block_position = 0
                    db.session.flush()
                    continue
                self._current_attend = self._get_current_attend(
                    self._current_outline_item
                )
                self.app.logger.info(
                    f"current_attend: {self._current_attend.outline_item_bid} {self._current_attend.status} {self._current_attend.block_position}"
                )

                if (
                    self._current_attend.status == LEARN_STATUS_NOT_STARTED
                    or self._current_attend.status == LEARN_STATUS_LOCKED
                ):
                    self._current_attend.status = LEARN_STATUS_IN_PROGRESS
                    self._current_attend.block_position = 0
                    db.session.flush()
                    yield make_script_dto(
                        "lesson_update",
                        {
                            "lesson_id": update.outline_item_info.bid,
                            "status_value": LEARN_STATUS_NOT_STARTED,
                            "status": attend_status_values[LEARN_STATUS_NOT_STARTED],
                            **outline_item_info_args,
                        },
                        "",
                    )
                    yield make_script_dto(
                        "lesson_update",
                        {
                            "lesson_id": update.outline_item_info.bid,
                            "status_value": LEARN_STATUS_IN_PROGRESS,
                            "status": attend_status_values[LEARN_STATUS_IN_PROGRESS],
                            **outline_item_info_args,
                        },
                        "",
                    )
            elif update.type == _OutlineUpateType.LEAF_COMPLETED:
                current_attend = self._get_current_attend(update.outline_item_info)
                current_attend.status = LEARN_STATUS_COMPLETED
                db.session.flush()
                yield make_script_dto(
                    "lesson_update",
                    {
                        "lesson_id": update.outline_item_info.bid,
                        "status_value": LEARN_STATUS_COMPLETED,
                        "status": attend_status_values[LEARN_STATUS_COMPLETED],
                        **outline_item_info_args,
                    },
                    "",
                )
            elif update.type == _OutlineUpateType.NODE_START:
                if new_chapter:
                    status = LEARN_STATUS_NOT_STARTED
                else:
                    status = LEARN_STATUS_IN_PROGRESS
                current_attend = self._get_current_attend(update.outline_item_info)
                current_attend.status = LEARN_STATUS_IN_PROGRESS
                current_attend.block_position = 0
                db.session.flush()

                yield make_script_dto(
                    "chapter_update",
                    {
                        "lesson_id": update.outline_item_info.bid,
                        "status_value": status,
                        "status": attend_status_values[status],
                        **outline_item_info_args,
                    },
                    "",
                )

                yield make_script_dto(
                    "next_chapter",
                    {
                        "lesson_id": update.outline_item_info.bid,
                        "status_value": status,
                        "status": attend_status_values[status],
                        **outline_item_info_args,
                    },
                    "",
                )
            elif update.type == _OutlineUpateType.NODE_COMPLETED:
                current_attend = self._get_current_attend(update.outline_item_info)
                current_attend.status = LEARN_STATUS_COMPLETED
                db.session.flush()
                yield make_script_dto(
                    "chapter_update",
                    {
                        "lesson_id": update.outline_item_info.bid,
                        "status_value": LEARN_STATUS_COMPLETED,
                        "status": attend_status_values[LEARN_STATUS_COMPLETED],
                        **outline_item_info_args,
                    },
                    "",
                )

    def _get_default_llm_settings(self) -> LLMSettings:
        return LLMSettings(
            model=self.app.config.get("DEFAULT_LLM_MODEL"),
            temperature=float(self.app.config.get("DEFAULT_LLM_TEMPERATURE")),
        )

    def set_input(self, input: str, input_type: str):
        self._trace_args["input"] = input
        self._trace_args["input_type"] = input_type
        self._input_type = input_type
        self._input = input
        self.app.logger.info(f"set_input {input} {input_type}")

    def _get_goto_attend(
        self,
        block_dto: BlockDTO,
        user_info: User,
        outline_item_info: ShifuOutlineItemDto,
    ) -> LearnProgressRecord:
        goto: GotoDTO = block_dto.block_content
        variable_id = block_dto.variable_bids[0] if block_dto.variable_bids else ""
        if not variable_id:
            return None
        user_variable = get_user_variable_by_variable_id(
            self.app, user_info.user_id, variable_id
        )

        if not user_variable:
            return None
        destination_condition: GotoConditionDTO = None
        for condition in goto.conditions:
            if condition.value == user_variable:
                destination_condition = condition
                break
        if not destination_condition:
            return None

        goto_attend = LearnProgressRecord.query.filter(
            LearnProgressRecord.user_bid == user_info.user_id,
            LearnProgressRecord.shifu_bid == outline_item_info.shifu_bid,
            LearnProgressRecord.outline_item_bid
            == destination_condition.destination_bid,
            LearnProgressRecord.status.notin_(
                [LEARN_STATUS_RESET, LEARN_STATUS_COMPLETED]
            ),
        ).first()
        if not goto_attend:
            goto_attend = LearnProgressRecord()
            goto_attend.user_bid = user_info.user_id
            goto_attend.shifu_bid = outline_item_info.shifu_bid
            goto_attend.outline_item_bid = destination_condition.destination_bid
            goto_attend.progress_record_bid = generate_id(self.app)
            goto_attend.status = LEARN_STATUS_IN_PROGRESS
            goto_attend.block_position = 0
            db.session.add(goto_attend)
            db.session.flush()
        return goto_attend

    def _get_outline_struct(self, outline_item_id: str) -> HistoryItem:
        q = queue.Queue()
        q.put(self._struct)
        outline_struct = None
        while not q.empty():
            item = q.get()
            if item.bid == outline_item_id:
                outline_struct = item
                break
            if item.children:
                for child in item.children:
                    q.put(child)
        return outline_struct

    def _get_run_script_info(self, attend: LearnProgressRecord) -> RunScriptInfo:
        outline_item_id = attend.outline_item_bid
        outline_item_info: ShifuOutlineItemDto = get_outline_item_dto(
            self.app, outline_item_id, self._preview_mode
        )

        outline_struct = self._get_outline_struct(outline_item_id)

        if attend.block_position >= len(outline_struct.children):
            return None
        block_id = outline_struct.children[attend.block_position].id
        block_info: Union[DraftBlock, PublishedBlock] = self._block_model.query.filter(
            self._block_model.id == block_id,
        ).first()
        if not block_info:
            raise_error("server.lesson.lessonNotFoundInCourse")
        block_dto = generate_block_dto_from_model_internal(
            block_info, convert_html=False
        )
        if block_dto.type == "goto":
            goto_attend = self._get_goto_attend(
                block_dto, self._user_info, outline_item_info
            )
            goto_outline_struct = self._get_outline_struct(goto_attend.outline_item_bid)
            if goto_attend.block_position >= len(goto_outline_struct.children):
                attend.block_position = attend.block_position + 1
                goto_attend.status = LEARN_STATUS_COMPLETED
                db.session.flush()
                ret = self._get_run_script_info(attend)
                if ret:
                    return ret
            return self._get_run_script_info(goto_attend)
        return RunScriptInfo(
            attend=attend,
            outline_item_info=outline_item_info,
            block_dto=block_dto,
        )

    def _get_run_script_info_by_block_id(self, block_id: str) -> RunScriptInfo:
        block_info: Union[DraftBlock, PublishedBlock] = (
            self._block_model.query.filter(
                self._block_model.block_bid == block_id,
            )
            .order_by(self._block_model.id.desc())
            .first()
        )
        if not block_info:
            raise_error("server.lesson.lessonNotFoundInCourse")
        block_dto = generate_block_dto_from_model_internal(
            block_info, convert_html=False
        )
        outline_item_info: ShifuOutlineItemDto = get_outline_item_dto(
            self.app, block_info.outline_item_bid, self._preview_mode
        )
        attend = LearnProgressRecord.query.filter(
            LearnProgressRecord.user_bid == self._user_info.user_id,
            LearnProgressRecord.shifu_bid == outline_item_info.shifu_bid,
            LearnProgressRecord.outline_item_bid == outline_item_info.bid,
            LearnProgressRecord.status != LEARN_STATUS_RESET,
        ).first()
        return RunScriptInfo(
            attend=attend,
            outline_item_info=outline_item_info,
            block_dto=block_dto,
        )

    def run(self, app: Flask) -> Generator[str, None, None]:
        try:
            yield make_script_dto("teacher_avatar", self._shifu_info.avatar, "")
            if not self._current_attend:
                self._current_attend = self._get_current_attend(self._outline_item_info)
            self.app.logger.info(
                f"current_attend: {self._current_attend.progress_record_bid} {self._current_attend.block_position}"
            )
            self._trace_args["session_id"] = self._current_attend.progress_record_bid
            outline_updates = self._get_next_outline_item()
            if len(outline_updates) > 0:
                yield from self._render_outline_updates(
                    outline_updates, new_chapter=False
                )
                db.session.flush()
                if self._current_attend.status != LEARN_STATUS_IN_PROGRESS:
                    self._can_continue = False
                    return
            run_script_info: RunScriptInfo = self._get_run_script_info(
                self._current_attend
            )
            if run_script_info and self._run_type == RunType.INPUT:
                res = handle_block_input(
                    app=app,
                    user_info=self._user_info,
                    attend_id=run_script_info.attend.progress_record_bid,
                    input_type=self._input_type,
                    input=self._input,
                    outline_item_info=self._outline_item_info,
                    block_dto=run_script_info.block_dto,
                    trace_args=self._trace_args,
                    trace=self._trace,
                    is_preview=self._preview_mode,
                )
                if res:
                    yield from res
                self._can_continue = True
                if (
                    run_script_info.block_dto.type != "content"
                    and self._input_type != "ask"
                ):
                    run_script_info.attend.block_position += 1
                run_script_info.attend.status = LEARN_STATUS_IN_PROGRESS
                self._input_type = "continue"
                self._run_type = RunType.OUTPUT
                db.session.flush()
            elif run_script_info:
                continue_check = check_block_continue(
                    app=app,
                    user_info=self._user_info,
                    attend_id=run_script_info.attend.progress_record_bid,
                    outline_item_info=self._outline_item_info,
                    block_dto=run_script_info.block_dto,
                    trace_args=self._trace_args,
                    trace=self._trace,
                    is_preview=self._preview_mode,
                )
                if run_script_info.block_dto.type == "content" or not continue_check:
                    res = handle_block_output(
                        app=app,
                        user_info=self._user_info,
                        attend_id=run_script_info.attend.progress_record_bid,
                        outline_item_info=self._outline_item_info,
                        block_dto=run_script_info.block_dto,
                        trace_args=self._trace_args,
                        trace=self._trace,
                        is_preview=self._preview_mode,
                    )
                    if res:
                        yield from res
                self._current_attend.status = LEARN_STATUS_IN_PROGRESS
                self._input_type = "continue"
                self._run_type = RunType.OUTPUT
                app.logger.info(f"output block type: {run_script_info.block_dto.type}")
                self._can_continue = continue_check
                if self._can_continue:
                    run_script_info.attend.block_position += 1
                db.session.flush()
            outline_updates = self._get_next_outline_item()
            if len(outline_updates) > 0:
                yield from self._render_outline_updates(
                    outline_updates, new_chapter=True
                )
                self._can_continue = False
                db.session.flush()
            self._trace.update(**self._trace_args)
        except PaidException as e:
            self.app.logger.info(f"PaidException: {e}")
            self._can_continue = False
            yield from handle_block_output(
                app=app,
                user_info=self._user_info,
                attend_id="",
                outline_item_info=self._outline_item_info,
                block_dto=BlockDTO(
                    bid="",
                    block_content=PaymentDTO(
                        label={"lang": {}},
                    ),
                    variable_bids=[],
                    resource_bids=[],
                ),
                trace_args=self._trace_args,
                trace=self._trace,
                is_preview=self._preview_mode,
            )

    def has_next(self) -> bool:
        self.app.logger.info(f"has_next {self._can_continue}")
        return self._can_continue

    def get_system_prompt(self, outline_item_info: ShifuOutlineItemDto) -> str:
        path = find_node_with_parents(self._struct, outline_item_info.bid)
        path = list(reversed(path))
        outline_ids = [item.id for item in path if item.type == "outline"]
        shifu_ids = [item.id for item in path if item.type == "shifu"]
        outline_item_info_db: Union[DraftOutlineItem, PublishedOutlineItem] = (
            self._outline_model.query.filter(
                self._outline_model.id.in_(outline_ids),
                self._outline_model.deleted == 0,
            ).all()
        )
        outline_item_info_map: dict[
            str, Union[DraftOutlineItem, PublishedOutlineItem]
        ] = {o.id: o for o in outline_item_info_db}
        for id in outline_ids:
            outline_item_info = outline_item_info_map.get(id, None)
            if outline_item_info and outline_item_info.llm_system_prompt:
                return outline_item_info.llm_system_prompt
        shifu_info_db: Union[DraftShifu, PublishedShifu] = (
            self._shifu_model.query.filter(
                self._shifu_model.id.in_(shifu_ids),
                self._shifu_model.deleted == 0,
            ).first()
        )
        if shifu_info_db and shifu_info_db.llm_system_prompt:
            return shifu_info_db.llm_system_prompt
        return None

    def get_llm_settings(self, outline_item_info: ShifuOutlineItemDto) -> LLMSettings:
        path = find_node_with_parents(self._struct, outline_item_info.bid)
        path.reverse()
        outline_ids = [item.id for item in path if item.type == "outline"]
        shifu_ids = [item.id for item in path if item.type == "shifu"]
        outline_item_info_db: Union[DraftOutlineItem, PublishedOutlineItem] = (
            self._outline_model.query.filter(
                self._outline_model.id.in_(outline_ids),
                self._outline_model.deleted == 0,
            ).all()
        )
        outline_item_info_map = {o.id: o for o in outline_item_info_db}
        for id in outline_ids:
            outline_item_info = outline_item_info_map.get(id, None)
            if outline_item_info and outline_item_info.llm:
                return LLMSettings(
                    model=outline_item_info.llm,
                    temperature=outline_item_info.llm_temperature,
                )
        shifu_info_db: Union[DraftShifu, PublishedShifu] = (
            self._shifu_model.query.filter(
                self._shifu_model.id.in_(shifu_ids),
                self._shifu_model.deleted == 0,
            ).first()
        )
        if shifu_info_db and shifu_info_db.llm:
            return LLMSettings(
                model=shifu_info_db.llm, temperature=shifu_info_db.llm_temperature
            )
        return self._get_default_llm_settings()

    def reload(self, app: Flask, script_id: str):
        yield make_script_dto("teacher_avatar", self._shifu_info.avatar, "")
        run_script_info: RunScriptInfo = self._get_run_script_info_by_block_id(
            script_id
        )
        LearnGeneratedBlock.query.filter(
            LearnGeneratedBlock.progress_record_bid
            == run_script_info.attend.progress_record_bid,
            LearnGeneratedBlock.block_bid == script_id,
            LearnGeneratedBlock.role == ROLE_TEACHER,
            LearnGeneratedBlock.status == 1,
        ).update(
            {
                LearnGeneratedBlock.status: 0,
            }
        )
        res = handle_block_output(
            app=app,
            user_info=self._user_info,
            attend_id=run_script_info.attend.progress_record_bid,
            outline_item_info=run_script_info.outline_item_info,
            block_dto=run_script_info.block_dto,
            trace_args=self._trace_args,
            trace=self._trace,
            is_preview=self._preview_mode,
        )
        if res:
            yield from res
        self._can_continue = False
        db.session.flush()
