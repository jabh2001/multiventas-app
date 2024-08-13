from libs.models import User, Notifications, db
from libs.schemas import UserSchema, WalletSchema, PrizeWalletSchema

def dict_of_user_data(user:User):
    notifications, *_ = db.session.query(db.func.count(Notifications.id))\
        .filter(Notifications.user_id == user.id)\
        .filter(Notifications.showed == 0)\
        .first()
    user_schema = UserSchema(exclude=("password", "parent_id"))
    wallet_schema = WalletSchema(exclude=["id"])
    prize_wallet_schema = PrizeWalletSchema(exclude=["id"])

    response = dict()
    response["user"] = user_schema.dump(user)
    response["wallet"] = wallet_schema.dump(user.wallet)
    response["prize_wallet"] = prize_wallet_schema.dump(user.prize_wallet)
    response["notifications"] = notifications


    return response