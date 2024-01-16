from libs.models import ProductsByRequest, UserProducts, User, BuyHistory, RequestUserMoney, db
from libs.schemas import ProductsByRequestSchema, UserProductsSchema
from services.general_service import notify_user
from services.general_service import save_file
from services.clientService.products_service import product_final_reward, product_final_price
from services.money_change_service import change_price
from werkzeug.datastructures import FileStorage
from datetime import timedelta
import os
import json

def create_product_by_request(form, file):
    title = form.get("title")
    slug = form.get("title_slug")
    description = form.get("description")
    public = 1 if form.get("public") else 0
    config = json.loads(form.get("config"))
    file_path = save_file(file, slug.lower().replace("-", "_"))

    return ProductsByRequest(
        title=title,
        title_slug=slug,
        file_path=file_path,
        description=description,
        config=config,
        public=public
    )
def update_product_by_request(product:ProductsByRequest, form, file:FileStorage):
    title = form.get("title")
    slug = form.get("title_slug")
    description = form.get("description")
    public = 1 if form.get("public") and form.get("public").lower() == "true" else 0
    config = json.loads(form.get("config"))
    new_data = {
        "title":title,
        "title_slug":slug,
        "description":description,
        "public":public,
        "config":config,
    }
    if file:
        file_path = save_file(file, slug.lower().replace("-", "_"))
        new_data["file_path"] = file_path

    datos_actualizados = ProductsByRequestSchema().load(new_data, instance=product, partial=True)

def product_deltatime_duration(product:ProductsByRequest, price_index, today):
    if not product.price_is_list():
        return False
    d = product.price[price_index].get("duration", False)
    if not d:
        return False

    days, months, years = d["days"], d["months"], d["years"]
    days = timedelta(days=int(days))
    if months:  months = timedelta(days=months*30)
    else:       months = timedelta()
    years = today.replace(year=today.year+years) - today
    
    return days + months + years

def active_user_product(user_product:UserProducts, today, info = None):
    product = user_product.product
    if not product:
        raise Exception("Ese producto no existe")

    user_product.status = 1
    user_product.start_date = today
    time = product_deltatime_duration(product, user_product.data.get("plan", -1), today)
    user_product.end_date = today + time if time else None

    if info:
        copy = user_product.data.copy()
        copy["info"] = info
        user_product.data = copy

    db.session.commit()

    user = user_product.user
    notify_user(user, today, f"Se ha aceptado su producto '{product.title}'")

    req_user_money = RequestUserMoney.query.filter(RequestUserMoney.request_id==user_product.id).filter(RequestUserMoney.request_type=="product").first()
    Lottery.reward_user(
        user=user,
        buy_amount=product_final_price(
            product,
            user_product.data.get("plan"),
            user.is_afiliated(),
            coupon=req_user_money.coupon
        )
    )

    reference_reward = product_final_reward(product, user_product.data.get("plan"))
    reference_reward = change_price(reference_reward, user.main_money, rounded=False)
    
    user_product_send_buy_history(user_product, product, user, today, reference_reward)

def reject_user_product(user_product:UserProducts, today, description=None):
    if user_product.status != 0:
        raise Exception("No puede rechazar el peticion por que ya fue procesada")
    user_product.status=2

    product = user_product.product
    user = user_product.user
    wallet = user.wallet
    req_user_money = RequestUserMoney.query.filter(RequestUserMoney.request_id==user_product.id).filter(RequestUserMoney.request_type=="product").first()
    if req_user_money:
        wallet.add_amount(req_user_money.amount, req_user_money.money_type)
        db.session.delete(req_user_money)
    else:
        # Con el favor de dios y si todo va bien esto no se va a usar, eliminar despues de un tiempo
        price = product_final_price(product, user_product.data.get("plan"), user.is_afiliated())
        price = change_price(price, user.main_money, rounded=False)
        wallet.add_amount(price, user.main_money)

    db.session.commit()

    if description:
        mensaje = f"Su peticion de {product.title} fué rechazada, Motivo: {description}. Se le ha repuesto su dinero."
        notify_user(user, today, mensaje)
    return True

def user_product_send_buy_history(user_product:UserProducts, product:ProductsByRequest, user:User, today, reference_reward=0):
    req_user_money = RequestUserMoney.query.filter(RequestUserMoney.request_id==user_product.id).filter(RequestUserMoney.request_type=="product").first()
    coupon_code=None
    if req_user_money: coupon_code = req_user_money.coupon_code

    price = product_final_price(product, user_product.data.get("plan"), user.is_afiliated(), coupon=req_user_money.coupon)
    price = change_price(price, user.main_money, rounded=False)

    history = BuyHistory(  user = user_product.user,
                            product = "product",
                            price = price,
                            references_reward = 0,
                            buy_description = f"Compra de {product.title}",
                            coupon_code=coupon_code,
                            fecha = today)
    if req_user_money:
        req_user_money.coupon_code = None
        db.session.add(req_user_money)                       
    db.session.add(history)
    db.session.commit()

    user.reward_parent(reference_reward, history)