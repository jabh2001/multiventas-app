from flask import Blueprint, jsonify, request, g
from flask_jwt_extended import current_user, jwt_required
from libs.models import Platform, StreamingAccount, Screen, Config, AfiliationGiftCode, User, db
from libs.schemas import UserSchema, AfiliationGiftCodeSchema
from services.clientService.seller_service import afiliar as afiliar_service, afiliar_with_code, afiliar_platinum as afiliar_platinum_services, afiliar_platinum_with_code, buy_affiliation_gift_code
from services.responsesService import SuccessResponse, ErrorResponse
from services.money_change_service import str_price, change_price

# BLUEPRINTS
seller_bp = Blueprint('seller_bp', __name__)


def create_str_price(user=None):
    money_type=user.main_money if user else "bs"
    return lambda price: str_price(price=price, money_type=money_type)


@seller_bp.route("/")
@jwt_required()
def index():
    platform_prices = db.session.query( Platform.name, db.func.max(StreamingAccount.price).label("price"), db.func.max(StreamingAccount.afiliated_price).label("afiliated_price"), db.func.max(StreamingAccount.reference_reward).label("reference_reward") ).\
                        select_from(StreamingAccount).\
                        join(Platform, Platform.id == StreamingAccount.platform_id).\
                        where(StreamingAccount.days > 28).\
                        where(StreamingAccount.id.in_(db.session.query(Screen.account_id).subquery() )).\
                        group_by(Platform.name).all()
    config = Config.query.filter_by(name="afiliation").first()
    vip_config = Config.query.filter_by(name="vip").first()
    platinum_config = Config.query.filter_by(name="platinum").first()

    afiliation = current_user.afiliated
    platinum_membership = current_user.platinum_membership
    is_afiliated = afiliation.status == 1 if afiliation else False
    time = " - " if not afiliation else f"Inicio: {afiliation.start_date.strftime('%d-%m-%Y')} - Fin: {afiliation.end_date.strftime('%d-%m-%Y')}"
    create_final_price = create_str_price(current_user)

    return jsonify({
        "is_afiliated": is_afiliated,
        "is_platinum_membership": not platinum_membership is None,
        "afiliation_price":create_final_price(config.options["price"]),
        "vip_price":create_final_price(vip_config.options["price"]),
        "vip_reference_reward":create_final_price(vip_config.options["reference_reward"]),
        "vip_gift_code_price":create_final_price(vip_config.options.get("gift_code_price", 0)),
        "platinum_price":create_final_price(platinum_config.options["price"]),
        "platinum_reference_reward":create_final_price(platinum_config.options["reference_reward"]),
        "platinum_gift_code_price":create_final_price(platinum_config.options.get("gift_code_price", 0)),
        "time":time,
        "platform_prices" : [ {
            "name": row.name,
            "price": f"{row.price}$",
            "afiliated_price": f"{row.afiliated_price}$",
            "reference_reward": f"{row.reference_reward}$"
        } for row in platform_prices]
    })

@seller_bp.route("/buy/vip/", methods=["POST"])
@jwt_required()
def afiliar():
    try:
        if current_user.is_vip(): raise Exception("Ya estas suscrito")
        if "code" in request.args:
            gift_code = AfiliationGiftCode.query.filter(AfiliationGiftCode.code == request.args['code']).first()
            msg, end_date = afiliar_with_code(current_user, gift_code, hoy=g.today)
            return SuccessResponse({ "msg": msg, "start_date":g.today, "end_date":end_date, "user": UserSchema(exclude=("password", "parent_id")).dump(current_user)})

        else:
            wallet = current_user.wallet
            config = Config.query.filter_by(name="vip").first()

            price = change_price(config.options["price"], money_type=current_user.main_money, rounded=False)
            reference_reward = change_price(config.options["reference_reward"], money_type=current_user.main_money, rounded=False)

            if wallet.main(current_user) < price: raise Exception("No tienes dinero suficiente")
            
            msg, end_date = afiliar_service(current_user, wallet, price, reference_reward, hoy=g.today)
            return SuccessResponse({ "msg": msg, "start_date":g.today, "end_date":end_date, "user": UserSchema(exclude=("password", "parent_id")).dump(current_user)})

    except Exception as e:
        return ErrorResponse(error = str(e), status_code=400)

@seller_bp.route("/buy/titanium/", methods=["POST"])
@seller_bp.route("/buy/platinum/", methods=["POST"])
@jwt_required()
def afiliar_platinum():
    try:
        if current_user.is_platinum(): raise Exception("Ya estas suscrito")
        if "code" in request.args:
            gift_code = AfiliationGiftCode.query.filter(AfiliationGiftCode.code == request.args['code']).first()
            msg = afiliar_platinum_with_code(current_user, gift_code, g.today)
            return SuccessResponse({ "msg": msg, "user": UserSchema(exclude=("password", "parent_id")).dump(current_user)})
        else:
            wallet = current_user.wallet
            config = Config.query.filter_by(name="platinum").first()

            price = change_price(config.options["price"], money_type=current_user.main_money, rounded=False)
            reference_reward = change_price(config.options["reference_reward"], money_type=current_user.main_money, rounded=False)

            if wallet.main(current_user) < price: raise Exception("No tienes dinero suficiente")
            
            msg = afiliar_platinum_services(current_user, wallet, price, reference_reward, g.today)
            return SuccessResponse({ "msg": msg, "user": UserSchema(exclude=("password", "parent_id")).dump(current_user) })

    except Exception as e:
        return ErrorResponse(error = str(e), status_code=400)


@seller_bp.route("/afiliation-gift-code/")
@jwt_required()
def afiliation_gift_code():
    all_codes = (
        db.session.query(AfiliationGiftCode, User)
        .join(User, AfiliationGiftCode.receiver_id == User.id, isouter=True)
        .filter(AfiliationGiftCode.owner_id == current_user.id)
        .all()
    )
    code_schema = AfiliationGiftCodeSchema()
    user_schema = UserSchema(only=("username", "email", "phone"))
    return [
        {**code_schema.dump(code), "user":user_schema.dump(user)} for code, user in all_codes
    ]

@seller_bp.route("/buy/gift/<affiliation>/", methods=["POST"])
@jwt_required()
def buy_afiliation_gift_code(affiliation: str):
    try:
        affiliation = affiliation.lower()
        if not affiliation in ["vip", "titanium"]:
            raise Exception("afiliación no encontrada")
        if affiliation == "titanium" and not current_user.is_platinum():
            raise Exception("Debes haber comprado este plan previamente")
        if affiliation == "vip" and not current_user.is_vip():
            raise Exception("Debes haber comprado este plan previamente")
            
        wallet = current_user.wallet
        affiliation = affiliation if affiliation == "vip" else "platinum"
        config = Config.query.filter(Config.name == affiliation ).first()

        price = change_price(config.options["gift_code_price"], money_type=current_user.main_money, rounded=False)

        if wallet.main(current_user) < price: raise Exception("No tienes dinero suficiente")
        
        code = buy_affiliation_gift_code(current_user, wallet, price, affiliation)
        return SuccessResponse({ "code": code.code })

    except Exception as e:
        return ErrorResponse(error = str(e), status_code=400)
