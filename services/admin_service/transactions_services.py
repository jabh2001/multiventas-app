from libs.models import RechargeRequest, RechargeAlerts, User, Wallet, PaymentMethod, PagoMovilRequest, db
from libs.schemas import RechargeRequestSchema, UserSchema, PaymentMethodSchema, PagoMovilRequestSchema, db

def get_transfers():
    # subquery = db.session.query(db.func.count(RechargeAlerts.id)).select_from(RechargeAlerts).filter(RechargeAlerts.last == RechargeRequest.id).subquery()
    subquery = db.text("(select count(*) from recharge_alerts where recharge_alerts.last = recharge_request.id)")
    return db.session.query(RechargeRequest, PaymentMethod, User, subquery)\
        .filter(RechargeRequest.status=="no verificado")\
        .join(RechargeRequest.user)\
        .join(RechargeRequest.payment_method)

def get_verified_transfers(page:int=1, per_page:int=50):
    query = db.session.query(RechargeRequest, PaymentMethod, User)\
        .filter(RechargeRequest.status.in_(["verificado", "rechazado"]))\
        .order_by(RechargeRequest.id.desc())\
        .join(RechargeRequest.user)\
        .join(RechargeRequest.payment_method)
    return query.paginate(page=page, per_page=per_page, max_per_page=500, error_out=False)

def get_duplicate_transfers(recharge_id):
    return db.session.query(RechargeRequest, PaymentMethod, User)\
        .filter(RechargeAlerts.last == recharge_id)\
        .join(RechargeRequest.user)\
        .join(RechargeAlerts, RechargeRequest.id == RechargeAlerts.first)\
        .join(RechargeRequest.payment_method)
        
def format_recharges_entries(entries, verified=True):
    recharge_schema = RechargeRequestSchema()
    payment_method_schema = PaymentMethodSchema(only=("payment_platform_name", "money_type",))
    user_schema = UserSchema(only=("id", "username"))
    
    return [ {
            "recharge_request":recharge_schema.dump(recharge),
            "payment_method":payment_method_schema.dump(payment_method),
            "user":user_schema.dump(user)
        } for recharge, payment_method, user in entries
    ] if verified else [ {
            "recharge_request":recharge_schema.dump(recharge),
            "payment_method":payment_method_schema.dump(payment_method),
            "user":user_schema.dump(user),
            "duplicate":duplicate
        } for recharge, payment_method, user, duplicate in entries
    ]
def format_duplicate_entries(entries):
    recharge_schema = RechargeRequestSchema()
    payment_method_schema = PaymentMethodSchema(only=("payment_platform_name", "money_type",))
    user_schema = UserSchema(only=("id", "username"))
    
    return [ {
            "recharge_request":recharge_schema.dump(recharge),
            "payment_method":payment_method_schema.dump(payment_method),
            "user":user_schema.dump(user)
        } for recharge, payment_method, user in entries
    ]

def approve_recharge(recharge:RechargeRequest, payment_method:PaymentMethod, wallet:Wallet, *arg):
    try:
        recharge.status = RechargeRequest.VERIFIED
        wallet.add_amount(amount = recharge.amount, money_type = payment_method.money_type)

        db.session.add_all([wallet, recharge])
        db.session.commit()
        return {
            "status":True,
            "msg":'Tu solicitud por ' + payment_method.money_type + '. ' + str(recharge.amount) + ' fue aceptada'
        }
    except Exception as e:
        return {
            "status":False,
            "msg":str(e)
        }

def reject_recharge(recharge:RechargeRequest, payment_method:PaymentMethod):
    try:
        recharge.status = RechargeRequest.REJECT

        db.session.add(recharge)
        db.session.commit()
        return {
            "status":True,
            "msg":'Tu solicitud por ' + payment_method.money_type + '. ' + str(recharge.amount) + ' fue rechazada'
        }
    except Exception as e:
        return {
            "status":False,
            "msg":str(e)
        }

def get_pago_movil():
    return db.session.query(PagoMovilRequest, User)\
        .filter(PagoMovilRequest.status == 0)\
        .join(PagoMovilRequest.user)\

def get_verified_pago_movil(page:int=1, per_page:int=50):
    query = db.session.query(PagoMovilRequest, User)\
        .filter(PagoMovilRequest.status != 0)\
        .order_by(PagoMovilRequest.id.desc())\
        .join(PagoMovilRequest.user)
    return query.paginate(page=page, per_page=per_page, max_per_page=500, error_out=False)
    
        
def format_pago_movil_entries(entries, verified=True):
    pago_movil_schema = PagoMovilRequestSchema()
    user_schema = UserSchema(only=("id", "username"))
    
    return [ {
            "pago_movil_request":pago_movil_schema.dump(pago_movil),
            "user":user_schema.dump(user)
        } for pago_movil, user in entries
    ]


def approve_pago_movil(pagomovil:PagoMovilRequest, today, referencia:str):
    try:
        pagomovil.status = 1
        pagomovil.referencia = referencia
        recarga = RechargeRequest(user_id=pagomovil.user_id, date=today, status="retiro_de_utilidades", payment_method_id=-123, amount=pagomovil.amount, reference=pagomovil.money_type)
        
        db.session.add_all([pagomovil, recarga])
        db.session.commit()
        return {
            "status":True,
            "msg":f"Su operacion de pago movil fué aceptada, referencia: {pagomovil.referencia}"
        }
    except Exception as e:
        return {
            "status":False,
            "msg":str(e)
        }

def reject_pago_movil(pagomovil:PagoMovilRequest, wallet:Wallet):
    try:
        pagomovil.status = 2
        wallet.add_balance(pagomovil.amount, pagomovil.money_type)

        db.session.add_all([wallet, pagomovil])
        db.session.commit()
        return {
            "status":True,
            "msg":"Su solicitud de pago movil fué rechazada"
        }
    except Exception as e:
        return {
            "status":False,
            "msg":str(e)
        }