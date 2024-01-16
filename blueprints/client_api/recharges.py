from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from libs.models import RechargeRequest, PaymentMethod, db
from libs.schemas import RechargeRequestSchema, PaymentMethodSchema

# BLUEPRINTS
recharges_bp = Blueprint('recharges_bp', __name__)

@recharges_bp.route('/')
@jwt_required()
def index():
    recharges =  db.session.query(RechargeRequest, PaymentMethod)\
            .join(PaymentMethod, PaymentMethod.id == RechargeRequest.payment_method_id)\
            .filter(RechargeRequest.id > 0)\
            .filter(RechargeRequest.user_id == current_user.id).all()
    ret = []
    for recharge, payment_method in recharges:
        ret.append({
            "id":recharge.id,
            "reference":recharge.reference,
            "date":recharge.date.strftime("%d-%m-%Y %H:%M"),
            "payment_data":payment_method.payment_platform_name,
            "amount":f"{recharge.amount} {payment_method.money_type}",
            "status":recharge.status,
            
        })
    return ret

@recharges_bp.route('/', methods=["POST"])
@jwt_required()
def post():
    errors : dict()
    try: payment_method = int(request.json.get("method", 0))
    except: 
        payment_method = 0
        errors["payment_method"] = "-Error al ingresar el método de pago"

    try: amount = float(request.json.get("amount", 0))
    except: 
        amount = 0.0
        errors["amount"] = "-Error al ingresar la cantidad no puede ser cero"

    try: 
        code = request.json.get("code", "")
        int(code)
        if len(code) != 4: 
            raise Exception("La referencia debe contener 4 digitos")
    except Exception as e: 
        code = 0
        errors["code"] = str(e)

    if not payment_method or not amount>0 or not code:
        return jsonify({"status":False, "errors":errors})
    recarga = RechargeRequest.revisarDuplicados(code, amount=amount, payment_method_id=payment_method, user=current_user)
    if not recarga:
        return jsonify({"status":False, "error":"Recarga repetida, debe esperar a que la anterior sea procesada"})
    revision = recarga.revisarEstafaRepetido()
    return jsonify(revision)

@recharges_bp.route('/payment-method/')
# @jwt_required()
def get():
    payment_methods = PaymentMethod.query.filter(PaymentMethod.id > 0).all()
    schema = PaymentMethodSchema(many=True, exclude=("file_name",))
    return schema.dump(payment_methods)
