from flask import Blueprint, request
from flask_jwt_extended import jwt_required, current_user
from libs.models import FrequentQuestion, Banner, Lottery, db
from libs.schemas import FrequentQuestionSchema, BannerSchema
from services.money_change_service import str_price


# BLUEPRINTS
system_bp = Blueprint('system_bp', __name__)

@system_bp.route("/frequent-question/")
@system_bp.route("/frequent-questions/")
def frequent_question():
    frequent_question_schema = FrequentQuestionSchema()
    return frequent_question_schema.dump(FrequentQuestion.query, many=True)

@system_bp.route("/banner/")
@system_bp.route("/banners/")
def banner():
    banner_schema = BannerSchema()
    return banner_schema.dump(Banner.query, many=True)

@system_bp.route("/lottery/")
@jwt_required()
def lottery():
    config = Lottery.config()
    lottery = Lottery.query.filter(Lottery.user == current_user).first()
    amount = 0
    if not lottery:
        amount = 0
    else:
        amount = lottery.amount

    return {
        "config":{
            **config.options,
            "active":{
                **config.options["active"],
                "start_date":Lottery.start_date.strftime("%d-%m-%Y"),
                "end_date":Lottery.end_date.strftime("%d-%m-%Y") if Lottery.end_date else ""
            },
            "min_buy":str_price(config.options["min_buy"], current_user.main_money)
        },
        "data":amount,
    }
