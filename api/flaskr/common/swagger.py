
from dataclasses import fields
import typing
from marshmallow_dataclass import dataclass
from marshmallow import Schema, fields
swagger_config = {
    "openapi": "3.0.2",
    "info": {
        "title": "枕头编程-API 文档",
        "version": "1.0.0"
    },
    'optional_fields': ['components'],
    "components": {
        "schemas": {
            # "AILessonAttendDTO": AILessonAttendDTOSchema,
            # "AICourseDTO": AICourseDTOSchema
        }
    },
    # "definitions": {},
    
     "specs": [
        {
            "endpoint": 'apispec_1',
            "route": '/apispec_1.json',
          #  "rule_filter": lambda rule: True,  # all in
          #  "model_filter": lambda tag: True,  # all in
        }
    ],
    # # "host": "localhost:5000",  # 指定主机
    # "basePath": "/",  # 指定基础路径
    # "schemes": [
    #     "http"
    # ],
}



def get_field_schema(typ):
    field_schema = {}
    origin = typing.get_origin(typ)
    args = typing.get_args(typ)

    # 基础类型处理
    if typ in (str, int, float, bool):
        field_schema['type'] = typ.__name__
    # 处理列表类型
    elif origin == list:
        item_type = args[0]
        field_schema['type'] = 'array'
        field_schema['items'] = get_field_schema(item_type)
    # 处理字典类型
    elif origin == dict:
        key_type, value_type = args
        field_schema['type'] = 'object'
        field_schema['additionalProperties'] = get_field_schema(value_type)
    # 处理复杂类型，使用引用
    elif hasattr(typ, '__annotations__'):
        field_schema['$ref'] = f'#/components/schemas/{typ.__name__}'
    else:
        field_schema['type'] = 'object'

    return field_schema

def register_schema_to_swagger(cls):
    if swagger_config['components']['schemas'].get(cls.__name__, None):
        return swagger_config['components']['schemas'].get(cls.__name__)
    
    properties = {}
    required = []

    for name, typ in cls.__annotations__.items():
        field_schema = get_field_schema(typ)
        properties[name] = field_schema
        required.append(name)

    schema = {
        'type': 'object',
        'properties': properties,
        'required': required
    }
    swagger_config['components']['schemas'][cls.__name__] = schema

    # return schema
    
    # return schema_cls
    return cls