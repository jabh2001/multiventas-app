from flask import Blueprint, request, g
from flask_jwt_extended import jwt_required, current_user
from libs.models import Platform, StreamingAccount, CompleteAccountRequest, Screen, User, ExpiredAccount, Supplier, RequestUserMoney, Wallet, User, db
from libs.schemas import PlatformSchema, StreamingAccountSchema, CompleteAccountRequestSchema, ScreenSchema, UserSchema, ExpiredAccountSchema, SupplierSchema
from services.general_service import save_file
from services.general_service import delete_file
from services.admin_service.platform_sales_services import get_complete_request
from services.admin_service.platform_sales_services import get_complete_account
from services.admin_service.platform_sales_services import create_streaming_account
from services.admin_service.platform_sales_services import renewal_streaming_account
from services.admin_service.platform_sales_services import reject_complete_account
from services.admin_service.platform_sales_services import set_complete_account
from services.general_service import convert_str_to_int
import os, datetime


platform_sales_bp = Blueprint('platform_sales_bp', __name__)

@platform_sales_bp.route("/platform/", methods=["GET", "POST"])
@platform_sales_bp.route("/platform/<platform_id>/", methods=["GET", "PUT"])
@jwt_required()
def platform(platform_id=None):
    platform_schema = PlatformSchema()
    if platform_id:
        platform = Platform.query.get(platform_id)
        if request.method == "PUT":
            try:
                platform_schema.load({ **request.form, "public":True if request.form["public"] == "1" else False  }, instance=platform)
                if request.files.get("img"):
                    delete_file(platform.file_name)
                    platform.file_name = save_file(request.files["img"], filename=request.form.get("slug"))
                db.session.add(platform)
                db.session.commit()
                return {
                    "platform":platform_schema.dump(platform),
                    "status":True
                }
            except Exception as e:
                return {
                    "status":False,
                    "msg":str(e)
                }
        return platform_schema.dump(platform)
    else:
        if request.method == "POST":
            try:
                platform = platform_schema.load({ **request.form })
                if request.files.get("img"):
                    platform.file_name = save_file(request.files["img"], filename=request.form.get("slug"))
                db.session.add(platform)
                db.session.commit()
                return {
                    "platform":platform_schema.dump(platform),
                    "status":True
                }
            except Exception as e:
                return {
                    "status":False,
                    "msg":str(e)
                }
        else:
            return platform_schema.dump(Platform.query, many=True)

@platform_sales_bp.route("/streaming-accounts/", methods=["GET", "POST"])
@platform_sales_bp.route("/streaming-accounts/<account_id>/", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def streaming_accounts(account_id=None):
    streaming_account_schema = StreamingAccountSchema()
    screen_schema = ScreenSchema()
    user_schema = UserSchema(only=("id", "username", "wsphone"))
    expired_schema = ExpiredAccountSchema()

    if account_id:
        account = StreamingAccount.query.get(account_id)
        if not account:
            return { "status":False, "msg":"Esa cuenta no existe en la base de datos" }
        screens_with_user = db.session.query(Screen, User).join(Screen.client, isouter=True).filter(Screen.account_id == account_id)
        expired_with_user = db.session.query(ExpiredAccount, User).join(ExpiredAccount.user, isouter=True).filter(ExpiredAccount.account_id == account_id)
        if request.method == "PUT":
            try:
                renewal_streaming_account(account, streaming_account_schema, request.json, g.today)
                return { "status":True, "msg":"Se ha renovado esta cuenta" }
            except Exception as e: 
                raise e
                return { "status":False, "msg":str(e) }
        if request.method == "DELETE":
            try:
                stmt1 = db.delete(StreamingAccount).filter(StreamingAccount.id == account_id)
                stmt2 = db.delete(Screen).filter(Screen.account_id == account_id)
                stmt3 = db.delete(ExpiredAccount).filter(ExpiredAccount.account_id == account_id)
                
                db.session.execute(stmt1)
                db.session.execute(stmt2)
                db.session.execute(stmt3)
                db.session.commit()
                return { "status":True, "msg":"Se ha eliminado esta cuenta" }
            except Exception as e: 
                raise e
                return { "status":False, "msg":str(e) }
        return {
            **streaming_account_schema.dump(account),
            "screens":[{**screen_schema.dump(screen), "user":user_schema.dump(user) if user else None} for screen, user in screens_with_user],
            "expired":[{**expired_schema.dump(expired), "user":user_schema.dump(user) if user else None} for expired, user in expired_with_user],
        }
    else:
        if request.method == "POST":
            try:
                account = create_streaming_account(request.json, current_user)
                for key, value in streaming_account_schema.dump(account).items():
                    print(f"{key=} {value=}")
                return { "status":True, "msg":"La cuenta se ha creado sin ningún problema" }
            except Exception as e: return { "status":False, "msg":str(e) }
        else:
            page = convert_str_to_int(request.args.get("page"), default_number=1)
            per_page = convert_str_to_int(request.args.get("size", 100), default_number=100)

            # is_renewal = db.text('(SELECT COUNT(*)>0 FROM expired_accounts WHERE expired_accounts.account_id = streaming_account.id)')
            is_renewal = (
                db.session.query(db.func.count(ExpiredAccount.id) > 0)
                .filter(ExpiredAccount.account_id == StreamingAccount.id)
                .label("is_renewal")
            )
            screen_count = (
                db.session.query(db.func.count(Screen.id))
                .filter(Screen.client_id.is_(None))
                .filter(Screen.account_id == StreamingAccount.id)
                .label("screen_count")
            )
            days_left = db.func.datediff(StreamingAccount.c_end_date(), g.today).label("days_left")
            query = db.session.query(StreamingAccount, is_renewal, screen_count, days_left)

            if request.args.get("inactive"):
                query = query.filter( db.not_(StreamingAccount.active))
                print("inactive")
            else:
                query = query.filter(StreamingAccount.active)
                print("active")
                
            if request.args.get("platform_id"):
                query = query.filter(StreamingAccount.platform_id == request.args.get("platform_id"))

            subquery = db.session.query(CompleteAccountRequest.account_id).filter(CompleteAccountRequest.account_id.is_not(None))
            query = query.filter(StreamingAccount.id.not_in(subquery)).order_by(db.desc(is_renewal)).order_by(days_left)
            paging = query.paginate(page=page, per_page=per_page, max_per_page=500, error_out=False)
            return {
                "last_page":paging.pages,
                "data":[ {
                    **streaming_account_schema.dump(account),
                    "renovar":is_renewal,
                    "screens":screen_count,
                    "days_left":days_left
                } 
                for account, is_renewal, screen_count, days_left in paging ]
            }

@platform_sales_bp.route("/screen/<screen_id>/", methods=["PUT"])
@platform_sales_bp.route("/screens/<screen_id>/", methods=["PUT"])
def update_screen(screen_id):
    screen = Screen.query.get(screen_id)
    screen_schema = ScreenSchema()
    if not screen:
        return {
            "status":False,
            "msg": "No existe la pantalla con el id {}".format(screen_id)
        }
    update_type = request.args["update_type"]
    if update_type == "date":
        try:
            start_date = datetime.date.fromisoformat(request.json["start_date"])
            end_date = datetime.date.fromisoformat(request.json["end_date"])
            screen.start_date = start_date
            screen.end_date = end_date
            db.session.commit()
            return {
                "status": True,
                "msg":"Fecha actualizada correctamente",
                "screen": screen_schema.dump(screen),
            }
        except Exception as e:
            return {
                "status": False,
                "msg":"La fecha no fue actualizada, " + str(e),
            }
    if update_type == "client":
        try:
            if screen.client:
                screen.client = None
                msg = "Cliente expulsado correctamente"
            else:
                user = User.query.filter(User.email == request.json["client_id"]).first()
                if not user:
                    raise Exception("El cliente establecido no existe")
                screen.client = user
                msg = "Cliente asignado correctamente"
            db.session.commit()
            return {
                "status": True,
                "msg":msg,
                "screen": screen_schema.dump(screen),
            }
        except Exception as e:
            return {
                "status": False,
                "msg":"El cliente no fué cambiado, " + str(e),
            }


    pass

@platform_sales_bp.route("/complete-account/", methods=["GET"])
@platform_sales_bp.route("/complete-account/<complete_account_id>/", methods=["GET", "PUT"])
@jwt_required()
def complete_account(complete_account_id=None):
    complete_account_schema = CompleteAccountRequestSchema()
    if complete_account_id:
        complete_account_req, user, wallet, platform, req_user_money = (
            db.session.query(CompleteAccountRequest, User, Wallet, Platform, RequestUserMoney)
            .join(CompleteAccountRequest.user)
            .join(User.wallet)
            .join(CompleteAccountRequest.platform)
            .join(
                RequestUserMoney,
                db.and_(
                    CompleteAccountRequest.id == RequestUserMoney.request_id,
                    RequestUserMoney.request_type=="complete_account"
                )
            ).filter(CompleteAccountRequest.id == complete_account_id).first()
        )
        if request.method == "PUT":
            try:
                msg = None
                if request.json["method"] == "reject":
                    msg = reject_complete_account(complete_account_req, request.json["description"], user, wallet, platform, req_user_money, g.today)
                elif request.json["method"] == "accept":
                    msg = set_complete_account(request.json, complete_account_req, user, platform, req_user_money, g.today)
                elif request.json["method"] == "edit":
                    complete_account_req.account.email = request.json["email"]
                    complete_account_req.account.password = request.json["password"]

                    complete_account_req.account.start_date = datetime.date.fromisoformat(request.json["start_date"])
                    complete_account_req.account.days = int(request.json["days"])
                    complete_account_req.account.price = float(request.json["price"])
                    complete_account_req.account.afiliated_price = float(request.json["afiliated_price"])
                    db.session.commit()
                    msg = "Se ha actualizado la informacion correctamente"
                return { 
                    "status":True,
                    "msg":msg or "Hubo un error al enviar el metodo de acción"
                }
            except Exception as e: 
                raise e
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return {}
    else:
        page = convert_str_to_int(request.args.get("page"), default_number=1)
        per_page = convert_str_to_int(request.args.get("size", 20), default_number=20)

        filtro = request.args.get("filter", "normal")
        sort_field = request.args.get("sort[0][field]")
        sort_dir = request.args.get("sort[0][dir]")

        return (
            get_complete_account(page, per_page, sort_field, g.today) if filtro == "verified" else
            get_complete_account(page, per_page, sort_field, g.today) if filtro == "reject" else get_complete_request()
        )


@platform_sales_bp.route("/supplier/", methods=["GET", "POST"])
@platform_sales_bp.route("/supplier/<supplier_id>/", methods=["GET", "PUT"])
@jwt_required()
def supplier(supplier_id=None):
    supplier_schema = SupplierSchema()
    if supplier_id:
        instance = Supplier.query.get(supplier_id)
        if not instance:
            return {
                "msg":"supplier not found"
            }, 404
        if request.method == "PUT":
            try:
                supplier_schema.load(request.json, instance=instance)
                instance.save_me()
                return { 
                    "status":True,
                    "msg":"Proveedor editado correctamente",
                    "supplier":supplier_schema.dump(instance),
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return supplier_schema.dump(instance)
    else:
        if request.method == "POST":
            try:
                instance = supplier_schema.load(request.json )
                instance.save_me()
                return { 
                    "status":True,
                    "msg":"Proveedor agregado correctamente",
                    "supplier":supplier_schema.dump(instance),
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return supplier_schema.dump(Supplier.query, many=True)