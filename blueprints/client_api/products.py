from flask import Blueprint, request, jsonify, g
from libs.models import Platform, StreamingAccount, ProductsByRequest, User, Coupon, Category, ProductCategories, BuyHistory, RequestUserMoney, GoogleDriveCategories, GoogleDriveProduct
from libs.schemas import PlatformSchema, StreamingAccountSchema, ScreenSchema, CategorySchema, GoogleDriveCategoriesSchema, GoogleDriveProductSchema
from flask_jwt_extended import jwt_required, current_user
from services.responsesService import ErrorResponse, SuccessResponse
from services.money_change_service import str_price, change_price
from services.clientService.products_service import streaming_account_final_price
from services.clientService.products_service import streaming_account_final_reward
from services.clientService.products_service import product_final_price
from services.clientService.products_service import product_config_json
from services.clientService.products_service import platform_format_json
from services.clientService.products_service import product_format_json
from services.clientService.products_service import get_account_diff_day
from services.clientService.products_service import buy_screen
from services.clientService.products_service import request_complete_account
from services.clientService.products_service import request_products_by_request

# BLUEPRINTS
products_bp = Blueprint('products_bp', __name__)


@products_bp.before_request
def users_before_request():
    g.coupon = Coupon.query.get( request.headers.get("Vip-Cuopon", ""))

def create_str_price(user=None):
    money_type=user.main_money if user else "bs"
    return lambda price: str_price(price=price, money_type=money_type)
def create_number_price(user=None):
    money_type=user.main_money if user else "bs"
    return lambda price: change_price(price, money_type=money_type, rounded=False)
    
@products_bp.route('/')
@jwt_required(optional=True)
def index():
    categories=request.args.get("categories", "").split(",")
    products_categories = ProductCategories.query.filter(ProductCategories.category_id.in_(categories)).all()
    products_ids = [p.product_id for p in products_categories if p.product_type == "product"]
    platforms_ids = [p.product_id for p in products_categories if p.product_type == "platform"]
    
    convert_str=create_str_price(current_user)
    
    platforms_query=Platform.all_with_price()
    products_query= ProductsByRequest.query.filter(ProductsByRequest.public==1)
    if len(request.args.get("categories", ""))>0:
        platforms_query = platforms_query.filter(Platform.id.in_(platforms_ids))
        products_query = products_query.filter(ProductsByRequest.id.in_(products_ids))

    platforms_unique_id = set()

    ret = {"all_products": [] }
    is_afiliated = current_user and current_user.is_afiliated()
    for platform, account, in_buy in platforms_query:
        if platform.id not in platforms_unique_id:
            platforms_unique_id.add(platform.id)
            price = streaming_account_final_price(account, g.today, is_afiliated, convert_str=convert_str)
            ret["all_products"].append(platform_format_json(platform, price, 0, 0, 0, in_buy))
    for product in products_query.all():
        try:
            price = product_final_price(product, is_afiliated=is_afiliated, convert_str=convert_str)
            ret["all_products"].append(product_format_json(product, price=price))
        except:
            prices = product.price[0] if product.price_is_list() else product.price
            print(f"{product.title_slug}, {prices}".center(150, "*"))
    return ret

@products_bp.route('/categories/')
def categories():
    return {
        "categories":CategorySchema(many=True).dump(Category.query.all())
    }


def account_json(account, money_type, user=None, coupon:Coupon=None):
    is_afiliated = user and user.is_afiliated()
    response =  {
        "id": account.id,
        "days_left": (account.end_date - g.today).days,
        "start_date": account.start_date.strftime("%d-%m-%Y"),
        "end_date": account.end_date.strftime("%d-%m-%Y"),
        "price": streaming_account_final_price(account, g.today, is_afiliated, convert_str=create_str_price(current_user)),
        "number_price": streaming_account_final_price(account, g.today, is_afiliated, convert_str=create_number_price(current_user), coupon=coupon),
        "reference_reward": streaming_account_final_reward(account, g.today, convert_str=create_str_price(current_user))
    }
    
    if coupon and coupon.verify_resource(account.coupon_resource(coupon.level)):
        response["price"] = streaming_account_final_price(account, g.today, is_afiliated, convert_str=create_str_price(current_user), coupon=coupon)
        response["old_price"] = streaming_account_final_price(account, g.today, is_afiliated, convert_str=create_str_price(current_user))
        # response["price"] = User.str_price(user, account.final_price(user=user, coupon=g.coupon))
        # response["old_price"] = User.str_price(user, account.final_price(user=user))
    else:
        response["price"] = streaming_account_final_price(account, g.today, is_afiliated, convert_str=create_str_price(current_user))
        # response["price"] = User.str_price(user, account.final_price(user=user))
    return response

@products_bp.route("/platform/<platform_id>/")
@jwt_required(optional=True)
def platform(platform_id):
    money_type=current_user.main_money if current_user else "bs"
    platform = Platform.query.filter(Platform.id == platform_id).first()

    streaming_accounts = get_account_diff_day(platform_id, g.today)
    platformJSON = platform_format_json(
        platform, 
        str_price(price=platform.price, money_type=money_type),
        change_price(platform.price, money_type=money_type, rounded=False),
        str_price(price=platform.year_price, money_type=money_type),
        change_price(platform.year_price, money_type=money_type, rounded=False),
    )

    return {
        "platform": platformJSON,
        "streaming_accounts": [account_json(account, money_type, user=current_user, coupon=g.coupon) for account in streaming_accounts]
    }


@products_bp.route("/request/<slug>/")
@jwt_required(optional=True)
def request_(slug):
    is_afiliated = current_user and current_user.is_afiliated()
    convert_str=create_str_price(current_user)

    productModel = ProductsByRequest.query.filter(ProductsByRequest.title_slug == slug).first()
    product = product_format_json(productModel, 0)
    config = product_config_json(productModel, is_afiliated, convert_str, create_number_price(current_user), g.coupon)
    
    return jsonify({
        "product":product,
        "config":config
    })


@products_bp.route("/buy/<option>/", methods=["GET", "POST"])
@jwt_required()
def buy(option):
    wallet = current_user.wallet
    is_afiliated = current_user and current_user.is_afiliated()
    if option.lower() == "screen":
        account_id =  request.args.get("account_id")

        if account_id == None: 
            account = StreamingAccount.query.order_by(StreamingAccount.end_date.desc()).first()
        else:
            account = StreamingAccount.query.filter(StreamingAccount.id == account_id).first()

        final_price = streaming_account_final_price(account, g.today, is_afiliated, coupon=g.coupon)
        main_wallet = wallet.main(current_user)
        
        if main_wallet - final_price < 0:
            return ErrorResponse(400, "Saldo insuficiente, por favor recargue su saldo y luego vuelva a pedir su pantalla")
        elif request.method == "POST":
            screen = buy_screen(account=account, today=g.today, user=current_user, is_afiliated=is_afiliated, coupon=g.coupon)
            if screen == False: 
                return ErrorResponse(400, "Esta cuenta no tiene pantallas disponibles, por favor vuelve a intentarlo")
            else:
                return SuccessResponse({
                    "msg":"Su compra ha sido satisfactoria",
                    "buy_data":{
                        "screen":ScreenSchema().dump(screen),
                        "account":StreamingAccountSchema().dump(account),
                        "platform":PlatformSchema().dump(account.platform),
                    }
                })
        else:
            final_price = str_price(final_price, current_user.main_money)
            main_wallet = str_price(wallet.main(current_user), current_user.main_money, change_price_=False)
            days_left = account.days_left()
            return SuccessResponse({"msg":"El precio es {} bs, y usted tiene {} bs Va a comprar su cuenta por {} días. ¿Esta seguro?".format(final_price, main_wallet, days_left) })
    elif option.lower() == "complete":
        platform_id = request.args.get("platform")
        account_type = request.args.get("type")
        if not account_type or not account_type in ("month", "year"):
            return ErrorResponse(400, "Tiempo no aceptado")
        platform = Platform.query.get(platform_id)
        
        if request.method == "POST":
            try:
                return request_complete_account(platform, g.today, current_user, is_afiliated, g.coupon, account_type=account_type)
            except Exception as e:
                return ErrorResponse(400, str(e))
        return ErrorResponse(400, "Metodo no soportado")
    elif option.lower() == "product":
        slug =  request.args.get("slug")
        p = ProductsByRequest.query.filter_by(title_slug=slug).first()
        if not p: return ErrorResponse(400, "Ese producto no existe")
        compra = request_products_by_request(p, request.form, current_user, is_afiliated, g.coupon)
        if compra: return SuccessResponse({ "msg": "Su pedido se ha realizado, pronto se le notificará"})
        else: return ErrorResponse(400, "Este producto sobrepasa tu presupuesto por favor recarga")


@products_bp.route("/check-coupon/<coupon_code>/")
@jwt_required()
def check_coupon(coupon_code):
    coupon = Coupon.query.get(coupon_code) 
    if not coupon:
        return {
            "is_valid_coupon": False,
            "msg":"Ese cupón no existe en la base de datos"
        }
    uses = BuyHistory.query.filter(BuyHistory.coupon_code == coupon_code).filter(BuyHistory.user_id == current_user.id).count()
    request_uses = RequestUserMoney.query\
        .filter(RequestUserMoney.coupon_code == coupon_code)\
        .filter(RequestUserMoney.user_id == current_user.id).count()
    total_uses=uses+request_uses
    if total_uses >= coupon.uses:
        return {
            "is_valid_coupon": False,
            "msg":"Ya haz usado muchas veces este cupón"
        }
    return {
        "is_valid_coupon": True,
        "msg":"Cupón aplicado"
    }

@products_bp.route("/platinum-categories/")
@products_bp.route("/platinum-category/")
def platinum_categories():
    schema = GoogleDriveCategoriesSchema(exclude=("products", ), many=True)
    return schema.dump(GoogleDriveCategories.query)

@products_bp.route("/platinum-product/")
@products_bp.route("/platinum-products/")
@products_bp.route("/platinum-product/<category_id>/")
@products_bp.route("/platinum-products/<category_id>/")
def platinum_product(category_id = None):
    schema = GoogleDriveProductSchema(many=True)
    query = GoogleDriveProduct.query
    category = GoogleDriveCategories.query.get(category_id)
    if category:
        query = category.products
    return schema.dump(query)

# def deleteNotusage():
#     img_path = []
#     for lista in all.values():
#         for product in lista:
#             img_path.append(product.get("file_name"))
#     for img in os.listdir(path="static/img/"):
#         if img not in img_path:
#             os.remove(path="static/img/"+img)
#     pass
