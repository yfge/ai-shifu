from flask import Flask
from flaskr.service.shifu.models import DraftOutlineItem
from flaskr.service.common import raise_error
from flaskr.dao import db


def get_shifu_mdflow(app: Flask, shifu_bid: str, outline_bid: str) -> str:
    """
    Get shifu mdflow
    """
    with app.app_context():
        outline_item = DraftOutlineItem.query.filter(
            DraftOutlineItem.outline_item_bid == outline_bid
        ).first()
        if not outline_item:
            raise_error("SHIFU.OUTLINE_ITEM_NOT_FOUND")
        return outline_item.content


def save_shifu_mdflow(
    app: Flask, shifu_bid: str, outline_bid: str, content: str
) -> str:
    """
    Save shifu mdflow
    """
    with app.app_context():
        outline_item = DraftOutlineItem.query.filter(
            DraftOutlineItem.outline_item_bid == outline_bid
        ).first()
        if not outline_item:
            raise_error("SHIFU.OUTLINE_ITEM_NOT_FOUND")
        outline_item.content = content
        db.session.commit()
