from flask import Blueprint, request, g
from flask_jwt_extended import jwt_required, current_user
from libs.models import RechargeRequest, User, Wallet, PaymentMethod, RechargeAlerts, PagoMovilRequest, db
from libs.schemas import RechargeRequestSchema, UserSchema, PaymentMethodSchema, PagoMovilRequestSchema, db
from services.admin_service.transactions_services import get_transfers
from services.admin_service.transactions_services import get_verified_transfers
from services.admin_service.transactions_services import get_duplicate_transfers
from services.admin_service.transactions_services import format_recharges_entries
from services.admin_service.transactions_services import format_duplicate_entries
from services.admin_service.transactions_services import approve_recharge
from services.admin_service.transactions_services import reject_recharge
from services.admin_service.transactions_services import get_pago_movil
from services.admin_service.transactions_services import get_verified_pago_movil
from services.admin_service.transactions_services import format_pago_movil_entries
from services.admin_service.transactions_services import approve_pago_movil
from services.admin_service.transactions_services import reject_pago_movil
from services.responsesService import SuccessResponse, ErrorResponse 
from services.general_service import notify_user

transactions_bp = Blueprint('transactions_bp', __name__)

def convert_str_to_int(num:str, default_number:int = 0):
    try:
        return int(num)
    except:
        return default_number

@transactions_bp.route("/transfers/")
@jwt_required()
def transfers():
    page = convert_str_to_int(request.args.get("page"), default_number=1)
    per_page = convert_str_to_int(request.args.get("size", 100), default_number=100)
    verified = request.args.get("verified", None)
    verified = verified if verified in ["true", "false"] else "false"
    if verified == "true":
        all_transfers = get_verified_transfers(page, per_page) 
        return {
            "last_page":all_transfers.pages,
            "data":format_recharges_entries(all_transfers)
        }
    return format_recharges_entries(get_transfers(), verified=False)

@transactions_bp.route("/recharge-request/<recharge_id>/", methods=["PUT"])
@jwt_required()
def transfers_post(recharge_id):
    recharge, payment_method, user, wallet = db.session.query(RechargeRequest, PaymentMethod, User, Wallet)\
                                            .join(RechargeRequest.user)\
                                            .join(RechargeRequest.payment_method)\
                                            .join(User.wallet)\
                                            .filter(RechargeRequest.id == recharge_id).first()
    option = request.json.get("option")

    response = None
    if option == 'approved':
        response = approve_recharge(recharge, payment_method, wallet)
    elif option == 'rejected':
        response = reject_recharge(recharge, payment_method)

    if response:
        notify_user(user, g.today, response["msg"])
        return SuccessResponse({
            "msg":"La solicitud se ha procesado"
        })
    else:
        return ErrorResponse("La solicitud no pudo ser procesada")

@transactions_bp.route("/recharge-alerts/<recharge_id>/" )
@jwt_required()
def recharge_alerts(recharge_id):
    return format_duplicate_entries( get_duplicate_transfers(recharge_id))

@transactions_bp.route("/payment-method/", methods=["GET", "POST"] )
@transactions_bp.route("/payment-method/<payment_id>/", methods=["GET", "PUT"])
@jwt_required()
def payment_method(payment_id=None):
    payment_schema = PaymentMethodSchema()
    if payment_id:
        payment_method = PaymentMethod.query.get(payment_id)
        if request.method == "PUT":
            payment_schema.load({ **request.json }, instance=payment_method)
            db.session.commit()
        return payment_schema.dump(payment_method)
    else:
        if request.method == "POST":
            method = payment_schema.load({ **request.json })
            db.session.add(method)
            db.session.commit()
            return payment_schema.dump(method)
        else:

            return payment_schema.dump(PaymentMethod.query, many=True)

@transactions_bp.route("/pago-movil/", methods=["GET"] )
@transactions_bp.route("/pago-movil/<pago_id>/", methods=["GET", "PUT"])
@jwt_required()
def pago_movil(pago_id=None):
    pago_movil_schema = PagoMovilRequestSchema()
    if pago_id:
        pagomovil, user, wallet = db.session.query(PagoMovilRequest, User, Wallet).join(PagoMovilRequest.user).join(User.wallet).filter(PagoMovilRequest.id == pago_id).first()

        option = request.json.get("option")
        referencia = request.json.get("referencia")

        response = None
        if option == 'approved':
            response = approve_pago_movil(pagomovil, g.today, referencia)
        elif option == 'rejected':
            response = reject_pago_movil(pagomovil, wallet)

        if response:
            notify_user(user, g.today, response["msg"])
            return SuccessResponse({
                "msg":"La solicitud se ha procesado"
            })
        else:
            return ErrorResponse("La solicitud no pudo ser procesada")
    else:
        page = convert_str_to_int(request.args.get("page"), default_number=1)
        per_page = convert_str_to_int(request.args.get("size", 100), default_number=100)
        verified = request.args.get("verified", None)
        verified = verified if verified in ["true", "false"] else "false"
        

        if verified == "true":
            all_pago_movil = get_verified_pago_movil(page, per_page) 
            return {
                "last_page":all_pago_movil.pages,
                "data":format_pago_movil_entries(all_pago_movil)
            }
        return format_pago_movil_entries(get_pago_movil())