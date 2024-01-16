from libs.models import Afiliated, PlatinumMembers, BuyHistory, Wallet, User, AfiliationGiftCode, db
from datetime import timedelta, date
from services.random_password import generate_password
from services.general_service import create_affiliation_gift_code

def afiliar(user:User, wallet:Wallet, price:float, reference_reward:float, hoy:date=None):
        wallet.add_amount(-price, user.main_money)
        un_mes = hoy + timedelta( days=30 )

        afiliacion = Afiliated.query.filter_by(user_id = user.id).first()
        msg=""

        if afiliacion:
            afiliacion.status = 1
            afiliacion.start_date = hoy
            afiliacion.end_date = un_mes
            msg = "Su membresía ha sido renovada"
        else:
            afiliacion = Afiliated(user_id=user.id, status=1, start_date=hoy, end_date=un_mes)
            msg = "Ha comprado la membresía de revendedor"

        history = BuyHistory(user_id=user.id,
                            product="afiliation vip",
                            price=price,
                            references_reward=0,
                            buy_description=f"{user.username} Se ha suscrito al plan vip",
                            money_type=user.main_money,
                            fecha=hoy)
                        
        db.session.add_all([ afiliacion, history ])
        db.session.commit()
        
        user.reward_parent(reward=reference_reward, history=history)

        return msg, un_mes

def afiliar_with_code(user:User, gift_code:AfiliationGiftCode, hoy:date=None):
    if gift_code.owner_id == user.id:
        raise Exception("El dueño de un código no puede usarlo")
    if gift_code.receiver_id != None:
        raise Exception("Este código ya ha sido usado")
    if gift_code.type != "vip":
        raise Exception("Este código es para otro tipo de afiliacion")
    if user.is_vip():
        raise Exception("No puedes hacer esto, ya usted esta suscrito")
    gift_code.receiver_id = user.id
    
    un_mes = hoy + timedelta( days=30 )

    afiliacion = Afiliated.query.filter_by(user_id = user.id).first()
    msg=""

    if afiliacion:
        afiliacion.status = 1
        afiliacion.start_date = hoy
        afiliacion.end_date = un_mes
        msg = "Su membresía ha sido renovada"
    else:
        afiliacion = Afiliated(user_id=user.id, status=1, start_date=hoy, end_date=un_mes)
        msg = "Ha comprado la membresía de revendedor"

    history = BuyHistory(user_id=user.id,
                        product="afiliation vip",
                        price=0,
                        references_reward=0,
                        buy_description=f"{user.username} Se ha suscrito al plan vip usando el código {gift_code.code}",
                        money_type=user.main_money,
                        fecha=hoy)
                    
    db.session.add_all([ afiliacion, history ])
    db.session.commit()

    return msg, un_mes

def afiliar_platinum(user:User, wallet:Wallet, price:float, reference_reward:float, hoy=None):
        wallet.add_amount(-price, user.main_money)

        member = PlatinumMembers.query.filter(PlatinumMembers.user_id == user.id).first()
        msg=""

        if member:
            raise Exception("Ya eres un miembro TITANIUM" if member.status == 1 else "Aun se esta procesando tu solicitud")
        else:
            member = PlatinumMembers(user_id=user.id, status=0, start_date=None)
            msg = "Ha comprado la membresia TITANIUM"

        history = BuyHistory(user_id=user.id,
                            product="afiliation TITANIUM",
                            price=price,
                            references_reward=0,
                            buy_description=f"{user.username} Se ha suscrito al plan TITANIUM",
                            money_type=user.main_money,
                            fecha=hoy)
                        
        db.session.add_all([ member, history ])
        db.session.commit()
        
        user.reward_parent(reward=reference_reward, history=history)

        return msg

def afiliar_platinum_with_code(user:User, gift_code:AfiliationGiftCode, hoy=None):
    if gift_code.owner_id == user.id:
        raise Exception("El dueño de un código no puede usarlo")
    if gift_code.receiver_id != None:
        raise Exception("Este código ya ha sido usado")
    if gift_code.type != "platinum":
        raise Exception("Este código es para otro tipo de afiliacion")
    gift_code.receiver_id = user.id

    member = PlatinumMembers.query.filter(PlatinumMembers.user_id == user.id).first()
    msg=""

    if member:
        raise Exception("Ya eres un miembro TITANIUM" if member.status == 1 else "Aun se esta procesando tu solicitud")
    else:
        member = PlatinumMembers(user_id=user.id, status=0, start_date=None)
        msg = "Ha comprado la membresia TITANIUM"

    history = BuyHistory(user_id=user.id,
                        product="afiliation TITANIUM",
                        price=0,
                        references_reward=0,
                        buy_description=f"{user.username} Se ha suscrito al plan TITANIUM con el código {gift_code.code}",
                        money_type=user.main_money,
                        fecha=hoy)
                    
    db.session.add_all([ member, history ])
    db.session.commit()
    
    return msg

def buy_affiliation_gift_code(user:User, wallet:Wallet, price, type):
    all_gift_codes = AfiliationGiftCode.query.all()
    code = create_affiliation_gift_code(all_gift_codes)
    gift_code = AfiliationGiftCode(owner_id=user.id, code=code, type=type)
    wallet.add_amount(-price, user.main_money)
    
    db.session.add(gift_code)
    db.session.commit()
    return gift_code
