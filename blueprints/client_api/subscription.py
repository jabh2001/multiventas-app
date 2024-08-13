from flask import Blueprint
from flask_jwt_extended import jwt_required, current_user
from libs.models import Prize, PrizeHistory, PrizeWallet, PrizeWalletHistory, CreditsTitaniumPrice, CreditsVipPrice, AfiliationGiftCode, User, db, Config
from libs.schemas import PrizeSchema, PrizeHistorySchema, PrizeWalletSchema, PrizeWalletHistorySchema, CreditsTitaniumPriceSchema, CreditsVipPriceSchema, AfiliationGiftCodeSchema
from services.clientService.seller_service import generate_gift_code
from services.responsesService import SuccessResponse
from services.money_change_service import change_price, str_price

subscription_bp = Blueprint('subscription_bp', __name__)

@subscription_bp.route("/prizes/")
@jwt_required()
def prizes():
    prizes = Prize.query.all()

    return {
        "prizes": PrizeSchema(many=True).dump(prizes),
    }

@subscription_bp.route("/prizes/me/")
@jwt_required()
def my_prizes():
    prize_history_schema = PrizeHistorySchema()
    prize_schema = PrizeSchema()
    return [{
        **prize_history_schema.dump(history),
        "prize":prize_schema.dump(prize)
    } for history, prize in db.session.query(PrizeHistory, Prize).join(PrizeHistory.prize).filter(PrizeHistory.user_id == current_user.id)]

@subscription_bp.route("/prizes/<prize_id>/buy/", methods=["POST"])
@jwt_required()
def buy_prize(prize_id):
    prize = Prize.query.get(prize_id)
    if not prize:
        return {"error": "Prize not found"}, 404
    if prize.points > current_user.prize_wallet.points:
        return {"error": "Insufficient Points"}, 400
    current_user.prize_wallet.points -= prize.points
    if current_user.prize_wallet.points < 0:
        return {"error": "Insufficient Points"}, 400
    prize_history = PrizeHistory(user_id=current_user.id, prize=prize, points=prize.points )
    db.session.add(prize_history)
    db.session.commit()
    return {"message": "Prize bought successfully"}, 200
    

@subscription_bp.route("/credits/")
@jwt_required()
def credits():
    titaniumSchema = CreditsTitaniumPriceSchema(many=True)
    vipSchema = CreditsVipPriceSchema(many=True)
    affiliationGiftCodeSchema = AfiliationGiftCodeSchema()
    codes = [{
        **affiliationGiftCodeSchema.dump(code),
        "user":{ 
            "username":user.username,
            "email":user.email
        } if user else None
    } for code, user in db.session.query(AfiliationGiftCode, User).join(User, AfiliationGiftCode.receiver_id == User.id, isouter=True).filter(AfiliationGiftCode.owner_id == current_user.id).all()]
    
    return {
        "creditsTitaniumPrice":[ {
            "id": credit.id,
            "amount": credit.amount,
            "price": change_price(credit.price, money_type=current_user.main_money, rounded=False),
            "str_price": str_price(credit.price, money_type=current_user.main_money)
        } for credit in CreditsTitaniumPrice.query.order_by(CreditsTitaniumPrice.order).all()],
        "creditsVipPrice":[ {
            "id": credit.id,
            "amount": credit.amount,
            "price": change_price(credit.price, money_type=current_user.main_money, rounded=False),
            "str_price": str_price(credit.price, money_type=current_user.main_money)
        } for credit in CreditsVipPrice.query.order_by(CreditsVipPrice.order).all()],
        "codes":codes
    }

@subscription_bp.route("/credits/<credits_type>/<credit_id>/buy/", methods=["POST"])
@jwt_required()
def buy_credits(credits_type, credit_id):
    model = CreditsVipPrice if credits_type == "vip" else CreditsTitaniumPrice if credits_type == "titanium" else None
    if not model:
        return {"error": "Invalid credits type"}, 400
    credit = model.query.get(credit_id)
    if not credit:
        return {"error": "Credit not found"}, 404
        

    price = change_price(credit.price, money_type=current_user.main_money, rounded=False)

    if price > current_user.wallet.main(current_user):
        return {"error": "Insufficient Balance"}, 400
    
    codes = generate_gift_code(current_user, credit.amount, credits_type)
    return SuccessResponse({ "msg": "Success process, verify your credits" })


@subscription_bp.route("/points/")
@jwt_required()
def points_():
    points = Config.get_points()
    data = { "price": change_price(points.options["price"], current_user.main_money),  "str_price": str_price(points.options["price"], current_user.main_money)}
    return data

@subscription_bp.route("/points/<int:amount>/buy/", methods=["POST"])
@jwt_required()
def buy_points(amount):
    points = Config.get_points()
    price = change_price(points.options["price"], current_user.main_money)
    if amount < 1:
        return {
            "status":False,
            "msg":"Cantidad de puntos no valida"
        }
    
    final_price = price * amount
    if final_price > current_user.wallet.main(current_user):
        return {
            "status":False,
            "msg":"Insuficiente dinero, recargue"
        }

    prize_wallet = current_user.prize_wallet
    current_user.wallet.add_amount(-final_price, current_user.main_money)
    prize_wallet.points += amount
    db.session.commit()
    return {
        "status":True,
        "msg":f"{amount} puntos comprados exitosamente"
    }
