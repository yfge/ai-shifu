"""
Shifu route

This module contains route functions for shifu.
use restful api to manage shifu.
will be auto registered by flaskr.framework.plugin.inject.inject
includes:
    - get shifu list
    - create shifu
    - get shifu detail
    - save shifu detail
    - mark favorite shifu
    - publish shifu
    - preview shifu
    - reorder outline tree
    - create outline
    - modify outline
    - get outline info
    - delete outline
    - get outline tree
    - get block list
    - save blocks
    - add block
    - upload file
    - upload url
    - get video info

Author: yfge
Date: 2025-08-07
"""

from flask import Flask, request, current_app
from .funcs import (
    mark_or_unmark_favorite_shifu,
    upload_file,
    upload_url,
    get_video_info,
    shifu_permission_verification,
)
from flaskr.route.common import make_common_response
from flaskr.framework.plugin.inject import inject
from flaskr.service.common.models import raise_param_error, raise_error
from .consts import UNIT_TYPE_GUEST
from functools import wraps
from enum import Enum


from flaskr.service.shifu.shifu_draft_funcs import (
    get_shifu_draft_list,
    create_shifu_draft,
    get_shifu_draft_info,
    save_shifu_draft_info,
)
from flaskr.service.shifu.shifu_publish_funcs import (
    publish_shifu_draft,
    preview_shifu_draft,
)
from flaskr.service.shifu.shifu_outline_funcs import (
    reorder_outline_tree,
    create_outline,
    modify_unit,
    get_unit_by_id,
    delete_unit,
    get_outline_tree,
)
from flaskr.service.shifu.shifu_block_funcs import (
    get_block_list,
    save_shifu_block_list,
    add_block,
)
from flaskr.service.shifu.shifu_mdflow_funcs import (
    get_shifu_mdflow,
    save_shifu_mdflow,
    parse_shifu_mdflow,
)


class ShifuPermission(Enum):
    VIEW = "view"
    EDIT = "edit"
    PUBLISH = "publish"


class ShifuTokenValidation:
    """
    Shifu token validation decorator
    if is_creator is true, only verify creator permission and skip shifu-specific verification
    """

    def __init__(
        self,
        permission: ShifuPermission = ShifuPermission.VIEW,
        is_creator: bool = False,
    ):
        self.permission = permission
        self.is_creator = is_creator

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

            if not request.user.is_creator:
                raise_error("server.shifu.noPermission")

            # If is_creator is True, only verify creator permission and skip shifu-specific verification
            if self.is_creator:
                return f(*args, **kwargs)

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
                raise_error("server.shifu.noPermission")

            return f(*args, **kwargs)

        return decorated_function


@inject
def register_shifu_routes(app: Flask, path_prefix="/api/shifu"):
    """
    Register shifu routes
    """
    app.logger.info(f"register shifu routes {path_prefix}")

    @app.route(path_prefix + "/shifus", methods=["GET"])
    @ShifuTokenValidation(ShifuPermission.VIEW, is_creator=True)
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
            get_shifu_draft_list(app, user_id, page_index, page_size, is_favorite)
        )

    @app.route(path_prefix + "/shifus", methods=["PUT"])
    @ShifuTokenValidation(ShifuPermission.VIEW, is_creator=True)
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
            create_shifu_draft(
                app, user_id, shifu_name, shifu_description, shifu_avatar, []
            )
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
        return make_common_response(get_shifu_draft_info(app, user_id, shifu_bid))

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
        shifu_system_prompt = request.get_json().get("system_prompt", None)
        return make_common_response(
            save_shifu_draft_info(
                app,
                user_id,
                shifu_bid,
                shifu_name,
                shifu_description,
                shifu_avatar,
                shifu_keywords,
                shifu_model,
                shifu_temperature,
                shifu_price,
                shifu_system_prompt,
            )
        )

    @app.route(path_prefix + "/shifus/<shifu_bid>/favorite", methods=["POST"])
    @ShifuTokenValidation(ShifuPermission.VIEW, is_creator=True)
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
        return make_common_response(publish_shifu_draft(app, user_id, shifu_bid))

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
        return make_common_response(
            preview_shifu_draft(app, user_id, shifu_bid, variables)
        )

    @app.route(path_prefix + "/shifus/<shifu_bid>/outlines/reorder", methods=["PATCH"])
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def update_chapter_order_api(shifu_bid: str):
        """
        update chapter order
        reset the chapter order to the order of the chapter ids
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
                $ref: "#/components/schemas/ReorderOutlineDto"


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
                                        $ref: "#/components/schemas/OutlineDto"
        """
        user_id = request.user.user_id
        outlines = request.get_json().get("outlines")
        app.logger.info(type(outlines))
        app.logger.info(
            f"reorder outline tree, user_id: {user_id}, shifu_bid: {shifu_bid}, outlines: {outlines}"
        )
        return make_common_response(
            reorder_outline_tree(app, user_id, shifu_bid, outlines)
        )

    @app.route(path_prefix + "/shifus/<shifu_bid>/outlines", methods=["PUT"])
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def create_outline_api(shifu_bid: str):
        """
        create unit
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
                    parent_bid:
                        type: string
                        description: parent id
                    name:
                        type: string
                        description: outline name
                    description:
                        type: string
                        description: outline description
                    type:
                        type: string
                        description: outline type (normal,trial,guest)
                    system_prompt:
                        type: string
                        description: outline system prompt
                    is_hidden:
                        type: boolean
                        description: outline is hidden
                    index:
                        type: integer
                        description: outline index
        responses:
            200:
                description: create outline success
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
                                    $ref: "#/components/schemas/SimpleOutlineDto"
        """
        user_id = request.user.user_id
        parent_bid = request.get_json().get("parent_bid")
        name = request.get_json().get("name")
        description = request.get_json().get("description", "")
        type = request.get_json().get("type", UNIT_TYPE_GUEST)
        index = request.get_json().get("index", None)
        system_prompt = request.get_json().get("system_prompt", None)
        is_hidden = request.get_json().get("is_hidden", False)
        return make_common_response(
            create_outline(
                app,
                user_id,
                shifu_bid,
                parent_bid,
                name,
                description,
                index,
                type,
                system_prompt,
                is_hidden,
            )
        )

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>", methods=["POST"]
    )
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def modify_outline_api(shifu_bid: str, outline_bid: str):
        """
        modify outline
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
                        description: unit type (normal,trial,guest)
        responses:
            200:
                description: modify outline success
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
        name = request.get_json().get("name")
        description = request.get_json().get("description")
        index = request.get_json().get("index")
        system_prompt = request.get_json().get("system_prompt", None)
        is_hidden = request.get_json().get("is_hidden", False)
        type = request.get_json().get("type", UNIT_TYPE_GUEST)
        return make_common_response(
            modify_unit(
                app,
                user_id,
                outline_bid,
                name,
                description,
                index,
                system_prompt,
                is_hidden,
                type,
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
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>",
        methods=["DELETE"],
    )
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def delete_unit_api(shifu_bid: str, outline_bid: str):
        """
        delete unit
        ---
        tags:
            - shifu
        parameters:
            - name: shifu_bid
              type: string
              required: true
            - name: outline_bid
              type: string
              required: true
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
        return make_common_response(delete_unit(app, user_id, outline_bid))

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>/mdflow",
        methods=["GET"],
    )
    @ShifuTokenValidation(ShifuPermission.VIEW)
    def get_mdflow_api(shifu_bid: str, outline_bid: str):
        """
        get mdflow
        ---
        tags:
            - shifu
        parameters:
            - name: outline_bid
              type: string
              required: true
            - name: shifu_bid
              type: string
              required: true
        responses:
            200:
                description: get mdflow success
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
                                    description: mdflow
        """
        user_id = request.user.user_id
        return make_common_response(get_shifu_mdflow(app, user_id, outline_bid))

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>/mdflow",
        methods=["POST"],
    )
    @ShifuTokenValidation(ShifuPermission.EDIT)
    def save_mdflow_api(shifu_bid: str, outline_bid: str):
        """
        save mdflow
        ---
        tags:
            - shifu
        parameters:
            - name: outline_bid
              type: string
              required: true
            - name: shifu_bid
              type: string
              required: true
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    data:
                        type: string
                        description: mdflow
        responses:
            200:
                description: save mdflow success
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
                                    description: mdflow
        """
        user_id = request.user.user_id
        content = request.get_json().get("data")
        return make_common_response(
            save_shifu_mdflow(app, user_id, shifu_bid, outline_bid, content)
        )

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>/mdflow/parse",
        methods=["POST"],
    )
    @ShifuTokenValidation(ShifuPermission.VIEW)
    def parse_mdflow_api(shifu_bid: str, outline_bid: str):
        """
        parse mdflow
        ---
        tags:
            - shifu
        parameters:
            - name: outline_bid
              type: string
              required: true
            - in: body
              name: body
              required: true
              schema:
                type: object
                properties:
                    data:
                        type: string
                        description: mdflow
        responses:
            200:
                description: parse mdflow success
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
                                    $ref: "#/components/schemas/MdflowDTOParseResult"
        """
        data = request.get_json().get("data", None)
        return make_common_response(
            parse_shifu_mdflow(app, shifu_bid, outline_bid, data)
        )

    @app.route(
        path_prefix + "/shifus/<shifu_bid>/outlines/<outline_bid>/mdflow/run",
        methods=["POST"],
    )
    @ShifuTokenValidation(ShifuPermission.VIEW)
    def run_mdflow_api(shifu_bid: str, outline_bid: str):
        """
        run mdflow

        Raises:
            NotImplementedError: This API endpoint is not yet implemented
        """
        raise NotImplementedError("MDFlow run API is not yet implemented")

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
        return make_common_response(
            save_shifu_block_list(app, user_id, outline_bid, blocks)
        )

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
        if block is None:
            raise_param_error("block is required")
        if block_index is None:
            raise_param_error("block_index is required")
        if not block.get("type"):
            raise_param_error("block type is required")
        return make_common_response(
            add_block(app, user_id, outline_bid, block, block_index)
        )

    @app.route(path_prefix + "/upfile", methods=["POST"])
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

    @app.route(path_prefix + "/url-upfile", methods=["POST"])
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

    @app.route(path_prefix + "/get-video-info", methods=["POST"])
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
