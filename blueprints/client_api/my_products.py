from werkzeug.http import HTTP_STATUS_CODES
from flask import Blueprint, request, g
from libs.models import UserProducts, CompleteAccountRequest, Screen, StreamingAccount, Platform, User, db
from libs.schemas import UserProductsSchema, CompleteAccountRequestSchema, ScreenSchema
from flask_jwt_extended import jwt_required, current_user
from services.clientService.my_products_service import format_user_products_data, format_complete_account_data, format_screen_data, get_query_with_dependencies, renew_screen as renew_screen_services, renew_complete_account as renew_complete_account_services
from services.clientService.products_service import streaming_account_final_price, platform_final_price
from services.money_change_service import change_price, str_price
from services.responsesService import SuccessResponse, ErrorResponse
# BLUEPRINTS
my_products_bp = Blueprint('my_products_bp', __name__)


@my_products_bp.route('/')
@jwt_required()
def index():
    querys = get_query_with_dependencies(current_user.id, g.today)
    return {
        "product_by_requests": [format_user_products_data(*row) for row in querys["UserProducts"]],
        "complete_accounts": [format_complete_account_data(g.today, *row) for row in querys["CompleteAccountRequest"]],
        "screens": [format_screen_data(g.today, *row) for row in querys["Screen"]]
    }


@my_products_bp.route("/renew/screen/<id>/", methods=["GET", "POST"])
@jwt_required()
def renew_screen(id):
    screen, account, platform = db.session.query(Screen, StreamingAccount, Platform)\
                                .select_from(Screen)\
                                .join(Screen.account)\
                                .join(StreamingAccount.platform)\
                                .filter(Screen.id == id)\
                                .filter(StreamingAccount.active == True)\
                                .first()
    if not screen:
        return ErrorResponse("Esta pantalla no existe")

    wallet = current_user.wallet
    final_price = streaming_account_final_price(account, g.today, current_user.is_afiliated(), apply_time_discount=False)
    final_price = change_price(final_price, current_user.main_money, rounded=True)

    if screen.client_id == None or screen.client_id != current_user.id:
        return ErrorResponse(400, "No puedes renovar esta cuenta, ya que no es tuya")
    elif wallet.main(current_user) - final_price < 0:
        return ErrorResponse(400, f"Usted no cuenta con suficiente dinero para renovar su pantalla necesita por lo menos {final_price} Bs, por favor recargue")
    elif request.method == "POST":
        return renew_screen_services(screen, g.today, current_user, wallet, account, platform)
    main_money = current_user.main_money
    return SuccessResponse({
        "msg":"El precio es {} bs, y usted tiene {} bs Va a renovar su cuenta por {} d&iacute;as m&aacute;s.</br></br>¿Esta seguro?"
                .format(str_price(final_price, main_money, change_price_=False), str_price(wallet.main(current_user), main_money, change_price_=False), account.duration_days().days)
    })
    


@my_products_bp.route("/renew/complete_account/<id>/", methods=["GET", "POST"])
@jwt_required()
def renew_complete_account(id):
    # complete = CompleteAccountRequest.query.filter(CompleteAccountRequest.id == id).first()
    
    complete, account, platform = db.session.query(CompleteAccountRequest, StreamingAccount, Platform)\
                                .select_from(CompleteAccountRequest)\
                                .join(CompleteAccountRequest.account)\
                                .join(StreamingAccount.platform)\
                                .filter(CompleteAccountRequest.id == id)\
                                .first()
    if not complete:
        return ErrorResponse("Esta cuenta no existe")

    wallet = current_user.wallet
    final_price = platform_final_price(platform=platform, is_afiliated=current_user.is_afiliated())
    final_price = change_price(final_price, current_user.main_money, rounded=False)

    if complete.user_id != current_user.id:
        return ErrorResponse("No puedes renovar esta cuenta, ya que no es tuya")
    elif wallet.main(current_user) - final_price < 0:
        return ErrorResponse(f"Usted no cuenta con suficiente dinero para renovar su pantalla necesita por lo menos {final_price} Bs, por favor recargue")
    elif request.method == "POST":
        return renew_complete_account_services(complete, g.today, current_user, wallet, account, platform)
    main_money = current_user.main_money
    return SuccessResponse({
        "msg":"El precio es {}, y usted tiene {} bs Va a renovar su cuenta por {} d&iacute;as m&aacute;s.</br></br>¿Esta seguro?"
                .format(str_price(final_price, main_money, change_price_=False), str_price(wallet.main(current_user), main_money, change_price_=False), account.duration_days().days)
    })


@my_products_bp.route("/renew/dynamic/")
@jwt_required()
def renew_dynamic(id):
    return {"status": False, "error": "este metodo no esta implementado"}
