from flask import Blueprint, request, Response
from flask_jwt_extended import jwt_required, current_user
from marshmallow import ValidationError
from libs.models import User, Wallet, RechargeRequest, BuyHistory, db
from libs.schemas import UserSchema, WalletSchema, BuyHistorySchema, GoogleDataSchema
from services.general_service import convert_str_to_int
from services.admin_service.clients_services import wsphone
from services.admin_service.clients_services import convert_clientlist_to_xlsx
from services.admin_service.clients_services import convert_client_list_with_buy_count_to_xlsx

fields_names = {
    "username":"Nombre de usuario",
    "email":"Correo",
    "password":"Contraseña",
    "phone":"Teléfono",
}

clients_bp = Blueprint('clients_bp', __name__)

@clients_bp.route('/user/', methods=["GET", "POST"])
@clients_bp.route('/users/', methods=["GET", "POST"])
@clients_bp.route("/user/<user_id>/", methods=["GET", "PUT"])
@clients_bp.route("/users/<user_id>/", methods=["GET", "PUT"])
@jwt_required()
def user_(user_id = None):
    if user_id:
        user, wallet = db.session.query(User, Wallet).join(User.wallet).filter(User.id == user_id).first()
        user_schema = UserSchema(exclude=("access_token",))
        wallet_schema = WalletSchema()
        buy_history_schema = BuyHistorySchema(many=True)
        google_data_schema = GoogleDataSchema()
        if request.method == "PUT":
            try:
                msg = "No se ha hecho nada"
                copy_data = request.json.copy()
                new_data = dict()

                if request.args.get("edit") == "data":
                    copy_data.pop("wallet")
                    copy_data.pop("link")
                    copy_data.pop("wsphone")
                    for key,value in copy_data.items():
                        if key in ["username", "email", "password", "phone", "ci"] and getattr(user, key) != value:
                            new_data[key] = value
                    if new_data:
                        user_schema.load(new_data, instance=user, partial=True)
                        msg="Se ha actualizado la informacion del usuario"
                    else:
                        msg="No ha cambiado la informacion del usuario"

                if request.args.get("edit") == "wallet":
                    for key,value in copy_data.items():
                        if getattr(wallet, key) != value:
                            new_data[key] = value
                    if new_data:
                        wallet_schema.load(new_data, instance=wallet, partial=True)
                        msg="Se ha actualizado la informacion de la billetera"
                    else:
                        msg="No ha cambiado la informacion del usuario"
                
                if "edit" in request.args:
                    db.session.commit()
                return {
                    "status":True,
                    "msg":msg
                }
            except Exception as e:
                # raise e
                return {
                    "status":False,
                    "msg":str(e)
                }
        return {
            **user_schema.dump(user),
            "wsphone":wsphone(user.phone),
            "wallet":wallet_schema.dump(wallet),
            "buy_history":buy_history_schema.dump(user.buy_historys),
            "google_data":google_data_schema.dump(user.google_data),
        }
    else:
        if request.method == "POST":
            try:
                user_schema = UserSchema( exclude=["access_token"])
                wallet_schema = WalletSchema()

                user_data = request.json
                wallet_data = user_data["wallet"]
                if "id" in wallet_data:
                    wallet_data.pop("id")
                data = {
                    "user_type":"client",
                    "username": user_data.get("username", None),
                    "email": user_data.get("email", None),
                    "password": user_data.get("password", None),
                    "phone": user_data.get("phone", None) or None,
                    "ci": user_data.get("ci", None) or None,
                    "is_valid_email":True,
                }
                
                
                user = User(**data)
                wallet = wallet_schema.load(wallet_data)
                user.wallet = wallet

                db.session.add_all([user, wallet])
                db.session.commit()

                return {
                    "status":True,
                    "msg":"El cliente se ha registrado",
                    # "user": user_schema.dump(user)
                }
            except ValidationError as ve:
                error_msg = []
                for field, errors in ve.messages.items():
                    field_name = fields_names[field]
                    for e in errors:
                        error_msg.append(f"{field_name} - {e}")
                return {
                    "status":False,
                    "errors":error_msg,
                    "msg":error_msg,
                }
            except Exception as e:
                return {
                    "status":False,
                    "msg": f"Error al crear el usuario {str(e)}"
                }

        page = convert_str_to_int(request.args.get("page"), default_number=1)
        per_page = convert_str_to_int(request.args.get("size", 50), default_number=50)
        user_schema = UserSchema(only=("id","username", "email", "phone"))
        wallet_schema = WalletSchema()
        q = request.args.get("q")
        query = (
            db.session.query(
                User,
                db.session.query(
                    db.func.date_format(RechargeRequest.date, "%Y-%m-%d")
                )
                .filter(RechargeRequest.user_id == User.id)
                .filter(RechargeRequest.status == "verificado")
                .order_by(RechargeRequest.date.desc())
                .limit(1)
                .label("last_recharge")
            )
        )
        
        if q:
            q = q
            query = (
                query.filter(
                    db.or_(
                        User.id == q,
                        User.username.like(f"%{q}%"),
                        User.email.like(f"%{q}%"),
                        User.phone.like(f"%{q}%"),
                        User.ci.like(f"%{q}%"),
                    )
                )
            )
            
            

        query = (
            query
            .filter(User.user_type == "client")
            .order_by(db.desc(User.id))
            .paginate(page=page, per_page=per_page, max_per_page=2000, error_out=False)
        )
        return {
            "last_page":query.pages,
            "data":[{
                **user_schema.dump(user),
                "last_recharge":last_recharge,
            } for user, last_recharge in query]
        }
"""

SELECT user.*, COUNT(buy_history.user_id) compras FROM user 
JOIN buy_history ON user.id = buy_history.user_id
WHERE user.user_type = "client" AND buy_history.product IN ("platform", "product") AND username LIKE "%gabriel%"
GROUP BY buy_history.user_id;
"""
@clients_bp.route('/download/<mode>/')
def download(mode = "all"):
    if mode == "5-buy":
        query = (
            db.session.query(User, db.func.count(BuyHistory.user_id))
            .join(User.buy_historys)
            .filter(User.user_type == "client")
            .filter(BuyHistory.product.in_(["platform", "product"]))
            .group_by(BuyHistory.user_id)
        )
        return convert_client_list_with_buy_count_to_xlsx(query)
    query = User.query.filter(User.user_type == "client")
    if mode == "all":
        query = query.all()
    if mode == "refer":
        query = (
            query
            .filter(
                User.id.in_(
                    db.session.query(User.parent_id.distinct())
                    .filter(User.parent_id.is_not(None))
                ))
            .all()
        )
    if mode == "not-refer":
        query = (
            query
            .filter(
                User.id.not_in(
                    db.session.query(User.parent_id.distinct())
                    .filter(User.parent_id.is_not(None))
                ))
            .all()
        )
    if mode == "not-buy":
        query = (
            query
            .filter(
                User.id.in_(
                    db.session.query(BuyHistory.user_id.distinct())
                    .filter(BuyHistory.user_id.is_not(None))
                ))
            .all()
        )

    return convert_clientlist_to_xlsx(query)