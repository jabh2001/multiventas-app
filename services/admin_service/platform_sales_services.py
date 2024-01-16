from libs.models import StreamingAccount, Screen, User, CompleteAccountRequest, Platform, Wallet, RequestUserMoney, BuyHistory, ExpiredAccount, Lottery, db
from libs.schemas import CompleteAccountRequestSchema, PlatformSchema, UserSchema, StreamingAccountSchema
from services.general_service import notifify_users_of_accounts, notify_user
from services.clientService.products_service import platform_final_price
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os, datetime
from datetime import timedelta


def create_streaming_account(data, user:User):
    start_date = datetime.date.fromisoformat(data["start_date"])
    # end_date = datetime.date.fromisoformat(data["end_date"])
    days = int(data["days"])
    screen_amount, *_ = db.session.query(Platform.screen_amount).filter(Platform.id == data["platform_id"]).first()

    account = StreamingAccount(
        user_id = user.id,
        platform_id = data["platform_id"],
        email = data["email"],
        password = data["password"],
        start_date = start_date,
        # end_date = end_date,
        price = float(data["price"]),
        afiliated_price = float(data["afiliated_price"]),
        reference_reward = float(data["reference_reward"]),
        pin = data["pin"],
        supplier_id = data["supplier_id"],
        days = days,
        active = data["active"],
    )
    account.screens = [
        Screen( profile=profile+1, start_date=start_date, end_date=start_date + timedelta(days = days)) 
        for profile in range(screen_amount)
    ]
    db.session.add(account)
    db.session.commit()
    return account

def reject_complete_account(req:CompleteAccountRequest, description:str, user:User, wallet:Wallet, platform:Platform, req_user_money:RequestUserMoney, today):
    req.status = 2
    if req_user_money:
        wallet.add_amount(req_user_money.amount, req_user_money.money_type)
        db.session.delete(req_user_money)
    else:
        raise Exception("Esta peticion es vieja, manejela de otra forma")
    db.session.commit()

    if description:
        mensaje = f"Su peticion de una cuenta completa de {platform.name} fué rechazada, Motivo: {description}. Se le ha repuesto su dinero."
        notify_user(user=user, today=today, content=mensaje)
    return "La solicitud fué rechazada con exito"

def set_complete_account(data, req:CompleteAccountRequest, user:User, platform:Platform, req_user_money:RequestUserMoney, today):
    start_date = datetime.date.fromisoformat(data["start_date"])
    days = int(data["days"])
    end_date = start_date + timedelta(days = days)

    coupon_code = req_user_money.coupon_code if req_user_money else None

    p_final_price = platform_final_price(platform, req.account_type, coupon=req_user_money.coupon)

    complete_account = StreamingAccount(
        supplier_id = data["supplier_id"],
        start_date = start_date,
        # end_date = end_date,
        days=days,
        email = data["email"],
        password = data["password"],
        reference_reward = float(data["reference_reward"]),
        user_id = user.id,
        platform_id = req.platform_id,
        price =p_final_price,
        afiliated_price = p_final_price,
        pin = 0,
        active = True
    )
    buy_description =  f"Compra de cuenta completa de {platform.name}"
    history = BuyHistory(user_id=req.user_id, product="complete_account", price=p_final_price, references_reward=0, buy_description=buy_description, coupon_code=coupon_code, fecha=today)

    req.status=1
    req.account=complete_account

    if req_user_money:
        req_user_money.coupon_code = None

    Lottery.reward_user( user=user, buy_amount=p_final_price )
    
    user.reward_parent(p_final_price, history=history)


    # db.session.add_all([complete_account, history])
    db.session.commit()
    notify_user(user=user, today=today, content=f"Su cuenta completa de {platform.name} fue asignada, ve a 'Mis productos'")
    return "Se asignó la cuenta con exito"


def renewal_streaming_account(account:StreamingAccount, account_schema:StreamingAccountSchema, data, today):
    start_date = datetime.date.fromisoformat(data["start_date"])
    days = int(data["days"])
    end_date = start_date + timedelta(days = days)

    data = {
        **data,
        # "start_date":start_date,
        "days":days,
        "pin":1 if data["pin"] else 0
    }
    if "supplier_id" in data:
        del data["supplier_id"]
    newValue=data.get("email", False)
    if newValue and newValue != account.email: 
        mensaje=f'Por ciertos motivos debimos cambiar la cuenta {account.email}, revisa en la seccion de "tus pantallas" la nueva cuenta es {newValue}. Lamentamos las molestias.'.strip()
        account.email =     newValue
        notifify_users_of_accounts(account, mensaje, today)

    newValue=data.get("password", False)
    if newValue and newValue != account.password:
        mensaje=f'Por ciertos motivos debimos cambiar contraseña de la cuenta {account.email}, revisa en la seccion de "tus pantallas" la nueva contraseña es {newValue}.'
        notifify_users_of_accounts(account, mensaje, today)

    account_schema.load(data, instance=account, partial=True)
    db.session.commit()

    account.expired_accounts = []
    for screen in account.screens:
        if not screen.client_id:
            screen.start_date = start_date
            screen.end_date = end_date
    db.session.commit()


def get_complete_request():
    req_schema, platform_schema, user_schema = CompleteAccountRequestSchema(), PlatformSchema(only=("id", "name")), UserSchema(only=("id", "username"))
    return [
        {
            "complete_account_request":req_schema.dump(complete_account_request),
            "platform":platform_schema.dump(platform),
            "user":user_schema.dump(user),
        } for complete_account_request, platform, user in (
            db.session.query( CompleteAccountRequest, Platform, User)
            .join(CompleteAccountRequest.platform)
            .join(CompleteAccountRequest.user)
            .filter(CompleteAccountRequest.status == 0)
        )
    ]

def get_complete_account(page, per_page, sort_field, today):
    # days_left = db.func.datediff(StreamingAccount.end_date, today).label("days_left")
    days_left = db.func.datediff(StreamingAccount.c_end_date(), today).label("days_left")
    req_schema, platform_schema, streaming_account_schema, user_schema = CompleteAccountRequestSchema(), PlatformSchema(only=("id", "name")), StreamingAccountSchema(), UserSchema(only=("id", "username"))
    query = (
        db.session.query( CompleteAccountRequest, Platform, StreamingAccount, days_left, User)
        .join(CompleteAccountRequest.platform)
        .join(CompleteAccountRequest.user)
        .join(CompleteAccountRequest.account)
        .filter(CompleteAccountRequest.status == 1)
    )
    if(sort_field == "platform.name"): query = query.order_by(Platform.name)
    if(sort_field == "account.end_date"): query = query.order_by(StreamingAccount.c_end_date())
    if(sort_field == "account.days_left"): query = query.order_by(days_left)
    if(sort_field == "account.price"): query = query.order_by(StreamingAccount.price)

    paging = query.paginate(page=page, per_page=per_page, max_per_page=500, error_out=False)
    return {
        "data":[
            {
                "complete_account_request":req_schema.dump(complete_account_request),
                "platform":platform_schema.dump(platform),
                "account":{**streaming_account_schema.dump(account), "days_left":days_left},
                "user":user_schema.dump(user),
            } for complete_account_request, platform, account, days_left, user in paging
        ],
        "last_page":paging.pages
    }


"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    platform_id = db.Column(db.Integer, db.ForeignKey(Platform.id))
    supplier_id = db.Column(db.Integer, db.ForeignKey(Supplier.id))
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())
    email = db.Column(db.String(255))
    password = db.Column(db.String(255))
    price = db.Column(db.Float, nullable=False, default=0)
    afiliated_price = db.Column(db.Float, nullable=False, default=0)
    reference_reward = db.Column(db.Float, nullable=False, default=0)
    pin = db.Column(db.Integer)
"""