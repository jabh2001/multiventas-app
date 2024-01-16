from libs.money_change import MoneyChange

MONEY_TYPES = [
    "bs",
    "cop",
    "sol",
    "mxn",
    "usd",
]

def change_price(amount, money_type="bs", rounded=True, dec_lenght=2):
    if not amount:
        amount = 0
    instance = MoneyChange.getInstance()
    final_amount = instance.change_from_usd(amount=amount, to_money=money_type)
    return round(final_amount, dec_lenght)
    return round(final_amount, dec_lenght) if rounded else final_amount


def str_price(price=0, money_type="bs", change_price_=True):
    if change_price_: price = change_price(price, money_type=money_type)
    if money_type == "cop":
        return f"{price} COP"
    elif money_type == "sol":
        return f"{price} SOL"
    elif money_type == "mxn":
        return f"{price} MXN"
    elif money_type == "usd":
        return f"{price} USD"
    return f"{price} Bs"
