# user service
# author: yfge
#


import uuid
from flask import Flask, current_app

from ...common.config import get_config
from ..common.models import raise_error, raise_error_with_args

from .utils import generate_token
from ...service.common.dtos import USER_STATE_UNREGISTERED, UserToken
from ...service.user.models import User, UserConversion
from ...dao import db
from ...api.wechat import get_wechat_access_token
import oss2
from .repository import build_user_info_dto, sync_user_entity_for_legacy


endpoint = get_config("ALIBABA_CLOUD_OSS_ENDPOINT")

ALI_API_ID = get_config("ALIBABA_CLOUD_OSS_ACCESS_KEY_ID")
ALI_API_SECRET = get_config("ALIBABA_CLOUD_OSS_ACCESS_KEY_SECRET")
IMAGE_BASE_URL = get_config("ALIBABA_CLOUD_OSS_BASE_URL")
BUCKET_NAME = get_config("ALIBABA_CLOUD_OSS_BUCKET")
if not ALI_API_ID or not ALI_API_SECRET:
    current_app.logger.warning(
        "ALIBABA_CLOUD_ACCESS_KEY_ID or ALIBABA_CLOUD_ACCESS_KEY_SECRET not configured"
    )
else:
    auth = oss2.Auth(ALI_API_ID, ALI_API_SECRET)
    bucket = oss2.Bucket(auth, endpoint, BUCKET_NAME)

# generate temp user for anonymous user
# author: yfge


def generate_temp_user(
    app: Flask, temp_id: str, user_source="web", wx_code=None, language="en-US"
) -> UserToken:
    with app.app_context():
        convert_user = UserConversion.query.filter(
            UserConversion.conversion_id == temp_id,
            UserConversion.conversion_source == user_source,
        ).first()
        wx_openid = ""
        if wx_code:
            wx_data = get_wechat_access_token(app, wx_code)
            if wx_data:
                wx_openid = wx_data.get("openid", "")
                # wx_uinionid = wx_data.get("unionid", "")
        if not convert_user:
            if wx_openid != "":
                user_info = (
                    User.query.filter(User.user_open_id == wx_openid)
                    .order_by(User.id.asc())
                    .first()
                )
                if user_info:
                    sync_user_entity_for_legacy(app, user_info)
                    return UserToken(
                        build_user_info_dto(user_info),
                        token=generate_token(app, user_id=user_info.user_id),
                    )
            user_id = str(uuid.uuid4()).replace("-", "")
            new_convert_user = UserConversion(
                user_id=user_id,
                conversion_uuid=temp_id,
                conversion_id=temp_id,
                conversion_source=user_source,
                conversion_status=0,
            )
            new_user = User(user_id=user_id, user_state=USER_STATE_UNREGISTERED)
            new_user.user_language = language
            new_user.user_open_id = wx_openid
            db.session.add(new_convert_user)
            db.session.add(new_user)
            db.session.commit()
            sync_user_entity_for_legacy(app, new_user)
            token = generate_token(app, user_id=user_id)
            return UserToken(build_user_info_dto(new_user), token=token)
        else:
            if wx_openid != "":
                user = (
                    User.query.filter(User.user_open_id == wx_openid)
                    .order_by(User.id.asc())
                    .first()
                )
                if user:
                    sync_user_entity_for_legacy(app, user)
                    return UserToken(
                        build_user_info_dto(user),
                        token=generate_token(app, user_id=user.user_id),
                    )
            user = User.query.filter_by(user_id=convert_user.user_id).first()
            user.user_open_id = wx_openid
            db.session.commit()
            sync_user_entity_for_legacy(app, user)
            token = generate_token(app, user_id=user.user_id)
            return UserToken(build_user_info_dto(user), token=token)


def update_user_open_id(app: Flask, user_id: str, wx_code: str) -> str:
    app.logger.info(f"update_user_open_id user_id: {user_id} wx_code: {wx_code}")
    with app.app_context():
        user = User.query.filter(User.user_id == user_id).first()
        if user:
            wx_data = get_wechat_access_token(app, wx_code)
            if wx_data:
                wx_openid = wx_data.get("openid", "")
                if wx_openid and user.user_open_id != wx_openid and wx_openid != "":
                    user.user_open_id = wx_openid
                    db.session.commit()
                    app.logger.info(
                        f"update_user_open_id user_id: {user_id} wx_openid: {wx_openid}"
                    )
                return wx_openid
        else:
            app.logger.error("user not found")
        return ""


def get_content_type(filename):
    extension = filename.rsplit(".", 1)[1].lower()
    if extension in ["jpg", "jpeg"]:
        return "image/jpeg"
    elif extension == "png":
        return "image/png"
    elif extension == "gif":
        return "image/gif"
    raise_error("module.backend.file.fileTypeNotSupport")


def upload_user_avatar(app: Flask, user_id: str, avatar) -> str:
    with app.app_context():
        if not ALI_API_ID or not ALI_API_SECRET:
            raise_error_with_args(
                "module.backend.api.alibabaCloudNotConfigured",
                config_var="ALIBABA_CLOUD_OSS_ACCESS_KEY_ID,ALIBABA_CLOUD_OSS_ACCESS_KEY_SECRET",
            )
        user = User.query.filter(User.user_id == user_id).first()
        if user:
            file_id = str(uuid.uuid4()).replace("-", "")
            old_avatar = user.user_avatar
            if old_avatar:
                old_file_id = old_avatar.split("/")[-1]
                if old_file_id and bucket.object_exists(old_file_id):
                    bucket.delete_object(old_file_id)
            bucket.put_object(
                file_id,
                avatar,
                headers={"Content-Type": get_content_type(avatar.filename)},
            )
            url = IMAGE_BASE_URL + "/" + file_id
            user.user_avatar = url
            db.session.commit()
            sync_user_entity_for_legacy(app, user)

            from ..shifu.funcs import _warm_up_cdn

            if not _warm_up_cdn(app, url, ALI_API_ID, ALI_API_SECRET, endpoint):
                app.logger.warning(
                    "The user avatar URL is inaccessible, but the URL continues to be returned"
                )

            return url
