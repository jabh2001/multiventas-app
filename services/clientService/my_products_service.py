from libs.models import User, Wallet, UserProducts, ProductsByRequest, CompleteAccountRequest, Screen, StreamingAccount, Platform, BuyHistory, db
from libs.exceptions import *
from services.clientService.products_service import streaming_account_final_price
from services.clientService.products_service import streaming_account_final_reward
from services.clientService.products_service import platform_final_price
from services.money_change_service import change_price
import datetime


def format_user_products_data(req: UserProducts, product: ProductsByRequest):
    return {
        "id": req.id,
        "title": product.title,
        "start_date": req.start_date.strftime("%d-%m-%Y") if req.start_date else " - ",
        "end_date": req.end_date.strftime("%d-%m-%Y") if req.end_date else req.start_date.strftime("%d-%m-%Y") if req.start_date else " - ",
        "data": req.data["campos"],
        "status": req.status,
        "info": req.data.get("info", "-")
    }


def format_complete_account_data(
        today: datetime.date, req: CompleteAccountRequest, account: StreamingAccount, platform: Platform):
    ret = {
        "id": req.id,
        "title": platform.name,
        "platform_url": platform.url,
        "start_date": account.start_date.strftime("%d-%m-%Y"),
        "end_date": account.end_date.strftime("%d-%m-%Y"),
        "days_left": (account.end_date - today).days,
        "email": account.email,
        "password": account.password
    }
    return ret


def format_screen_data(today: datetime.date, screen: Screen,
                       account: StreamingAccount, platform: Platform):
    return {
        "id": screen.id,
        "title": platform.name,
        "platform_url": platform.url,
        "start_date": screen.start_date.strftime("%d-%m-%Y"),
        "end_date": screen.end_date.strftime("%d-%m-%Y"),
        "days_left": (screen.end_date - today).days,
        "email": account.email,
        "password": account.password,
        "profile": screen.profile,
        "pin": screen.pin(account) if account.pin else "Sin pin"
    }


def get_query_with_dependencies(user_id: int, today: datetime.date):
    models = {
        "Screen": db.session.query(Screen, StreamingAccount, Platform)
            .join(Screen.account)
            .join(StreamingAccount.platform)
            .filter(Screen.client_id == user_id)
            .order_by(db.func.datediff(StreamingAccount.c_end_date(), today)),
            # .order_by(db.text(f"DATEDIFF(streaming_account.end_date, \"{today}\")")),
        "CompleteAccountRequest": db.session.query(CompleteAccountRequest, StreamingAccount, Platform)
        .join(CompleteAccountRequest.account)
        .join(StreamingAccount.platform)
        .filter(CompleteAccountRequest.user_id == user_id)
        .order_by(db.func.datediff(StreamingAccount.c_end_date(), today)),
        # .order_by(db.text(f"DATEDIFF(streaming_account.end_date, \"{today}\")")),
        "UserProducts": db.session.query(UserProducts, ProductsByRequest).join(UserProducts.product)
        .filter(UserProducts.status == 1)
        .filter(UserProducts.user_id == user_id)
    }
    return models


def found_product_by_id(id, model: str):
    models = {
        "Screen": Screen.query.filter(Screen.id == id),
        "CompleteAccountRequest": CompleteAccountRequest.query.filter(CompleteAccountRequest.id == id),
        "UserProducts": UserProducts.query.filter(UserProducts.id == id)
    }
    if model not in models.keys():
        raise CustomMessageError(
            "El model especificado no esta soportado para esta operacion")
    result = models[model].first()
    if not result:
        raise ProductNotFoundError()
    return result

def renew_screen(screen:Screen, today, user:User, wallet:Wallet, account:StreamingAccount, platform:Platform):
    final_price = streaming_account_final_price(account, today, user.is_afiliated(), apply_time_discount=False)
    final_price = change_price(final_price, user.main_money, rounded=False)
    wallet.add_amount(-final_price, user.main_money)

    if wallet.main(user) < 0 :
        return ErrorResponse("No tiene dinero suficiente")
    screen.end_date = screen.end_date + datetime.timedelta(days=account.days)
    history = BuyHistory(user_id=user.id,
                            product="platform",
                            price=final_price,
                            references_reward=0,
                            buy_description=f"Renovacion de pantalla {platform.name}",
                            money_type=user.main_money,
                            fecha=today)

    db.session.add_all([screen, wallet, history])
    db.session.commit()
        
    final_reward = streaming_account_final_reward(account, today=today)
    final_reward = change_price(final_reward, user.main_money, rounded=False)
    user.reward_parent(final_reward, history = history)

    return SuccessResponse({ "msg":"Usted ha renovado correctamente su cuenta" })

def renew_complete_account(complete:CompleteAccountRequest, today, user:User, wallet:Wallet, account:StreamingAccount, platform:Platform):
        final_price = platform_final_price(platform=platform, is_afiliated=user.is_afiliated())
        final_price = change_price(final_price, user.main_money, rounded=False)
        wallet.add_amount(-final_price, user.main_money)

        if wallet.main(user) < 0 :
            return ErrorResponse("No tiene dinero suficiente")
        account.end_date = account.end_date + account.duration_days()
        history = BuyHistory(user_id=user.id, 
                            product="platform",
                            price = final_price,
                            references_reward = 0,
                            buy_description = f"Renovacion de cuenta completa de {platform.name}",
                            money_type=user.main_money,
                            fecha=today)

        db.session.add_all([account, wallet, history])
        db.session.commit()
        
        final_reward = streaming_account_final_reward(account, today=today)
        final_reward = change_price(final_reward, user.main_money, rounded=False)
        user.reward_parent(final_reward, history=history)
        
        return SuccessResponse({ "msg":"Usted ha renovado correctamente su cuenta" })