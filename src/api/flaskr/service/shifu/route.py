from flask import Flask, request, current_app
from .funcs import (
    get_shifu_list,
    create_shifu,
    mark_or_unmark_favorite_shifu,
    publish_shifu,
    preview_shifu,
    save_shifu_detail,
    get_shifu_detail,
    upload_file,
    upload_url,
    get_video_info,
    shifu_permission_verification,
)
from .outline_funcs import (
    update_chapter_order,
    get_outline_tree,
)
from .unit_funcs import (
    create_unit,
    modify_unit,
    delete_unit,
    get_unit_by_id,
)
from .block_funcs import (
    get_block_list,
    save_block_list,
    add_block,
)
from flaskr.route.common import make_common_response
from flaskr.framework.plugin.inject import inject
from flaskr.service.common.models import raise_param_error, raise_error
from ..lesson.models import LESSON_TYPE_TRIAL
from functools import wraps
from enum import Enum


class ShifuPermission(Enum):
    VIEW = "view"
    EDIT = "edit"
    PUBLISH = "publish"


# Shifu permission verification decorator
# @ShifuTokenValidation(ShifuPermission.xxx)
class ShifuTokenValidation:
    def __init__(self, permission: ShifuPermission = ShifuPermission.VIEW):
        self.permission = permission

    def __call__(self, f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            token = request.cookies.get("token", None)
            if not token:
                token = request.args.get("token", None)
            if not token:
                token = request.headers.get("Token", None)
            if not token and request.method.upper() == "POST" and request.is_json:
                token = request.get_json().get("token", None)

            shifu_bid = request.view_args.get("shifu_bid", None)
            if not shifu_bid:
                shifu_bid = request.args.get("shifu_bid", None)
            if not shifu_bid and request.method.upper() == "POST" and request.is_json:
                shifu_bid = request.get_json().get("shifu_bid", None)

            if not token:
                raise_param_error("token is required")
            if not shifu_bid or not str(shifu_bid).strip():
                raise_param_error("shifu_bid is required")

            user_id = request.user.user_id
            app = current_app._get_current_object()
            has_permission = shifu_permission_verification(
                app, user_id, shifu_bid, self.permission.value
            )
            if not has_permission:
                raise_error("SHIFU.NO_PERMISSION")

            return f(*args, **kwargs)

        return decorated_function


@inject
def register_shifu_routes(app: Flask, path_prefix="/api/shifu"):
    app.logger.info(f"register shifu routes {path_prefix}")

    @app.route(path_prefix + "/shifus", methods=["GET"])
    def get_shifu_list_api():
        """
        get shifu list
        ---
        tags:
            - shifu
        parameters:
            - name: page_index
              type: integer
              required: true
            - name: page_size
              type: integer
              required: true
            - name: is_favorite
              type: boolean
              required: true
        responses:
            200:
                description: get shifu list success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: array
                                    items:
                                        $ref: "#/components/schemas/PageNationDTO"
        """
        user_id = request.user.user_id
        page_index = request.args.get("page_index", 1)
        page_size = request.args.get("page_size", 10)
        is_favorite = request.args.get("is_favorite", "False")
        is_favorite = True if is_favorite.lower() == "true" else False
        try:
            page_index = int(page_index)
            page_size = int(page_size)
        except ValueError:
            raise_param_error("page_index or page_size is not a number")

        if page_index < 0 or page_size < 1:
            raise_param_error("page_index or page_size is less than 0")
        app.logger.info(
            f"get shifu list, user_id: {user_id}, page_index: {page_index}, page_size: {page_size}, is_favorite: {is_favorite}"
        )
        return make_common_response(
            get_shifu_list(app, user_id, page_index, page_size, is_favorite)
        )

    @app.route(path_prefix + "/shifus", methods=["PUT"])
    def create_shifu_api():
        """
        create shifu
        ---
        tags:
            - shifu
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    name:
                        type: string
                        description: shifu name
                    description:
                        type: string
                        description: shifu description
                    avatar:
                        type: string
                        description: shifu avatar
        responses:
            200:
                description: create shifu success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: object
                                    $ref: "#/components/schemas/ShifuDto"
        """
        user_id = request.user.user_id
        shifu_name = request.get_json().get("name")
        if not shifu_name:
            raise_param_error("name is required")
        shifu_description = request.get_json().get("description")
        shifu_avatar = request.get_json().get("avatar", "")
        return make_common_response(
            create_shifu(app, user_id, shifu_name, shifu_description, shifu_avatar, [])
        )

    @app.route(path_prefix + "/shifus/<shifu_bid>/detail", methods=["GET"])
    @ShifuTokenValidation(ShifuPermission.VIEW)
    def get_shifu_detail_api(shifu_bid: str):
        """
        get shifu detail
        ---
        tags:
            - shifu
        parameters:
            - name: shifu_bid
              type: string
              required: true
        responses:
            200:
                description: get shifu detail success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: object
                                    $ref: "#/components/schemas/ShifuDetailDto"
        """
        user_id = request.user.user_id
        app.logger.info(f"get shifu detail, user_id: {user_id}, shifu_bid: {shifu_bid}")
        return make_common_response(get_shifu_detail(app, user_id, shifu_bid))

    @app.route(path_prefix + "/shifus/<shifu_bid>/detail", methods=["POST"])
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def save_shifu_detail_api(shifu_bid: str):
        """
        save shifu detail
        ---
        tags:
            - shifu
        parameters:
            - name: shifu_bid
              type: string
              required: true
            - name: body
              in: body
              type: object
              required: true
              schema:
                type: object
                properties:
                    name:
                        type: string
                        description: shifu name
                    description:
                        type: string
                        description: shifu description
                    avatar:
                        type: string
                        description: shifu avatar
                    keywords:
                        type: array
                        items:
                            type: string
                        description: shifu keywords
                    model:
                        type: string
                        description: shifu model
                    price:
                        type: number
                        description: shifu price
                    temperature:
                        type: number
                        description: shifu temperature
        responses:
            200:
                description: save shifu detail success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: object
                                    $ref: "#/components/schemas/ShifuDetailDto"
        """
        user_id = request.user.user_id
        shifu_name = request.get_json().get("name")
        shifu_description = request.get_json().get("description")
        shifu_avatar = request.get_json().get("avatar")
        shifu_keywords = request.get_json().get("keywords")
        shifu_model = request.get_json().get("model")
        shifu_price = request.get_json().get("price")
        shifu_temperature = request.get_json().get("temperature")
        return make_common_response(
            save_shifu_detail(
                app,
                user_id,
                shifu_bid,
                shifu_name,
                shifu_description,
                shifu_avatar,
                shifu_keywords,
                shifu_model,
                shifu_price,
                shifu_temperature,
            )
        )

    @app.route(path_prefix + "/shifus/<shifu_bid>/favorite", methods=["POST"])
    def mark_favorite_shifu_api():
        """
        mark favorite shifu
        ---
        tags:
            - shifu
        parameters:
            - name: shifu_bid
              type: string
              required: true
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    is_favorite:
                        type: boolean
                        description: is favorite
        responses:
            200:
                description: mark favorite shifu success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: boolean
                                    description: is favorite
        """
        user_id = request.user.user_id
        shifu_bid = request.view_args.get("shifu_bid")
        is_favorite = request.get_json().get("is_favorite")
        if isinstance(is_favorite, str):
            is_favorite = True if is_favorite.lower() == "true" else False
        elif isinstance(is_favorite, bool):
            is_favorite = is_favorite
        else:
            raise_param_error("is_favorite is not a boolean")
        return make_common_response(
            mark_or_unmark_favorite_shifu(app, user_id, shifu_bid, is_favorite)
        )

    @app.route(path_prefix + "/shifus/<shifu_bid>/publish", methods=["POST"])
    @ShifuTokenValidation(ShifuPermission.PUBLISH)
    def publish_shifu_api(shifu_bid: str):
        """
        publish shifu
        ---
        tags:
            - shifu
        parameters:
            - name: shifu_bid
              type: string
              required: true
        responses:
            200:
                description: publish shifu success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: string
                                    description: publish url
        """
        user_id = request.user.user_id
        return make_common_response(publish_shifu(app, user_id, shifu_bid))

    @app.route(path_prefix + "/shifus/<shifu_bid>/preview", methods=["POST"])
    @ShifuTokenValidation(ShifuPermission.VIEW)
    def preview_shifu_api(shifu_bid: str):
        """
        preview shifu
        ---
        tags:
            - shifu
        parameters:
            - name: shifu_bid
              type: string
              required: true
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    variables:
                        type: object
                        description: variables
                    skip:
                        type: boolean
                        description: skip
        responses:
            200:
                description: preview shifu success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: string
                                    description: preview url
        """
        user_id = request.user.user_id
        variables = request.get_json().get("variables")
        skip = request.get_json().get("skip", False)
        return make_common_response(
            preview_shifu(app, user_id, shifu_bid, variables, skip)
        )

    @app.route(path_prefix + "/shifus/<shifu_bid>/chapters/order", methods=["POST"])
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def update_chapter_order_api(shifu_bid: str):
        """
        update chapter order
        reset the chapter order to the order of the chapter ids
        ---
        tags:
            - shifu
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    shifu_id:
                        type: string
                        description: shifu id
                    chapter_ids:
                        type: array
                        items:
                            type: string
                        description: chapter ids
                    move_chapter_id:
                        type: string
                        description: the chapter id to be moved
                    move_to_parent_id:
                        type: string
                        description: the parent chapter id where the chapter will be moved to
        responses:
            200:
                description: update chapter order success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: array
                                    items:
                                        $ref: "#/components/schemas/ChapterDto"
        """
        user_id = request.user.user_id
        chapter_ids = request.get_json().get("chapter_ids")
        move_chapter_id = request.get_json().get("move_chapter_id")
        if not move_chapter_id:
            raise_param_error("move_chapter_id is required")
        move_to_parent_id = request.get_json().get("move_to_parent_id")
        return make_common_response(
            update_chapter_order(
                app, user_id, shifu_bid, chapter_ids, move_chapter_id, move_to_parent_id
            )
        )

    @app.route(path_prefix + "/shifus/<shifu_bid>/outlines", methods=["PUT"])
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def create_unit_api(shifu_bid: str):
        """
        create unit
        ---
        tags:
            - shifu
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    shifu_id:
                        type: string
                        description: shifu id
                    parent_id:
                        type: string
                        description: chapter id
                    unit_name:
                        type: string
                        description: unit name
                    unit_description:
                        type: string
                        description: unit description
                    unit_type:
                        type: string
                        description: unit type (normal,trial)
                    unit_system_prompt:
                        type: string
                        description: unit system prompt
                    unit_is_hidden:
                        type: boolean
                        description: unit is hidden
                    unit_index:
                        type: integer
                        description: unit index
        responses:
            200:
                description: create unit success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: object
                                    $ref: "#/components/schemas/OutlineDto"
        """
        user_id = request.user.user_id
        parent_bid = request.get_json().get("parent_bid")
        unit_name = request.get_json().get("unit_name")
        unit_description = request.get_json().get("unit_description", "")
        unit_type = request.get_json().get("unit_type", LESSON_TYPE_TRIAL)
        unit_index = request.get_json().get("unit_index", None)
        unit_system_prompt = request.get_json().get("unit_system_prompt", None)
        unit_is_hidden = request.get_json().get("unit_is_hidden", False)
        return make_common_response(
            create_unit(
                app,
                user_id,
                shifu_bid,
                parent_bid,
                unit_name,
                unit_description,
                unit_type,
                unit_index,
                unit_system_prompt,
                unit_is_hidden,
            )
        )

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>", methods=["POST"]
    )
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def modify_unit_api(shifu_bid: str, outline_bid: str):
        """
        modify unit
        ---
        tags:
            - shifu
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    name:
                        type: string
                        description: outline name
                    description:
                        type: string
                        description: outline description
                    index:
                        type: integer
                        description: outline index
                    system_prompt:
                        type: string
                        description: outline system prompt
                    is_hidden:
                        type: boolean
                        description: outline is hidden
                    type:
                        type: string
                        description: unit type (normal,trial)
        responses:
            200:
                description: modify unit success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: object
                                    $ref: "#/components/schemas/OutlineDto"
        """
        user_id = request.user.user_id
        unit_name = request.get_json().get("name")
        unit_description = request.get_json().get("description")
        unit_index = request.get_json().get("index")
        unit_system_prompt = request.get_json().get("system_prompt", None)
        unit_is_hidden = request.get_json().get("is_hidden", False)
        unit_type = request.get_json().get("type", LESSON_TYPE_TRIAL)
        return make_common_response(
            modify_unit(
                app,
                user_id,
                outline_bid,
                unit_name,
                unit_description,
                unit_index,
                unit_system_prompt,
                unit_is_hidden,
                unit_type,
            )
        )

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>", methods=["GET"]
    )
    @ShifuTokenValidation(ShifuPermission.VIEW)
    def get_unit_info_api(shifu_bid: str, outline_bid: str):
        """
        get unit info
        ---
        tags:
            - shifu
        parameters:
            - name: outline_bid
              type: string
              required: true
        responses:
            200:
                description: get unit info success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: object
                                    $ref: "#/components/schemas/OutlineDto"
        """
        user_id = request.user.user_id
        return make_common_response(get_unit_by_id(app, user_id, outline_bid))

    @app.route(
        path_prefix + "/shifus/<shifu_id>/chapters/<chapter_id>/units/<unit_id>",
        methods=["DELETE"],
    )
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def delete_unit_api():
        """
        delete unit
        ---
        tags:
            - shifu
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    unit_id:
                        type: string
                        description: unit id
        responses:
            200:
                description: delete unit success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: boolean
                                    description: delete unit success
        """
        user_id = request.user.user_id
        unit_id = request.get_json().get("unit_id")
        return make_common_response(delete_unit(app, user_id, unit_id))

    @app.route(path_prefix + "/shifus/<shifu_bid>/outlines", methods=["GET"])
    @ShifuTokenValidation(ShifuPermission.VIEW)
    def get_outline_tree_api(shifu_bid: str):
        """
        get outline tree
        ---
        tags:
            - shifu
        parameters:
            - name: shifu_bid
              type: string
              required: true
        responses:
            200:
                description: get outline tree success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: array
                                    items:
                                        $ref: "#/components/schemas/SimpleOutlineDto"
        """
        user_id = request.user.user_id
        return make_common_response(get_outline_tree(app, user_id, shifu_bid))

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>/blocks",
        methods=["GET"],
    )
    @ShifuTokenValidation(ShifuPermission.VIEW)
    def get_block_list_api(shifu_bid: str, outline_bid: str):
        """
        get block list
        ---
        tags:
            - shifu
        parameters:
            - name: outline_id
              type: string
              required: true
        responses:
            200:
                description: get block list success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: array
                                    items:
                                        $ref: "#/components/schemas/BlockDto"
        """
        user_id = request.user.user_id
        return make_common_response(get_block_list(app, user_id, outline_bid))

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>/blocks",
        methods=["POST"],
    )
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def save_blocks_api(shifu_bid: str, outline_bid: str):
        """
        save blocks
        ---
        tags:
            - shifu
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    outline_id:
                        type: string
                        description: outline id
                    blocks:
                        type: array
                        items:
                            $ref: "#/components/schemas/BlockDto"
        responses:
            200:
                description: save blocks success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: array
                                    items:
                                        $ref: "#/components/schemas/BlockDto"
        """
        user_id = request.user.user_id
        blocks = request.get_json().get("blocks")
        return make_common_response(save_block_list(app, user_id, outline_bid, blocks))

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>/blocks",
        methods=["PUT"],
    )
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def add_block_api(shifu_bid: str, outline_bid: str):
        """
        add block
        ---
        tags:
            - shifu
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    outline_bid:
                        type: string
                        description: outline bid
                    block:
                        type: object
                        $ref: "#/components/schemas/BlockDto"
                    block_index:
                        type: integer
                        description: block index
        responses:
            200:
                description: add block success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: object
                                    $ref: "#/components/schemas/BlockDto"
        """
        user_id = request.user.user_id
        block = request.get_json().get("block")
        block_index = request.get_json().get("block_index")
        return make_common_response(
            add_block(app, user_id, outline_bid, block, block_index)
        )

    @app.route(path_prefix + "/shifus/<shifu_id>/upfile", methods=["POST"])
    def upfile_api():
        """
        upfile to oss
        ---
        tags:
            - shifu
        parameters:
            - in: formData
              name: file
              type: file
              required: true
              description: documents
        responses:
            200:
                description: upload success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: return msg
                                data:
                                    type: string
                                    description: shifu file url
        """
        file = request.files.get("file", None)
        resource_id = request.values.get("resource_id", None)
        if resource_id is None:
            resource_id = ""
        user_id = request.user.user_id
        if not file:
            raise_param_error("file")
        return make_common_response(upload_file(app, user_id, resource_id, file))

    @app.route(path_prefix + "/shifus/<shifu_id>/url-upfile", methods=["POST"])
    def upload_url_api():
        """
        upload url to oss
        ---
        tags:
            - shifu
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    url:
                        type: string
                        description: url
        responses:
            200:
                description: upload success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: string
                                    description: uploaded file url
        """
        user_id = request.user.user_id
        url = request.get_json().get("url")
        if not url:
            raise_param_error("url is required")
        return make_common_response(upload_url(app, user_id, url))

    @app.route(path_prefix + "/shifus/<shifu_id>/get-video-info", methods=["POST"])
    def get_video_info_api():
        """
        get video info
        ---
        tags:
            - shifu
        parameters:
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    url:
                        type: string
                        description: url
        responses:
            200:
                description: get video info success
                content:
                    application/json:
                        schema:
                            properties:
                                code:
                                    type: integer
                                    description: code
                                message:
                                    type: string
                                    description: message
                                data:
                                    type: object
                                    description: video metadata
        """
        user_id = request.user.user_id
        url = request.get_json().get("url")
        if not url:
            raise_param_error("url is required")
        return make_common_response(get_video_info(app, user_id, url))

    return app
