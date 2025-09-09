from flaskr.service.shifu.dtos import (
    BlockDTO,
    LabelDTO,
    ContentDTO,
    LoginDTO,
    PaymentDTO,
    OptionsDTO,
    InputDTO,
    BreakDTO,
    GotoDTO,
    CheckCodeDTO,
    PhoneDTO,
)
from flaskr.service.shifu.consts import (
    BLOCK_TYPE_CONTENT,
    BLOCK_TYPE_BREAK,
    BLOCK_TYPE_INPUT,
    BLOCK_TYPE_OPTIONS,
    BLOCK_TYPE_GOTO,
    BLOCK_TYPE_PAYMENT,
    BLOCK_TYPE_LOGIN,
    BLOCK_TYPE_PHONE,
    BLOCK_TYPE_CHECKCODE,
)
from flaskr.service.common import raise_error


def __get_label_markdown_flow(label: LabelDTO) -> str:
    """
    Get label markdown flow
    """
    if hasattr(label, "lang") and label.lang:
        return label.lang.get("zh-CN", "")
    return ""


def __convert_to_markdown_flow_action(label: LabelDTO, action: str) -> str:
    """
    Convert to markdown flow action
    """
    return f"?[{__get_label_markdown_flow(label)}//{action}]"


def __convert_login_to_markdown_flow(
    login: LoginDTO, variable_map: dict[str, str]
) -> str:
    """
    Convert login to markdown flow
    """
    # Handle case where login.label is a dict
    if isinstance(login.label, dict):
        label_dto = LabelDTO(lang=login.label)
    else:
        label_dto = login.label
    return __convert_to_markdown_flow_action(label_dto, "login")


def __convert_payment_to_markdown_flow(
    payment: PaymentDTO, variable_map: dict[str, str]
) -> str:
    """
    Convert payment to markdown flow
    """
    # Handle case where payment.label is a dict
    if isinstance(payment.label, dict):
        label_dto = LabelDTO(lang=payment.label)
    else:
        label_dto = payment.label
    return __convert_to_markdown_flow_action(label_dto, "payment")


def __convert_options_to_markdown_flow(
    options: OptionsDTO, variable_map: dict[str, str]
) -> str:
    """
    Convert options to markdown flow
    """
    variable_name = variable_map.get(options.result_variable_bid, "")
    option_strings = []
    for option in options.options:
        if isinstance(option, dict):
            label_text = option.get("label", {}).get("zh-CN", "")
            value = option.get("value", "")
        else:
            label_text = __get_label_markdown_flow(option.label)
            value = option.value
        option_strings.append(f"{label_text}//{value}")

    options_str = "|".join(option_strings)
    return f"?[%{{{{{variable_name}}}}}{options_str}]"


def __convert_input_to_markdown_flow(
    input: InputDTO, variable_map: dict[str, str]
) -> str:
    """
    Convert input to markdown flow
    """
    variable_name = variable_map.get(input.result_variable_bid, "")
    placeholder = __get_label_markdown_flow(input.placeholder)
    # Input should return action format, not variable format
    return f"?[%{{{{{variable_name}}}}}...{placeholder}]"


def __convert_break_to_markdown_flow(
    break_dto: BreakDTO, variable_map: dict[str, str]
) -> str:
    """
    Convert break to markdown flow
    """
    if hasattr(break_dto, "label") and break_dto.label:
        return __convert_to_markdown_flow_action(break_dto.label, "break")
    else:
        # Create a default label for break
        label_dto = LabelDTO(lang={"zh-CN": "休息"})
        return __convert_to_markdown_flow_action(label_dto, "break")


def __convert_content_to_markdown_flow(
    content: ContentDTO, variable_map: dict[str, str]
) -> str:
    """
    Convert content to markdown flow
    """
    if content.content is None:
        content_text = ""
    else:
        content_text = content.content

    if content.llm_enabled:
        return content_text
    else:
        return f"==={content_text}==="


def __convert_goto_to_markdown_flow(goto: GotoDTO, variable_map: dict[str, str]) -> str:
    """
    Convert goto to markdown flow
    """
    if hasattr(goto, "label") and goto.label:
        return __convert_to_markdown_flow_action(goto.label, "goto")
    else:
        # Create a default label for goto
        label_dto = LabelDTO(lang={"zh-CN": "跳转"})
        return __convert_to_markdown_flow_action(label_dto, "goto")


def __convert_phone_to_markdown_flow(
    phone: PhoneDTO, variable_map: dict[str, str]
) -> str:
    """
    Convert phone to markdown flow
    """
    if hasattr(phone, "label") and phone.label:
        return __convert_to_markdown_flow_action(phone.label, "phone")
    else:
        # Create a default label for phone
        label_dto = LabelDTO(lang={"zh-CN": "手机验证"})
        return __convert_to_markdown_flow_action(label_dto, "phone")


def __convert_checkcode_to_markdown_flow(
    checkcode: CheckCodeDTO, variable_map: dict[str, str]
) -> str:
    """
    Convert checkcode to markdown flow
    """
    if hasattr(checkcode, "label") and checkcode.label:
        return __convert_to_markdown_flow_action(checkcode.label, "checkcode")
    else:
        # Create a default label for checkcode
        label_dto = LabelDTO(lang={"zh-CN": "验证码"})
        return __convert_to_markdown_flow_action(label_dto, "checkcode")


def convert_block_to_markdown_flow(
    block: BlockDTO, variable_map: dict[str, str]
) -> str:
    """
    Convert block to markdown flow
    """
    # Determine block type from content if not present
    if hasattr(block, "type") and block.type:
        block_type = block.type
    else:
        # Infer type from content class name
        content_class = block.block_content.__class__.__name__
        block_type = content_class.replace("DTO", "").lower()

    convert_func_map = {
        BLOCK_TYPE_CONTENT: __convert_content_to_markdown_flow,
        BLOCK_TYPE_BREAK: __convert_break_to_markdown_flow,
        BLOCK_TYPE_INPUT: __convert_input_to_markdown_flow,
        BLOCK_TYPE_OPTIONS: __convert_options_to_markdown_flow,
        BLOCK_TYPE_GOTO: __convert_goto_to_markdown_flow,
        BLOCK_TYPE_PAYMENT: __convert_payment_to_markdown_flow,
        BLOCK_TYPE_LOGIN: __convert_login_to_markdown_flow,
        BLOCK_TYPE_PHONE: __convert_phone_to_markdown_flow,
        BLOCK_TYPE_CHECKCODE: __convert_checkcode_to_markdown_flow,
    }

    convert_func = convert_func_map.get(block_type, None)
    if convert_func is None:
        raise_error(f"Invalid block type: {block_type}")
    ret = convert_func(block.block_content, variable_map)

    print(ret)
    return ret
