from libs.models import Platform, StreamingAccount, Screen, CompleteAccountRequest, ProductsByRequest, Coupon, BuyHistory, User, RequestUserMoney, UserProducts, Lottery, db
from services.responsesService import ErrorResponse, SuccessResponse
from services.money_change_service import change_price

f"""
Este metodo retorna el precio final de un producto tomando en cuenta el producto y si el usuario es afiliado
"""


def product_final_price(product_by_request, priceIndex=0, is_afiliated=False, show_afiliated_price=True, convert_str=None, coupon:Coupon=None):
    parser_price=convert_str or float
    if not show_afiliated_price:
        is_afiliated = False
    prices = product_by_request.price[priceIndex] if product_by_request.price_is_list() else product_by_request.price
    
    if not coupon is None and coupon.verify_resource(product_by_request.coupon_resource(coupon.level)):
        price = coupon.reduce_price(price)
    return parser_price(prices["price"] if not is_afiliated else prices["afiliated_price"])

def product_final_reward(product, price_index, convert_str = None):
    parser_price=convert_str or float
    reference_reward = 0
    if product.price_is_list():
        reference_reward = product.price[price_index]["reference_reward"]
    else:
        reference_reward = product.price["reference_reward"]
    return parser_price(reference_reward)

def final_price_list(product_by_request, is_afiliated=False, show_afiliated_price=True, convert_str=None, change_price=None, coupon:Coupon=None):
    parser_price=convert_str or float
    parser_number_price=change_price or float
    price_is_list = product_by_request.price_is_list()
    if not show_afiliated_price:
        is_afiliated = False
    
    verify_resource= not coupon is None and coupon.verify_resource(product_by_request.coupon_resource(coupon.level))
    if price_is_list:
        retPrice = []
        for plan in product_by_request.price:
            normal_price = plan["price"] or 1000
            afiliated_price = plan["afiliated_price"] or normal_price
            price = normal_price if not is_afiliated else afiliated_price
            old_price=False
            if verify_resource:
                old_price = parser_price(price)
                number_price = float(coupon.reduce_price(price))
                price = parser_price(coupon.reduce_price(price))
            else:
                number_price = float(price)
                price = parser_price(price)

            final_price_ = {
                "price":price,
                "old_price":old_price,
                "number_price": number_price,
                "duration":plan.get("duration"),
                "description":plan.get("description")
            }
            retPrice.append(final_price_)
    else:
        plan = product_by_request.price
        verify_resource= not coupon is None and coupon.verify_resource(product_by_request.coupon_resource(coupon.level))
        price = plan["price"] if not is_afiliated else plan["afiliated_price"]
        old_price=False
        number_price=0
        if verify_resource:
            old_price = parser_price(price)
            number_price = float(coupon.reduce_price(price))
            price = parser_price(coupon.reduce_price(price))
        else:
            number_price = float(price)
            price = parser_price(price)

        retPrice = {
            "price":price,
            "old_price":old_price,
            "number_price": number_price,
            "description":plan.get("description")
        }

    return retPrice

def platform_final_price(platform, account_type, is_afiliated=False, show_afiliated_price=True, convert_str=None, coupon:Coupon=None):
    parser_price=convert_str or float
    if not show_afiliated_price:
        is_afiliated = False
    price = 0
    if account_type == "month":
        price = platform.price if not is_afiliated else platform.afiliated_price
    elif account_type == "year":
        price = platform.year_price if not is_afiliated else platform.year_afiliated_price
    if not coupon is None and coupon.verify_resource(platform.coupon_resource(coupon.level)):
        price = coupon.reduce_price(price)
    return parser_price(price)

def streaming_account_final_price(account, today, is_afiliated=False, show_afiliated_price=True, apply_time_discount=True, convert_str=None, coupon:Coupon=None):
    parser_price=convert_str or float
    TIME_DISCOUNT = {0: 1, 1: .95, 2: .9, 3: .7}
    DEFAULT = .5
    if not show_afiliated_price:
        is_afiliated = False
    price = account.price if not is_afiliated else account.afiliated_price
    diff_day = (today - account.start_date).days
    discount = TIME_DISCOUNT.get(diff_day, DEFAULT)
    if not coupon is None and coupon.verify_resource(account.coupon_resource(coupon.level)):
        price = coupon.reduce_price(price)
    return parser_price( price * discount if apply_time_discount else price)

def streaming_account_final_reward(account, today, time_discount=True, apply_time_discount=True, convert_str=None, coupon:Coupon=None):
    parser_price=convert_str or float
    TIME_DISCOUNT = {0: 1, 1: .95, 2: .9, 3: .7}
    DEFAULT = .5
    reward = account.reference_reward
    diff_day = (today - account.start_date).days
    discount = TIME_DISCOUNT.get(diff_day, DEFAULT)
    return parser_price(reward * discount if apply_time_discount else reward)


def platform_format_json(platform: Platform, price:float, number_price:float, year_price:float, year_number_price:float, in_buy=0):
    return {
        "id": platform.id,
        "title": platform.name,
        "img_path": platform.img_path(),
        "file_name": platform.file_name,
        "price": price,
        "number_price": number_price,
        "year_price": year_price,
        "year_number_price": year_number_price,
        "in_buy": in_buy,
        "url": platform.url,
        "type":"platform"
    }


def product_format_json(product: ProductsByRequest, price:float):
    return {
        "id": product.id,
        "title": product.title,
        "img_path": product.img_path(),
        "description":product.description,
        "file_name": product.file_path,
        "price": price,
        "in_buy": 0,
        "slug": product.title_slug,
        "type":"product"
    }

def product_config_json(product, is_afiliated:bool, convert_str=None, change_price=None, coupon=None):
    return {
        **product.config,
        "price_is_list":product.price_is_list(),
        "is_time":product.is_time(),
        "price":final_price_list(product_by_request=product, is_afiliated=is_afiliated, convert_str=convert_str, change_price=change_price, coupon=coupon),
    }

# Devuelve cuentas que solo tengan dias diferentes
def get_account_diff_day(platform_id: int, today, only_available=True, hidden_expired=True, order_by_days_left=True):
    complete_account_ids=db.session.query(CompleteAccountRequest.account_id).group_by(CompleteAccountRequest.account_id).all()
    screens_ids=db.session.query(Screen.account_id).join(Screen.account).filter(StreamingAccount.platform_id == platform_id).where(db.text("isnull(screen.client_id)")).group_by(Screen.account_id).all()

    query = StreamingAccount.query.filter(StreamingAccount.platform_id == platform_id).filter(StreamingAccount.active == True)
    if only_available:
        query=query.filter(StreamingAccount.id.in_([row[0] for row in screens_ids]))
    if hidden_expired:
        query=query.filter(db.text(f"DATEDIFF(DATE_ADD(streaming_account.start_date, interval streaming_account.days DAY), '{today}')>0"))
    query=query.filter(StreamingAccount.id.not_in(complete_account_ids))
    if order_by_days_left:
        query=query.order_by(db.text(f"DATEDIFF(DATE_ADD(streaming_account.start_date, interval streaming_account.days DAY), '{today}') asc"))

    dif_day = dict()
    for a in query.all():
        key = f'{a.start_date}-{a.end_date}'
        if key not in dif_day.keys():
            dif_day[key] = a
    return list(dif_day.values())

def get_available_screen_of_account(account:StreamingAccount):
    for screen in account.screens:
        if screen.client == None:
            return screen
    return None




#-------------------------------------------------- BUY SERVICES --------------------------------------------------#
# def buy_screen(account, today, user, wallet = None, coupon:"Coupon"=None):
def buy_screen(account, today, user:User, is_afiliated:bool=False, coupon:Coupon=None):
    if not account.platform.public:
        return ErrorResponse(401, "Ventas cerrada")
    screen = get_available_screen_of_account(account)
    if screen:
        not_change_final_price = streaming_account_final_price(account=account, today=today, is_afiliated=is_afiliated, coupon=coupon)
        final_price = change_price(not_change_final_price, user.main_money, rounded=False)

        wallet = user.wallet
        wallet.add_amount(-final_price, user.main_money)
        wallet_amount = wallet.main(user)
        if wallet_amount < 0 :
            return False

        # POR IMPLEMENTAR
        Lottery.reward_user(user=user, buy_amount=not_change_final_price)

        screen.client = user
        screen.start_date = account.start_date
        screen.end_date = account.end_date

        history = BuyHistory(user_id=user.id,
                            product="platform",
                            price=final_price,
                            references_reward=0,
                            buy_description=f"Compra de pantalla {account.platform.name}",
                            money_type=user.main_money,
                            # coupon_code=coupon.code if coupon else None,
                            fecha=today)

        db.session.add_all([account, screen, wallet, history])
        db.session.commit()
        
        final_reward = streaming_account_final_reward(account, today=today, coupon=coupon)
        final_reward = change_price(final_reward, user.main_money, rounded=False)

        user.reward_parent(final_reward, history = history)
        return screen
    else: return False

def request_complete_account(platform, today, user:User, is_afiliated:bool=False, coupon:Coupon=None, account_type = "month"):
        if not platform.public:
            return ErrorResponse(401, "Ventas cerrada")
        wallet = user.wallet
        final_price = platform_final_price(platform=platform, account_type=account_type, is_afiliated=is_afiliated, coupon=coupon)
        final_price = change_price(final_price, user.main_money, rounded=False)

        if wallet.main(user) < final_price:
            return ErrorResponse(401, "Usted no tiene suficiente dinero para realizar esta transacción")
        wallet.add_amount(-final_price, user.main_money)
        req = CompleteAccountRequest(user_id = user.id, account_id=None, platform_id=platform.id, status=0, account_type = account_type)
        db.session.add_all([wallet, req])
        db.session.commit()
        
        coupon_code=coupon.code if coupon and coupon.verify_resource(platform.coupon_resource(coupon.level)) else None
        req_user_money = RequestUserMoney(user_id=user.id, request_id=req.id, request_type="complete_account", amount=final_price, money_type=user.main_money, coupon_code=coupon_code)
        db.session.add(req_user_money)
        db.session.commit()
        return SuccessResponse({ "msg": "Su solicitud fué enviada, espere la respuesta" })

def request_products_by_request(product_by_request, form, user, is_afiliated=False, coupon=None):
    try:
        wallet = user.wallet
        data = dict()
        if product_by_request.price_is_list(): plan = int( form.get("price") )
        else: plan = 0

        final_price = product_final_price(product_by_request, plan, is_afiliated=is_afiliated, coupon=coupon)
        final_price = change_price(final_price, user.main_money, rounded=False)
        
        if wallet.main(user) >= final_price:
            wallet.add_amount(-final_price, user.main_money)
            save = [user, wallet]

            data["campos"] = dict()
            for campo in product_by_request.campos:
                type = campo["type"]
                if type in ["text","email"]:
                    data["campos"][campo["name"]] = form[campo["name"]]
                elif type in ["number"]:
                    data["campos"][campo["name"]] = int(form[campo["name"]])
            data["plan"] = plan
            
            req = UserProducts(user_id=user.id, product_id = product_by_request.id, data=data, status=0)
            save.append(req)
            db.session.add_all(save)
            db.session.commit()

            coupon_code=coupon.code if coupon and coupon.verify_resource(product_by_request.coupon_resource(coupon.level)) else None
            req_user_money = RequestUserMoney(user_id=user.id, request_id=req.id, request_type="product", amount=final_price, money_type=user.main_money, coupon_code=coupon_code)
            db.session.add(req_user_money)
            db.session.commit()
            return True
    except Exception as e:
        return False
