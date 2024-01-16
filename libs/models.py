from datetime import date, datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from __init__ import create_app
import pytz
import enum

app = create_app()
db = SQLAlchemy()


class dateV:
    tz = app.config["TZ_INFO"]

    @classmethod
    def datetime_now(cls):
        return datetime.now(tz=cls.tz)

    @classmethod
    def date_today(cls) -> date:
        now = cls.datetime_now()
        return date(year=now.year, month=now.month, day=now.day)


def timeDecorator(cls):
    def duration_days(self): return self.end_date - self.start_date

    def timedelta_left(self)->timedelta: return self.end_date.__sub__(dateV.date_today())

    def days_left(self):
        days = self.timedelta_left().days
        return 0 if days < 0 else days

    def days_left_class_color(self):
        daysLeft = self.days_left()
        if daysLeft <= 5:
            badgeColor = 'danger'
        elif daysLeft <= 10:
            badgeColor = 'warning'
        else:
            badgeColor = 'success'
        return badgeColor
    
    def months_left(self):
        days = self.days_left()
        if days<21:     return 0
        else:           return self.end_date.month - dateV.date_today().month

    def time_left_message(self):
        dias = self.days_left()
        meses = self.months_left()
        return f'{dias} {"dias" if dias>1 else "dia"}' if meses < 1 else f'{meses} {"meses" if meses>1 else "mes"}'
    
    setattr(cls, "duration_days", duration_days)
    setattr(cls, "timedelta_left", timedelta_left)
    setattr(cls, "days_left", days_left)
    setattr(cls, "days_left_class_color", days_left_class_color)
    setattr(cls, "months_left", months_left)
    setattr(cls, "time_left_message", time_left_message)

    return cls
class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    user_type = db.Column(db.String(255))
    parent_id = db.Column(db.Integer)
    username = db.Column(db.String(255))
    email = db.Column(db.String(255))
    password = db.Column(db.String(255))
    phone = db.Column(db.String(100))
    ci = db.Column(db.String(255), nullable=True)
    gender = db.Column(db.String(255), nullable=True)
    country = db.Column(db.String(10), default="ve")
    main_money = db.Column(db.String(10), default="bs")

# ALTER TABLE user ADD COLUMN is_valid_email bool not null default false;
    is_valid_email = db.Column(db.Boolean, default=False)

    _parent = None 
    _childs = None

    wallet = db.relationship("Wallet", backref="user", uselist=False)
    afiliated = db.relationship("Afiliated", backref="user", uselist=False)
    lottery = db.relationship("Lottery", backref="user", uselist=False)
    pago_movil_requests = db.relationship("PagoMovilRequest", backref=db.backref("user"))
    suggestions = db.relationship("Suggestion", backref=db.backref("user"))
    support_products = db.relationship( "SupportProducts", backref=db.backref("user"))
    buy_historys = db.relationship("BuyHistory", backref=db.backref("user"))
    notifications = db.relationship( "Notifications", backref=db.backref("user"))
    recharge_requests = db.relationship("RechargeRequest", backref=db.backref("user"))
    screens = db.relationship("Screen", backref=db.backref("client"))
    complete_account_requests = db.relationship( "CompleteAccountRequest", backref=db.backref("user"))
    expired_accounts = db.relationship( "ExpiredAccount", backref=db.backref("user"))
    user_products = db.relationship("UserProducts", backref=db.backref("user"))
    document_request = db.relationship("DocumentRequest", backref=db.backref("user"))
    
    google_data = db.relationship("GoogleData", backref=db.backref("user"), uselist=False)
    platinum_membership = db.relationship("PlatinumMembers", backref=db.backref("user"), uselist=False)

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    def is_afiliated(self):
        try:
            return self.afiliated.status == 1
        except Exception as ae:
            return False

    def is_vip(self):
        return self.is_afiliated()

    def is_platinum(self):
        try:
            return not self.platinum_membership is None
        except Exception as ae:
            return False
    
    @property
    def parent(self):
        if self._parent is None:
            self._parent = User.query.get(self.parent_id)
        return self._parent
    
    @parent.setter
    def parent(self, parent):
        if not isinstance(parent, User):
            raise Exception("Debe ser una instancia de usuario")
        self.parent_id = parent.id
        
    def childs(self):
        childs = User.query.filter(User.parent_id == self.id).all()
        return childs if len(childs) > 0 else False

    def reward_parent(self, reward, history):
        parent = self.parent
        if not parent is None:
            parent_wallet = parent.wallet
            parent_wallet.add_balance(reward, self.main_money)

            if history != None:
                history.references_reward = reward
            db.session.commit()

class Config(db.Model):
    __tablename__ = "config"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    options = db.Column(db.JSON)

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class ExchangeRate(db.Model):
    __tablename__ = "exchange_rate"
    id = db.Column(db.Integer, primary_key=True)
    money_type = db.Column(db.String(10), nullable=False, unique=True)
    amount = db.Column(db.Float, nullable=False, default=0)

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class RechargeAlerts(db.Model):
    __tablename__ = "recharge_alerts"
    id = db.Column(db.Integer, primary_key=True)
    first = db.Column(db.Integer)
    last = db.Column(db.Integer)
    status = db.Column(db.Integer)

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class ProductsByRequest(db.Model):
    __tablename__ = "products_by_request"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    title_slug = db.Column(db.String(256), unique=True, nullable=False)
    description = db.Column(db.String(2000), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    config = db.Column(db.JSON())
    public = db.Column(db.Boolean, default=True)

    user_products = db.relationship(
        "UserProducts", backref=db.backref("product"))

    @property
    def name(self):
        return self.title

    @property
    def url(self):
        return self.config.get("url") or False

    @property
    def price(self):
        return self.config.get("price") or False

    @property
    def campos(self):
        return self.config.get("campos") or False

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    def price_is_list(self):
        return isinstance(self.price, list)

    def is_time(self):
        if self.price_is_list():
            return "duration" in self.price[0].keys()
        return False

    def img_path(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'assets/img/{self.file_path}/')
    

    def coupon_resource(self, level):
        if level == 1: return {"resource":"product_by_request", "resource_id":self.id}
        if level == 2: return {"resource":"all_product", "resource_id":self.id}
        if level == 3: return {"resource":"product", "resource_id":self.id}
        if level == 4: return {"resource":"category", "resource_id":self.four_level()}
        if level == 5: return {"resource":"all", "resource_id":"*"}

    def four_level(self):
        return db.session.query(db.text("group_concat(category_id)"))\
            .select_from(ProductCategories)\
            .filter(ProductCategories.product_id==self.id)\
            .filter(ProductCategories.product_type=="product")\
            .group_by(ProductCategories.product_id)\
            .group_by(ProductCategories.product_type)\
            .first


""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""


class Wallet(db.Model):
    __tablename__ = "wallet"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    amount = db.Column(db.Float, nullable=False, default=0)
    balance = db.Column(db.Float, nullable=False, default=0)
    usd_amount = db.Column(db.Float, nullable=False, default=0)
    usd_balance = db.Column(db.Float, nullable=False, default=0)
    cop_amount = db.Column(db.Float, nullable=False, default=0)
    cop_balance = db.Column(db.Float, nullable=False, default=0)
    mxn_amount = db.Column(db.Float, nullable=False, default=0)
    mxn_balance = db.Column(db.Float, nullable=False, default=0)
    sol_amount = db.Column(db.Float, nullable=False, default=0)
    sol_balance = db.Column(db.Float, nullable=False, default=0)

    # user=db.relationship("User", user)

    def get_all_wallets(self, wallet="amount"):
        return {
            "bs":self.amount,
            "cop":self.cop_amount,
            "usd":self.usd_amount,
            "mxn":self.mxn_amount,
            "sol":self.sol_amount,
        } if wallet == "amount" else {
            "bs":self.balance,
            "cop":self.cop_balance,
            "usd":self.usd_balance,
            "mxn":self.mxn_balance,
            "sol":self.sol_balance,
        } if wallet == "balance" else dict()
    #Este metodo devuelve la billetera principal del usuario
    def main(self, user = None):
        if not user:
            user = User.query.filter(Wallet.user_id == self.user_id)
        wallets = self.get_all_wallets(wallet="amount")
        return wallets.get(user.main_money, "bs")

    def main_balance(self, user = None):
        if user is None:
            user = User.query.filter(Wallet.user == self.user)
        wallets = self.get_all_wallets(wallet="balance")
        return wallets.get(user.main_money, "bs")

    def add_amount(self, amount = 0, money_type = "bs"):
        if money_type == "bs":
            self.amount += amount
        elif money_type == "cop":
            self.cop_amount += amount
        elif money_type == "sol":
            self.sol_amount += amount
        elif money_type == "mxn":
            self.mxn_amount += amount
        elif money_type == "usd":
            self.usd_amount += amount

    def add_balance(self, balance=0, money_type="bs"):
        if money_type == "bs":
            self.balance += balance
        elif money_type == "cop":
            self.cop_balance += balance
        elif money_type == "sol":
            self.sol_balance += balance
        elif money_type == "mxn":
            self.mxn_balance += balance
        elif money_type == "usd":
            self.usd_balance += balance


    def balanceToAmount(self, amount, money_type="bs"):
        if self.get_all_wallets(wallet="balance").get(money_type, "bs") < amount:
            raise Exception("Error al transferir las utilidades")
        self.add_amount(amount=amount, money_type=money_type)
        self.add_balance(balance=-amount, money_type=money_type)
        recarga = RechargeRequest(user_id=self.user_id, date=dateV.datetime_now(), status="utilidades_a_cuenta_corriente", payment_method_id=-123, amount=amount, reference=money_type)
        db.session.add_all([self, recarga])
        db.session.commit()

    def balanceToPagoMovil(self, user_id, phone, banco, amount, money_type="bs"):
        if self.get_all_wallets(wallet="balance").get(money_type, "bs") < amount:
            raise Exception("Error al transferir las utilidades")
        self.add_balance(balance=-amount, money_type=money_type)
        pagomovil = PagoMovilRequest(user_id = user_id, phone=phone, banco=banco, amount=amount, money_type=money_type)
        db.session.add_all([self, pagomovil])
        db.session.commit()

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class Afiliated(db.Model):
    __tablename__ = "afiliated"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    status = db.Column(db.Boolean)
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def config(cls):
        return Config.query.filter_by(name="afiliation").first() or False

    def expired(self, now=None):
        if self.status != 1:
            return
        if now is None:
            now = dateV.date_today()

        if now >= self.end_date:
            self.status = 0
            db.session.add(self)
            db.session.commit()

"""
Agregar foranea a user_id
ALTER TABLE lottery MODIFY COLUMN user_id INT NULL;
delete from lottery where lottery.user_id NOT IN (SELECT id FROM user);
ALTER TABLE lottery ADD FOREIGN KEY (user_id) REFERENCES user (id) ON DELETE CASCADE ON UPDATE CASCADE;
"""
class Lottery(db.Model):
    __tablename__ = "lottery"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(255), db.ForeignKey(User.id))
    amount = db.Column(db.Integer, default=0)
    _config = None

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def config(cls):
        if not cls._config:
            cls._config = Config.query.filter_by(name="lottery").first()
        return cls._config
    
    @classmethod
    def is_active(cls, today):
        active = cls.config().options.get("active")
        if not active:
            return False
        if not active["is_active"]:
            return False
        end = cls.end_date
        if today >= end:
            return False
        return True
    
    @classmethod
    @property
    def start_date(cls):
        config = cls.config()
        active = config.options.get("active")
        if not active:
            return None
        start = config.options.get("active").get("start_date")
        return date.fromisoformat(start)
    
    @classmethod
    @property
    def end_date(cls)->date:
        start = cls.start_date
        duration = cls.duration
        if not (start and duration):
            return None
        return start + duration
    
    @classmethod
    @property
    def duration(cls):
        active = cls.config().options.get("active")
        if not active:
            return None
        return timedelta(days=active.get("duration"))

    @classmethod
    def reward_user(cls, user:User, buy_amount:float):
        config = cls.config()
        if not config.options.get("active"):
            return ( False, "Lottery is not active")
        if not buy_amount >= config.options.get("min_buy"):
            return ( False, "Buying amount must be greater than or equal to min buying amount")

        uLottery = Lottery.query.filter(Lottery.user_id == user.id).first()
        parent_reward = False

        if not uLottery:
            uLottery = Lottery(user_id = user.id, amount = config.options.get("buy_reward"))
            db.session.add(uLottery)
            parent_reward = config.options.get("child_first_buy_reward")

        parent = user.parent
        if parent:
            pLottery = Lottery.query.filter(Lottery.user_id == parent.id).first()
            if pLottery:
                pLottery.amount += parent_reward or config.options.get("child_buy_reward")
                db.session.add(pLottery)

        return True, "Todo correcto"


class PagoMovilRequest(db.Model):
    __tablename__ = "pago_movil_request"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    phone = db.Column(db.String(16), nullable=False)
    banco = db.Column(db.String(16), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    money_type = db.Column(db.String(10), default="bs")

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class Suggestion(db.Model):
    __tablename__ = "suggestion"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    message = db.Column(db.String(64), nullable=False)
    date = db.Column(db.Date(), default=dateV.date_today())
    status = db.Column(db.Boolean, nullable=False, default=False)

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class SupportProducts(db.Model):
    __tablenmae__ = "support_products"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    subject = db.Column(db.String(64), nullable=False)
    file_path = db.Column(db.String(64), nullable=False)
    description = db.Column(db.String(255), default="")
    type = db.Column(db.String(64), nullable=False)
    type_id = db.Column(db.Integer)
    status = db.Column(db.Integer, default=1)
    date = db.Column(db.Date(), default=dateV.date_today)

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    def img_path(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'assets/support_img/{self.file_path}/')

    @property
    def product_schema(self):
        data_return = dict()
        
        if self.type == "account":
            account, title =  (
                db.session.query(StreamingAccount, Platform.name)
                .join(StreamingAccount.platform)
                .filter(StreamingAccount.id == self.type_id)
                .first()
            )
            data_return = {
                "title":title,
                "start_date":account.start_date,
                "end_date":account.end_date,
                "email":account.email,
                "password":account.password,
            }
        if self.type == "screen":
            screen, account, title =  (
                db.session.query(Screen, StreamingAccount, Platform.name)
                .join(Screen.account)
                .join(StreamingAccount.platform)
                .filter(Screen.id == self.type_id)
                .first()
            )
            data_return = {
                "title":title,
                "start_date":account.start_date,
                "end_date":account.end_date,
                "email":account.email,
                "password":account.password,
                "profile":screen.profile,
                "pin":screen.pin(),
            }
        elif self.type == "product":
            pass
        return data_return
        


class Supplier(db.Model):
    __tablename__ = "supplier"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    name = db.Column(db.String(255))
    platform_that_supplies = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(255))
    local_phone = db.Column(db.String(255))
    country = db.Column(db.String(255))
    paypal = db.Column(db.String(255))
    pago_movil = db.Column(db.String(255))
    bank = db.Column(db.String(255))

    accounts = db.relationship(
        "StreamingAccount",
        backref=db.backref("supplier"))

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class BuyHistory(db.Model):
    __tablename__ = "buy_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    product = db.Column(db.String(255))
    price = db.Column(db.Float)
    references_reward = db.Column(db.Float)
    buy_description = db.Column(db.String(255))
    fecha = db.Column(db.DateTime)
    money_type = db.Column(db.String(10), default="bs")
    coupon_code = db.Column(db.String(32))

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def all_of_user(cls, user):
        return BuyHistory.query.filter(BuyHistory.user_id == user.id).order_by(BuyHistory.fecha.desc()).all()

    @classmethod
    def all_of_child(cls, user):
        subquery = db.text(f"buy_history.user_id IN (SELECT id FROM user WHERE parent_id = {user.id}) ")
        # subquery = db.select(db.text(f"id from user where parent_id = {user.id}"))
        return db.session.query(cls, User).join(User, User.id == cls.user_id).filter(subquery).order_by(BuyHistory.fecha.desc()).all()

class Notifications(db.Model):
    __tablename__ = "notifications"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    date = db.Column(db.DateTime)
    content = db.Column(db.String(255))
    showed = db.Column(db.Integer)

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class PaymentMethod(db.Model):
    __tablename__ = "payment_method"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    payment_platform_name = db.Column(db.String(255))
    data = db.Column(db.String(255))
    file_name = db.Column(db.String(255), default="")
    money_type = db.Column(db.String(10), default="bs")

    recharges = db.relationship(
        "RechargeRequest",
        backref=db.backref("payment_method"))

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class RechargeRequest(db.Model):
    __tablename__ = "recharge_request"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    payment_method_id = db.Column(db.Integer, db.ForeignKey(PaymentMethod.id))
    date = db.Column(db.DateTime)
    amount = db.Column(db.Float)
    reference = db.Column(db.String(50))
    status = db.Column(db.String(100))

    NEW = "no verificado"
    VERIFIED = "verificado"
    REJECT = "rechazado"

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    #los duplicados son cuando la persona envia el mismo reporte varias veces por desespero
    @classmethod
    def revisarDuplicados(cls, reference, amount, payment_method_id, user):
        duplicate = RechargeRequest.query\
            .filter(RechargeRequest.status=="no verificado")\
            .filter(RechargeRequest.reference==reference)\
            .filter(RechargeRequest.amount==amount)\
            .filter(RechargeRequest.user_id==user.id)\
            .first()
        if not duplicate:
            recharge = RechargeRequest(user_id = user.id, date=dateV.datetime_now(), status="no verificado", payment_method_id=payment_method_id, amount=amount, reference=reference)
            db.session.add(recharge)
            db.session.commit()
            return recharge
        else:
            return False

    # son cuando quieren meter varias veces la misma recarga para sacar plata
        # Esta parte verifica si el metodo de pago es el mismo, pero salio el caso de que el pago fue reportado por pago movil y por transferencia a la misma cuenta
        # por eso se quitara la verificacion del metodo de pago
        # duplicate = RechargeRequest.query.filter_by(status="verificado", payment_method=payment_method, reference = reference, amount=amount).first()
    def revisarEstafaRepetido(self):
        duplicates = RechargeRequest.query\
            .filter(RechargeRequest.status=="verificado")\
            .filter(RechargeRequest.reference==self.reference)\
            .filter(RechargeRequest.amount==self.amount)\
            .all()
        if duplicates:
            alertMessage = "Este reporte a sido fichado como un caso de posible duplicacion, será revisado por los administradores"
            alerts = []
            for rr in duplicates:
                alert = RechargeAlerts(last=self.id, first=rr.id, status=0)
                alerts.append(alert)
            notifi = Notifications(user_id=self.user_id, date=dateV.date_today(), content=alertMessage, showed=0)
            db.session.add_all([*alerts, notifi])
            db.session.commit()
            return {"status": False, "error":alertMessage}
        else: return {"status": True, "message":"Su pedido de recarga a sido enviado exitosamente"}
        
    @classmethod
    def utilities_movements(cls, user):
        return RechargeRequest.query\
            .filter(RechargeRequest.user_id == user.id)\
            .filter(RechargeRequest.payment_method_id == -123)\
            .order_by(RechargeRequest.date.desc())\
            .all()

# alter table platform add column year_price float not null default 0;
# alter table platform add column year_afiliated_price float not null default 0;
# alter table platform add column year_reference_reward float not null default 0;
class Platform(db.Model):
    __tablename__ = "platform"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    name = db.Column(db.String(255))
    url = db.Column(db.String(255))
    screen_amount = db.Column(db.Integer)
    price = db.Column(db.Float)
    afiliated_price = db.Column(db.Float)
    reference_reward = db.Column(db.Float)
    year_price = db.Column(db.Float)
    year_afiliated_price = db.Column(db.Float)
    year_reference_reward = db.Column(db.Float)
    file_name = db.Column(db.String(255))

    accounts = db.relationship("StreamingAccount", backref="platform")
    complete_account_requests = db.relationship("CompleteAccountRequest", backref="platform")

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    def img_path(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'assets/img/{self.file_name}/')

    @classmethod
    def all_with_price(cls):
        # Crear un alias para la tabla streaming_account para la subconsulta eti
        sa_1 = db.aliased(StreamingAccount, name='streaming_account_1')

        screen_count_subquery = (
            db.session.query(
                db.func.count(Screen.id)
            )
            .filter(Screen.client_id.is_(None))
            .filter(Screen.account_id == StreamingAccount.id)
            .label('screens_count')
        )
        screen_count_subquery = (
            db.session.query(
                StreamingAccount.id.label('account_id'),
                screen_count_subquery
            )
            .group_by(StreamingAccount.id)
            .subquery()
        )

        # Subconsulta max_screens: obtén la cantidad máxima de pantallas sin cliente por plataforma
        max_screens_subquery = (
            db.session.query(
                sa_1.platform_id,
                db.func.max(screen_count_subquery.c.screens_count).label('max_screens_count')
            )
            .join(screen_count_subquery, sa_1.id == screen_count_subquery.c.account_id)
            # .filter(sa_1.end_date > dateV.date_today())
            .filter(db.func.date_add(sa_1.start_date, db.text(f"interval streaming_account_1.days day")) > dateV.date_today())
            .group_by(sa_1.platform_id)
            .subquery()
        )
        # Consulta principal
        query = (
            db.session.query(
                Platform,
                StreamingAccount,
                screen_count_subquery.c.screens_count
            )
            .join(StreamingAccount, StreamingAccount.platform_id == Platform.id)
            .join(screen_count_subquery, StreamingAccount.id == screen_count_subquery.c.account_id)
            .join(
                max_screens_subquery,
                db.and_(
                    StreamingAccount.platform_id == max_screens_subquery.c.platform_id,
                    screen_count_subquery.c.screens_count == max_screens_subquery.c.max_screens_count
                )
            )
            .order_by(Platform.id)
        )
        return query

    def coupon_resource(self, level):
        if level == 1: return {"resource":"complete_account_request", "resource_id":self.id}
        if level == 2: return {"resource":"all_complete", "resource_id":self.id}
        if level == 3: return {"resource":"platform", "resource_id":self.id}
        if level == 4: return {"resource":"category", "resource_id":self.four_level()}
        if level == 5: return {"resource":"all", "resource_id":"*"}

    def four_level(self):
        return db.session.query(db.text("group_concat(category_id)"))\
            .select_from(ProductCategories)\
            .filter(ProductCategories.product_id==self.id)\
            .filter(ProductCategories.product_type=="platform")\
            .group_by(ProductCategories.product_id)\
            .group_by(ProductCategories.product_type)\
            .first

@timeDecorator
class StreamingAccount(db.Model):
    __tablename__ = "streaming_account"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    platform_id = db.Column(db.Integer, db.ForeignKey(Platform.id))
    supplier_id = db.Column(db.Integer, db.ForeignKey(Supplier.id))
    start_date = db.Column(db.Date())
    # end_date = db.Column(db.Date())
    email = db.Column(db.String(255))
    password = db.Column(db.String(255))
    price = db.Column(db.Float, nullable=False, default=0)
    afiliated_price = db.Column(db.Float, nullable=False, default=0)
    reference_reward = db.Column(db.Float, nullable=False, default=0)
    pin = db.Column(db.Integer)
    days = db.Column(db.Integer, nullable = False, default=0)
    active = db.Column(db.Boolean, default=True)

    screens = db.relationship("Screen", backref="account")
    complete_accounts = db.relationship("CompleteAccountRequest", backref="account", uselist=True)
    expired_accounts = db.relationship("ExpiredAccount", backref="account", uselist=True)
    

    @classmethod
    def c_end_date(cls):return db.func.date_add(cls.start_date, db.text(f"interval {cls.__tablename__}.days day")).label("end_date")

    @property
    def end_date(self):
        return self.start_date + timedelta(days=self.days)
    
    @end_date.setter
    def end_date(self, end_date):
        if isinstance(end_date, str):
            end_date = date.fromisoformat(end_date)
        if not isinstance(end_date, date):
            raise Exception("Debe ser una fecha valida")
        time = end_date - self.start_date
        self.days = time.days

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    
    def coupon_resource(self, level):
        if level == 1: return {"resource":"screen", "resource_id":self.platform_id}
        if level == 2: return {"resource":"all_screen", "resource_id":self.platform_id}
        if level == 3: return {"resource":"platform", "resource_id":self.platform_id}
        if level == 4: return {"resource":"category", "resource_id":self.four_level()}
        if level == 5: return {"resource":"all", "resource_id":"*"}

    def four_level(self):
        return db.session.query(db.text("group_concat(category_id)"))\
            .select_from(ProductCategories)\
            .filter(ProductCategories.product_id==self.platform_id)\
            .filter(ProductCategories.product_type=="platform")\
            .group_by(ProductCategories.product_id)\
            .group_by(ProductCategories.product_type)\
            .first


@timeDecorator
class Screen(db.Model):
    __tablename__ = "screen"
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey(User.id))
    account_id = db.Column(db.Integer, db.ForeignKey(StreamingAccount.id))
    profile = db.Column(db.Integer)
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())
    month_pay = db.Column(db.String(11), default="si")

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    def pin(self, account=None):
        if not account:
            account = self.account
        p = self.profile
        pin = str(2 + p).rjust(2, "0") if 2 + p < 10 else str(2 + p)
        return f"2{p}{pin}" if account.pin else "No usa pin"


# ALTER TABLE complete_account_request ADD COLUMN account_type NOT NULL default = "month";
class CompleteAccountRequest(db.Model):
    __tablename__ = "complete_account_request"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    account_id = db.Column(db.Integer, db.ForeignKey(StreamingAccount.id))
    platform_id = db.Column(db.Integer, db.ForeignKey(Platform.id))
    status = db.Column(db.Integer)
    account_type = db.Column(db.String(128), nullable=False, default="month")
    # request_user_money = db.relationship("RequestUserMoney", backref="complete_account_request", uselist=False)

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class ExpiredAccount(db.Model):
    __tablename__ = "expired_accounts"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    account_id = db.Column(db.Integer, db.ForeignKey(StreamingAccount.id))
    expired_date = db.Column(db.Date)

    def save_me(self):
        db.session.add(self)
        db.session.commit()


class UserProducts(db.Model):
    __tablename__ = "user_products"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    product_id = db.Column(db.Integer, db.ForeignKey(ProductsByRequest.id))
    data = db.Column(db.JSON)
    status = db.Column(db.Integer)
    start_date = db.Column(db.Date())
    end_date = db.Column(db.Date())

    def save_me(self):
        db.session.add(self)
        db.session.commit()

    @classmethod
    def all_with_dependencies(cls, user=None, onlyAccept=True):
        query = db.session.query(cls, ProductsByRequest).join(
            ProductsByRequest, ProductsByRequest.id == cls.product_id)
        if user:
            query = query.filter(cls.user_id == user)
        if onlyAccept:
            query = query.filter(cls.status == 1)
        return query.all()
    

class OwnedPaymentMethod(db.Model):
    __tablename__ = "owned_payment_method"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    payment_method_id = db.Column(db.Integer, db.ForeignKey(PaymentMethod.id))

    user = db.relationship('User', uselist=False)
    payment_method = db.relationship('PaymentMethod', uselist=False)

    def save_me(self):
        db.session.add(self)
        db.session.commit()

class Category(db.Model):
    __tablename__="category"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))

    product_category=db.relationship("ProductCategories", uselist=True, backref="category")
    

class ProductCategories(db.Model):
    __tablename__="products_category"
    id = db.Column(db.Integer, primary_key=True)
    category_id= db.Column(db.Integer, db.ForeignKey(Category.id))
    product_id= db.Column(db.Integer, index=True)
    product_type=db.Column(db.String(255))

    # category=db.relationship("Category", uselist=True)


f"""
Coupon doc:
    Resource apunta al tipo de producto al que sel e va a hacer descuento, y resorce id es para especificar los disponible son:
    
    nivel 1:
        - screen                        
        - complete_account_request
        - product_by_request
    nivel 2:
        - all_screen
        - all_complete
    nivel 3:
        - product
        - platform
    nivel 4:
        - category
    nivel 5:
        - all
"""
LEVEL_1=("screen", "complete_account_request", "product_by_request")
LEVEL_2=("all_screen", "all_complete")
LEVEL_3=("product", "platform")
LEVEL_4=("category", )
LEVEL_5=("all", )

class Coupon(db.Model):
    __tablename__="coupon"
    code = db.Column(db.String(32), primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey(User.id))
    status= db.Column(db.Integer)
    resource = db.Column(db.String(32))
    resource_id= db.Column(db.Integer)
    discount=db.Column(db.Float)
    discount_type = db.Column(db.String(32))
    uses= db.Column(db.Integer)

    request_user_money=db.relationship("RequestUserMoney", uselist=True, backref="coupon")

    f"""Hace referencia al nivel del recurso apuntado, vease la documentacion de cupon"""
    @property
    def level(self):
        if self.resource in LEVEL_1: return 1
        if self.resource in LEVEL_2: return 2
        if self.resource in LEVEL_3: return 3
        if self.resource in LEVEL_4: return 4
        if self.resource in LEVEL_5: return 5

    def verify_resource(self, product_resource):
        level = self.level
        if level == 1: return self.resource==product_resource["resource"] and self.resource_id == product_resource["resource_id"]
        elif level == 2: return self.resource==product_resource["resource"]
        elif level == 3: return self.resource==product_resource["resource"]
        elif level == 4: 
            if not self.resource==product_resource["resource"]:
                return False
            product_resource = product_resource["resource_id"]()
            if product_resource is None:
                return False
            categories =    product_resource[0].split(",")
            resource_id = str(self.resource_id)
            return resource_id in categories
        elif level == 5: return True
        else:return False
    
    def reduce_price(self, price):
        new_price = price
        if self.discount_type == "%":
            percent = self.discount / 100
            discount = new_price * percent
            new_price -= discount
        else:
            discount = self.discount
            new_price -= discount
        return new_price if new_price >= 0 else 0

class RequestUserMoney(db.Model):
    __tablename__="request_user_money"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    request_id = db.Column(db.Integer, index=True)
    request_type = db.Column(db.String(32))
    amount = db.Column(db.Float, nullable=False, default=0)
    money_type = db.Column(db.String(10), default="bs")
    coupon_code = db.Column(db.String(32), db.ForeignKey(Coupon.code))

class FrequentQuestion(db.Model):
    __tablename__="frequent_questions"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(64), nullable=False)
    content = db.Column(db.String(1020), nullable=False)
    
class Banner(db.Model):
    __tablename__="banners"
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    url_redirect = db.Column(db.String(255), nullable=False)
    
    def img_path(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'assets/img/{self.file_name}/')

class DocumentRequest(db.Model):
    __tablename__="document_requests"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    file_name = db.Column(db.String(255), nullable=False)
    status = db.Column(db.Integer, nullable=False, default=0)
    
    def img_path(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'assets/documents/{self.file_name}/')

class GoogleData(db.Model):
    __tablename__="google_data"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    email = db.Column(db.String(255), nullable=False)
    image_url = db.Column(db.String(255), nullable=False)
    google_id = db.Column(db.String(255), nullable=False)
    is_google_register = db.Column(db.Boolean, default=False)
    
class PlatinumMembers(db.Model):
    __tablename__="platinum_members"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey(User.id))
    start_date = db.Column(db.Date())
    status = db.Column(db.Integer, nullable=False, default=0)

class EmailCode(db.Model):
    __tablename__="email_code"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    generated_date = db.Column(db.DateTime(timezone=True), onupdate=dateV.datetime_now)

    def verify_validation(self, code, now):
        if self.code != code:
            raise Exception("El código de confirmación es incorrecto")
        if not self.is_valid_time(now):
            raise Exception("El código de confirmación a expirado")

    def is_valid_time(self, now):
        add_5_minutes = self.generated_date.astimezone(pytz.timezone('America/Caracas')) + timedelta(minutes=6)
        
        if add_5_minutes < now:
            return False
        return True
        now = datetime.now(time_zone)

        # Verifica si el código fue generado hace menos de 5 minutos
        if email_code.generated_date and (now - email_code.generated_date) < timedelta(minutes=5):
            pass
google_drive_products_categories = db.Table('google_drive_products_categories',
    db.Column('google_drive_product_id', db.Integer, db.ForeignKey('google_drive_product.id')),
    db.Column('google_drive_category_id', db.Integer, db.ForeignKey('google_drive_categories.id'))
)

class GoogleDriveProductTypeEnum(enum.Enum):
    platinum = "platinum"
    vip = "vip"
    free = "free"

"""
INSERT INTO config(NAME, OPTIONS) VALUES ("vip", "{\"price\": 2, \"reference_reward\": 0}");
INSERT INTO config(NAME, OPTIONS) VALUES ("platinum", "{\"price\": 2, \"reference_reward\": 0}");
"""
class GoogleDriveProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(255), nullable=False)
    url_redirect = db.Column(db.String(255), nullable=False)
    product_type = db.Column(db.String(255), nullable=False)
    categories = db.relationship('GoogleDriveCategories', secondary=google_drive_products_categories, backref='products')


    def img_path(self):
        import os
        from flask import request
        return os.path.join(request.host_url, f'assets/img/{self.file_path}/')

class GoogleDriveCategories(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(32))

class LotteryV2():
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    # Otros campos según sea necesario

class Ticket():
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    lottery_id = db.Column(db.Integer, db.ForeignKey('lottery_v2.id'), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    # Otros campos según sea necesario

    def __repr__(self):
        return f"Ticket {self.code} - User {self.user_id} - Lottery {self.lottery_id}"

class AfiliationGiftCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id') )
    receiver_id = db.Column(db.Integer, db.ForeignKey('user.id') )
    code = db.Column(db.String(20), unique=True, nullable=False)
    type = db.Column(db.String(255), nullable=False)

def init_DB(app):
    db.init_app(app=app)

    with app.app_context():
        db.create_all()
    return db
