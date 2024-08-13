from marshmallow import EXCLUDE, fields, validates, ValidationError
from flask_marshmallow import Marshmallow
from flask_jwt_extended import create_access_token
from libs.validators import is_valid_email, is_valid_phone, range, is_valid_money_type
from marshmallow_sqlalchemy.fields import Nested
from services.general_service import wsphone

from libs.models import *

ma = Marshmallow()


class BaseMeta:
    load_instance = True
    unknown = EXCLUDE
    dump_only = "id",


class BuyHistorySchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = BuyHistory
    date = fields.Function(lambda history: history.fecha.strftime("%d-%m-%Y"))
    description = fields.Function(lambda history: history.buy_description)
    amount = fields.Function(lambda history: history.price)


class CompleteAccountRequestSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = CompleteAccountRequest


class ExpiredAccountSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = ExpiredAccount


class NotificationsSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Notifications


class PaymentMethodSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = PaymentMethod

    @validates("money_type")
    def validate_money_type(self, value):
        return is_valid_money_type(value)


class PlatformSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Platform


class ProductsByRequestSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = ProductsByRequest


class RechargeAlertsSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = RechargeAlerts


class RechargeRequestSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = RechargeRequest


class ScreenSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Screen
    getPin = fields.Function(lambda screen: screen.pin())


class StreamingAccountSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = StreamingAccount
    end_date = fields.Function(lambda account: account.end_date.isoformat())


class SupplierSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Supplier


class UserSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = User
    link = fields.Function(lambda user: f"/signup/{user.id}")
    wsphone = fields.Function(lambda user: wsphone(user.phone))
    access_token = fields.Function(lambda user: create_access_token(identity=user))
    google_data = Nested("GoogleDataSchema")
    is_vip = fields.Function(lambda user: user.is_vip())
    is_platinum = fields.Function(lambda user:user.is_platinum())


    @validates("email")
    def validate_email(self, value):
        if User.query.filter(User.email == value).first():
            raise ValidationError(
                "Ya existe una cuenta de usuario registrado con ese correo")
        return is_valid_email(value)

    @validates("phone")
    def validate_phone(self, value):
        return is_valid_phone(value)

    @validates("password")
    def validate_password(self, value):
        return range(value, min=8)

    @validates("username")
    def validate_username(self, value):
        return range(value, min=3)


class UserProductsSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = UserProducts


class WalletSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Wallet


class ConfigSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Config


class AfiliatedSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Afiliated
    user = Nested("UserSchema", only=("id", "username"))


class LotterySchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Lottery
    user = Nested("UserSchema", only=("id", "username", "email", "ci"))


class PagoMovilRequestSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = PagoMovilRequest


class SupportProductsSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = SupportProducts
    img_path = fields.Function(lambda support: f"{support.img_path()}")


class SuggestionSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Suggestion


class ExchangeRateSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = ExchangeRate


class OwnedPaymentMethodSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = OwnedPaymentMethod

class CategorySchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Category
    product_category = Nested("ProductCategoriesSchema", many=True)

class ProductsForCategorySchema(ma.Schema):
    class Meta:
        fields =  ("id", "name", "pro_name", "type")

class ProductCategoriesSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = ProductCategories

class CouponSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Coupon
    
class RequestUserMoneySchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = RequestUserMoney

class FrequentQuestionSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = FrequentQuestion

class BannerSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Banner
    img_path = fields.Function(lambda banner: banner.img_path())

class DocumentRequestSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = DocumentRequest
    img_path = fields.Function(lambda document: document.img_path())
    user = Nested("UserSchema", only=("id", "username"))
        
class GoogleDataSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = GoogleData

class PlatinumMembersSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = PlatinumMembers
    user = Nested("UserSchema", only=("id", "username", "email"))
        
class EnumField(fields.Field):
    def _serialize(self, value, attr, obj, **kwargs):
        if value is None:
            return None
        return value.value

class GoogleDriveProductSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = GoogleDriveProduct
    img_path = fields.Function(lambda document: document.img_path())

class GoogleDriveCategoriesSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = GoogleDriveCategories
    products = Nested("GoogleDriveProductSchema", only=("id", "title"), many=True)

class AfiliationGiftCodeSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = AfiliationGiftCode


class CreditsTitaniumPriceSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = CreditsTitaniumPrice

class CreditsVipPriceSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = CreditsVipPrice

class PrizeSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = Prize
    img_path = fields.Function(lambda prize: f"{prize.img_path()}")

class PrizeWalletSchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = PrizeWallet
    user = Nested("UserSchema", only=("id", "username", "email"))

class PrizeHistorySchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = PrizeHistory

class PrizeWalletHistorySchema(ma.SQLAlchemyAutoSchema):
    class Meta(BaseMeta):
        model = PrizeWalletHistory

def init_schemas(app):
    ma.init_app(app=app)
    return ma
