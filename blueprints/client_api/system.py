from flask import Blueprint, request
from flask_jwt_extended import jwt_required, current_user
from libs.models import FrequentQuestion, Banner, Lottery, db
from libs.schemas import FrequentQuestionSchema, BannerSchema
from libs.cache import timed_memoized
from services.money_change_service import str_price


# BLUEPRINTS
system_bp = Blueprint('system_bp', __name__)

@timed_memoized(3600)
def get_questions():
    frequent_question_schema = FrequentQuestionSchema()
    return frequent_question_schema.dump(FrequentQuestion.query, many=True)

@timed_memoized(3600)
def get_banners():
    banner_schema = BannerSchema()
    return banner_schema.dump(Banner.query, many=True)

@timed_memoized(3600)
def get_lottery(user_id):
    lottery = Lottery.query.filter(Lottery.user_id == user_id).first()


@system_bp.route("/frequent-question/")
@system_bp.route("/frequent-questions/")
def frequent_question():
    return get_questions()
    
@system_bp.route("/banner/")
@system_bp.route("/banners/")
def banner():
    return get_banners()

@system_bp.route("/lottery/")
@jwt_required()
def lottery():
    config = Lottery.config()
    lottery = get_lottery(current_user.id)
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
