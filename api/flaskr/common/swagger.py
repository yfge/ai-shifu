
from dataclasses import fields
from marshmallow_dataclass import dataclass
from marshmallow import Schema, fields
swagger_config = {
    "openapi": "3.0.2",
    "info": {
        "title": "枕头编程-API 文档",
        "version": "1.0.0"
    },
    "components": {
        "schemas": {
            # "AILessonAttendDTO": AILessonAttendDTOSchema,
            # "AICourseDTO": AICourseDTOSchema
        }
    },
    
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

def register_schema_to_swagger(cls):
    if swagger_config['components']['schemas'].get(cls.__name__,None):
        return swagger_config['components']['schemas'].get(cls.__name__) 
    attrs = {}
    for name, typ in cls.__annotations__.items():
        if typ == str:
            field = fields.String(required=True)
        elif typ == int:
            field = fields.Integer(required=True)
        elif typ == float:
            field = fields.Float(required=True)
        elif typ == bool:
            field = fields.Boolean(required=True)
        elif typ == list:
            field = fields.List(fields.Raw(), required=True)
        elif isinstance(typ, type) and issubclass(typ, (list, dict)):
            if hasattr(typ, '__args__') and issubclass(typ.__args__[0], (list, dict)):
                nested_cls = typ.__args__[0]
                nested_schema = register_schema_to_swagger(nested_cls)
                field = fields.List(fields.Nested(nested_schema), required=True)
            else:
                field = fields.Raw(required=True)
        else:
            field = fields.Raw(required=True)
        attrs[name] = field
    schema_cls = type(cls.__name__ + 'Schema', (Schema,), attrs)
    swagger_config['components']['schemas'][cls.__name__] = schema_cls
    return schema_cls
    # return cls