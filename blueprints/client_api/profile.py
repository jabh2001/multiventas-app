from flask import Blueprint, request
from flask_jwt_extended import jwt_required, current_user
from libs.models import Notifications, BuyHistory, RechargeRequest, db
from libs.schemas import UserSchema, NotificationsSchema, BuyHistorySchema, RechargeRequestSchema
from services.responsesService import SuccessResponse, ErrorResponse


# BLUEPRINTS
profile_bp = Blueprint('profile_bp', __name__)

def child_JSON(buy_history, username, schema:BuyHistorySchema):
    data = schema.dump(buy_history)
    return {
        **data,
        "utilities":buy_history.references_reward,
        "username":username
    }

def utilities_JSON(history):
    return {
        "id":history.id,
        "date":history.date.strftime("%d-%m-%Y"),
        "amount":history.amount,
        "money_type":history.reference,
        "description":history.status.replace("_", " ").capitalize()
    }

@profile_bp.route("/movements/")
@jwt_required()
def movements():
    buy_schema = BuyHistorySchema()
    buy_history = BuyHistorySchema(many=True).dump(BuyHistory.all_of_user(current_user))
    child_history = [ child_JSON(history, user.username, buy_schema) for history, user in BuyHistory.all_of_child(current_user)]
    utilities_history = [ utilities_JSON(history) for history in RechargeRequest.utilities_movements(current_user)]
    return  {
        "buy_history":buy_history,
        "child_history":child_history,
        "utilities_history":utilities_history
    }

@profile_bp.route("/utilities/", methods=["POST"])
@jwt_required()
def utilities():
    response = ""
    try:
        action = request.json["actionSelect"]
        amount = float(request.json["amount"])
        money_type = request.json["money_type"]
        wallet = current_user.wallet
        if not 0 < amount <= wallet.main_balance(current_user):
            raise Exception("Ingrese un cantidad valida que no exceda sus utilidades ni sea menor a cero")

        if action == "wallet":
            if amount > 0:
                wallet.balanceToAmount(amount=amount, money_type=money_type)
                response = SuccessResponse({"msg":"Se ha trapasado correctamente {} bs de sus utilidades a su billetera".format(amount)})
            else:
                response = ErrorResponse("Cantidad no valida para transferir")
        elif action == "pagomovil":
            if not current_user.ci:
                raise Exception("No tienes una cédula registrada")

            banco = request.json["banco"]
            phone = request.json["phone"]

            if money_type == "bs":
                if (len(banco) != 4):  raise Exception("El campo de banco debe ser un codigo de 4 digitos")
                try:int(banco) 
                except ValueError: raise Exception("El codigo del banco debe ser solamente numeros, sin signos, ni guiones ejemplo: 0102")

                if (len(phone) != 11): raise Exception("El telefono debe ser 11 digitos solamente,")
                try:int(phone) 
                except ValueError: raise Exception("El telefono debe ser solamente numeros, sin signos, ni guiones")
            else:
                banco = "-"

            wallet.balanceToPagoMovil(user_id = current_user.id, phone=phone, banco=banco, amount=amount, money_type=money_type)
            response = SuccessResponse({"msg":"Su peticion ha sido enviada correctamente"})

    except KeyError as e:
        response = { "error":"ERROR\nCampos no rellenados correctamente", "status":False }
    except ValueError as e:
        response = { "error":"Error inesperado, la cantidad deben ser un número valido", "status":False }
    except Exception as e:
        response = { "error":str(e), "status":False }
    return response
    
@profile_bp.route("/childs/")
@jwt_required()
def childs():
    childs = current_user.childs() or []
    return UserSchema(only = ("username", "email", "phone"), many=True).dump(childs)

@profile_bp.route("/main-money/", methods=["PUT"])
@jwt_required()
def main_money():
    availableOptions = "bs","usd","cop","sol","mxn"
    request_main_money = request.json["main_money"]
    selected = request_main_money if request_main_money in availableOptions else current_user.main_money
    if(current_user.main_money != selected):
        current_user.main_money = selected
        current_user.save_me()
    return SuccessResponse({ "msg":"Todo bien"})


@profile_bp.route("/notifications/", methods=["GET", "DELETE"])
@jwt_required()
def notifications():
    if request.method == "DELETE":
        print()
        notification_id = request.args.get("notification_id")
        notification = Notifications.query.get(notification_id)
        if notification:
            notification.showed=1
            notification.save_me()
    notifications = Notifications.query.filter(Notifications.user_id == current_user.id)\
        .filter(Notifications.showed == 0)\
        .order_by(Notifications.id.desc())\
        .limit(5)\
        .all()
    return {
        "notifications":NotificationsSchema(many=True).dump(notifications)
    }