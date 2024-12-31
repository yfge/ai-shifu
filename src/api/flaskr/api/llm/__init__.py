from typing import Generator
from .ernie import get_ernie_response, get_erine_models, chat_ernie
from .glm import get_zhipu_models, invoke_glm
import openai
from flask import Flask
from langfuse.client import StatefulSpanClient
from langfuse.model import ModelUsage

from openai.types.chat import ChatCompletionStreamOptionsParam
from openai.types.shared_params import ResponseFormatJSONObject
from flask import current_app

from flaskr.common.config import get_config
from flaskr.service.common.models import raise_error_with_args


openai_enabled = False


if get_config("OPENAI_API_KEY"):
    openai_enabled = True
    openai_client = openai.Client(
        api_key=get_config("OPENAI_API_KEY"),
        base_url=get_config("OPENAI_BASE_URL", "https://api.openai.com/v1"),
    )
else:
    current_app.logger.warning("OPENAI_API_KEY not configured")
    openai_client = None

deepseek_enabled = False
if get_config("DEEPSEEK_API_KEY"):
    deepseek_enabled = True
    deepseek_client = openai.Client(
        api_key=get_config("DEEPSEEK_API_KEY"),
        base_url=get_config("DEEPSEEK_API_URL", "https://api.deepseek.com"),
    )
    DEEP_SEEK_MODELS = [i.id for i in deepseek_client.models.list().data]
else:
    current_app.logger.warning("DEEPSEEK_API_KEY not configured")
    deepseek_client = None

qwen_enabled = False
if get_config("QWEN_API_KEY"):
    qwen_enabled = True
    qwen_client = openai.Client(
        api_key=get_config("QWEN_API_KEY"), base_url=get_config("QWEN_API_URL")
    )
    QWEN_MODELS = [i.id for i in qwen_client.models.list().data]
else:
    current_app.logger.warning("QWEN_API_KEY not configured")
    qwen_client = None

ernie_enabled = False
if get_config("ERNIE_API_ID") and get_config("ERNIE_API_SECRET"):
    ernie_enabled = True
else:
    current_app.logger.warning("ERNIE_API_ID and ERNIE_API_SECRET not configured")

glm_enabled = False
if get_config("GLM_API_KEY"):
    glm_enabled = True
else:
    current_app.logger.warning("GLM_API_KEY not configured")

if openai_enabled or deepseek_enabled or qwen_enabled or ernie_enabled or glm_enabled:
    pass
else:
    current_app.logger.warning("No LLM Configured")

try:
    if openai_client:
        OPENAI_MODELS = [
            i.id for i in openai_client.models.list().data if i.id.startswith("gpt")
        ]
    else:
        OPENAI_MODELS = []
except Exception as e:
    current_app.logger.warning(f"get openai models error: {e}")
    OPENAI_MODELS = []
ERNIE_MODELS = get_erine_models(Flask(__name__))
GLM_MODELS = get_zhipu_models(Flask(__name__))


class LLMStreamaUsage:
    def __init__(self, prompt_tokens, completion_tokens, total_tokens):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens


class LLMStreamResponse:
    def __init__(self, id, is_end, is_truncated, result, finish_reason, usage):
        self.id = id

        self.is_end = is_end
        self.is_truncated = is_truncated
        self.result = result
        self.finish_reason = finish_reason
        self.usage = LLMStreamaUsage(**usage) if usage else None


def invoke_llm(
    app: Flask,
    span: StatefulSpanClient,
    model: str,
    message: str,
    system: str = None,
    json: bool = False,
    **kwargs,
) -> Generator[LLMStreamResponse, None, None]:
    app.logger.info(
        f"invoke_llm [{model}] {message} ,system:{system} ,json:{json} ,kwargs:{kwargs}"
    )
    kwargs.update({"stream": True})
    model = model.strip()
    generation_input = []
    if system:
        generation_input.append({"role": "system", "content": system})
    generation_input.append({"role": "user", "content": message})
    generation = span.generation(model=model, input=generation_input)
    response_text = ""
    usage = None
    if (
        model in OPENAI_MODELS
        or model.startswith("gpt")
        or model in QWEN_MODELS
        or model in DEEP_SEEK_MODELS
    ):
        if model in OPENAI_MODELS or model.startswith("gpt"):
            client = openai_client
            if not client:
                raise_error_with_args(
                    "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                    model=model,
                    config_var="OPENAI_API_KEY,OPENAI_BASE_URL",
                )
        elif model in QWEN_MODELS:
            client = qwen_client
            if not client:
                raise_error_with_args(
                    "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                    model=model,
                    config_var="QWEN_API_KEY,QWEN_API_URL",
                )
        elif model in DEEP_SEEK_MODELS:
            client = deepseek_client
            if not client:
                raise_error_with_args(
                    "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                    model=model,
                    config_var="DEEPSEEK_API_KEY,DEEPSEEK_API_URL",
                )
        messages = []
        if system:
            messages.append({"content": system, "role": "system"})
        messages.append({"content": message, "role": "user"})
        if json:
            kwargs["response_format"] = ResponseFormatJSONObject(type="json_object")
        kwargs["temperature"] = float(kwargs.get("temperature", 0.8))
        kwargs["stream_options"] = ChatCompletionStreamOptionsParam(include_usage=True)
        response = client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )

        for res in response:
            if len(res.choices) and res.choices[0].delta.content:
                response_text += res.choices[0].delta.content
                yield LLMStreamResponse(
                    res.id,
                    True if res.choices[0].finish_reason else False,
                    False,
                    res.choices[0].delta.content,
                    res.choices[0].finish_reason,
                    None,
                )
            if res.usage:
                usage = ModelUsage(
                    unit="TOKENS",
                    input=res.usage.prompt_tokens,
                    output=res.usage.completion_tokens,
                    total=res.usage.total_tokens,
                )
    elif model in ERNIE_MODELS:
        if not ernie_enabled:
            raise_error_with_args(
                "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                model=model,
                config_var="ERNIE_API_ID,ERNIE_API_SECRET",
            )
        if system:
            kwargs.update({"system": system})
        if json:
            kwargs["response_format"] = "json_object"
        if kwargs.get("temperature", None) is not None:
            kwargs["temperature"] = float(kwargs.get("temperature", 0.8))
        response = get_ernie_response(app, model, message, **kwargs)
        for res in response:
            response_text += res.result
            if res.usage:
                usage = ModelUsage(
                    unit="TOKENS",
                    input=res.usage.prompt_tokens,
                    output=res.usage.completion_tokens,
                    total=res.usage.total_tokens,
                )
            yield LLMStreamResponse(
                res.id,
                res.is_end,
                res.is_truncated,
                res.result,
                res.finish_reason,
                res.usage.__dict__,
            )
    elif model.lower() in GLM_MODELS:
        if not glm_enabled:
            raise_error_with_args(
                "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                model=model,
                config_var="GLM_API_KEY",
            )
        if kwargs.get("temperature", None) is not None:
            kwargs["temperature"] = str(kwargs["temperature"])
        messages = []
        if system:
            messages.append({"content": system, "role": "system"})
        messages.append({"content": message, "role": "user"})
        response = invoke_glm(app, model.lower(), messages, **kwargs)
        for res in response:
            response_text += res.choices[0].delta.content
            if res.usage:
                usage = ModelUsage(
                    unit="TOKENS",
                    input=res.usage.prompt_tokens,
                    output=res.usage.completion_tokens,
                    total=res.usage.total_tokens,
                )
            yield LLMStreamResponse(
                res.id,
                True if res.choices[0].finish_reason else False,
                False,
                res.choices[0].delta.content,
                res.choices[0].finish_reason,
                None,
            )
    else:
        raise_error_with_args(
            "LLM.MODEL_NOT_SUPPORTED",
            model=model,
        )

    app.logger.info("invoke_llm response: {response_text} ")
    app.logger.info("invoke_llm usage: " + usage.__str__())
    generation.end(
        input=generation_input, output=response_text, usage=usage, metadata=kwargs
    )
    span.end(output=response_text)


def chat_llm(
    app: Flask,
    span: StatefulSpanClient,
    model: str,
    messages: list,
    json: bool = False,
    **kwargs,
) -> Generator[LLMStreamResponse, None, None]:
    app.logger.info(f"chat_llm [{model}] {messages} ,json:{json} ,kwargs:{kwargs}")
    kwargs.update({"stream": True})
    model = model.strip()
    generation_input = messages
    generation = span.generation(
        model=model, input=generation_input, name="user_follow_ask"
    )
    response_text = ""
    usage = None
    if kwargs.get("temperature", None) is not None:
        kwargs["temperature"] = float(kwargs.get("temperature", 0.8))
    if (
        model in OPENAI_MODELS
        or model.startswith("gpt")
        or model in QWEN_MODELS
        or model in DEEP_SEEK_MODELS
    ):
        if model in OPENAI_MODELS or model.startswith("gpt"):
            client = openai_client
            if not client:
                raise_error_with_args(
                    "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                    model=model,
                    config_var="OPENAI_API_KEY,OPENAI_BASE_URL",
                )
        elif model in QWEN_MODELS:
            client = qwen_client
            if not client:
                raise_error_with_args(
                    "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                    model=model,
                    config_var="QWEN_API_KEY,QWEN_API_URL",
                )
        elif model in DEEP_SEEK_MODELS:
            client = deepseek_client
            if not client:
                raise_error_with_args(
                    "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                    model=model,
                    config_var="DEEPSEEK_API_KEY,DEEPSEEK_API_URL",
                )
        response = client.chat.completions.create(
            model=model, messages=messages, **kwargs
        )
        for res in response:
            if len(res.choices) and res.choices[0].delta.content:
                response_text += res.choices[0].delta.content
                yield LLMStreamResponse(
                    res.id,
                    True if res.choices[0].finish_reason else False,
                    False,
                    res.choices[0].delta.content,
                    res.choices[0].finish_reason,
                    None,
                )
            if res.usage:
                usage = ModelUsage(
                    unit="TOKENS",
                    input=res.usage.prompt_tokens,
                    output=res.usage.completion_tokens,
                    total=res.usage.total_tokens,
                )
    elif model in ERNIE_MODELS:
        if not ernie_enabled:
            raise_error_with_args(
                "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                model=model,
                config_var="ERNIE_API_ID,ERNIE_API_SECRET",
            )
        if kwargs.get("temperature", None) is not None:
            kwargs["temperature"] = float(kwargs.get("temperature", 0.8))
        response = chat_ernie(app, model, messages, **kwargs)
        for res in response:
            response_text += res.result
            if res.usage:
                usage = ModelUsage(
                    unit="TOKENS",
                    input=res.usage.prompt_tokens,
                    output=res.usage.completion_tokens,
                    total=res.usage.total_tokens,
                )
            yield LLMStreamResponse(
                res.id,
                res.is_end,
                res.is_truncated,
                res.result,
                res.finish_reason,
                res.usage.__dict__,
            )
    elif model.lower() in GLM_MODELS:
        if not glm_enabled:
            raise_error_with_args(
                "LLM.SPECIFIED_LLM_NOT_CONFIGURED",
                model=model,
                config_var="GLM_API_KEY",
            )
        if kwargs.get("temperature", None) is not None:
            kwargs["temperature"] = str(kwargs["temperature"])
        response = invoke_glm(app, model.lower(), messages, **kwargs)
        for res in response:
            response_text += res.choices[0].delta.content
            if res.usage:
                usage = ModelUsage(
                    unit="TOKENS",
                    input=res.usage.prompt_tokens,
                    output=res.usage.completion_tokens,
                    total=res.usage.total_tokens,
                )
            yield LLMStreamResponse(
                res.id,
                True if res.choices[0].finish_reason else False,
                False,
                res.choices[0].delta.content,
                res.choices[0].finish_reason,
                None,
            )

    else:
        raise_error_with_args(
            "LLM.MODEL_NOT_SUPPORTED",
            model=model,
        )

    app.logger.info("invoke_llm response: {response_text} ")
    app.logger.info("invoke_llm usage: " + usage.__str__())
    generation.end(
        input=generation_input, output=response_text, usage=usage, metadata=kwargs
    )


def get_current_models(app: Flask) -> list[str]:
    return OPENAI_MODELS + ERNIE_MODELS + GLM_MODELS + QWEN_MODELS + DEEP_SEEK_MODELS
