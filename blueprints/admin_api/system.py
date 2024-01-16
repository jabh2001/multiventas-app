from flask import Blueprint, request, jsonify, g
from flask_jwt_extended import jwt_required, current_user
from libs.models import Category, Platform, ProductsByRequest, ProductCategories, Coupon, ExchangeRate, SupportProducts, User, Config, FrequentQuestion, Banner, DocumentRequest, Afiliated, PlatinumMembers, GoogleDriveCategories, GoogleDriveProduct, GoogleDriveProductTypeEnum, Lottery, AfiliationGiftCode, db
from libs.schemas import CategorySchema, ProductsForCategorySchema, CouponSchema, ExchangeRateSchema, SupportProductsSchema, UserSchema, FrequentQuestionSchema, BannerSchema, DocumentRequestSchema, AfiliatedSchema, PlatinumMembersSchema, GoogleDriveCategoriesSchema, GoogleDriveProductSchema, LotterySchema, ConfigSchema, AfiliationGiftCodeSchema
from services.admin_service.system_services import update_product_category
from services.admin_service.system_services import get_coupons
from services.admin_service.system_services import create_google_drive_product
from services.admin_service.system_services import create_lottery_tickets_to_xlsx
from services.general_service import convert_str_to_int, save_file, delete_file, create_affiliation_gift_code
import requests

system_bp = Blueprint('system_bp', __name__)

@system_bp.route("/category/", methods=["GET", "POST"])
@system_bp.route("/category/<category_id>/", methods=["GET", "PUT", "DELETE"])
@system_bp.route("/categories/", methods=["GET", "POST"])
@system_bp.route("/categories/<category_id>/", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def category(category_id=None):
    category_schema = CategorySchema()
    if category_id:
        category = Category.query.get(category_id)
        if not category:
            return {
                "status":False,
                "msg":"No se ha encontrado la categoría"
            }
        if request.method == "PUT":
            try:
                msg = update_product_category(category, request.form)
                return { 
                    "status":True,
                    "category":category_schema.dump(category),
                    "msg":msg
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        if request.method == "DELETE":
            try:
                db.session.delete(category)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"La categoría se ha eliminado correctamente"
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return {}
    else:
        if request.method == "POST":
            try:
                category=Category(name=request.json["category_name"])
                db.session.add(category)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se agregó la nueva categoría correctamente",
                    "category":category_schema.dump(category),
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return category_schema.dump(Category.query, many=True)

@system_bp.route("/products-for-category/")
@jwt_required()
def products_for_category(category_id=None):
    schema = ProductsForCategorySchema(many=True)
    pro_platform = db.session.query(
        Platform.id,
        Platform.name,
        db.func.replace( db.func.lower(Platform.name), " ", "_" ).label("pro_name"),
        db.func.lower("platform").label("type")
    )
    pro_product = db.session.query(
        ProductsByRequest.id,
        ProductsByRequest.title.label("name"),
        db.func.replace( db.func.lower(ProductsByRequest.title), " ", "_" ).label("pro_name"),
        db.func.lower("product").label("type")
    )
    return schema.dump(pro_platform.union(pro_product))



@system_bp.route("/support/")
@system_bp.route("/support/<support_id>/", methods=["GET", "PUT"])
@system_bp.route("/supports/")
@system_bp.route("/supports/<support_id>/", methods=["GET", "PUT"])
@jwt_required()
def support(support_id=None):
    support_schema = SupportProductsSchema()
    if support_id:
        support_product = SupportProducts.query.get(support_id)
        if not  support_product:
            raise Exception("No existe ese ticket de soporte")
        if request.method == "PUT":
            try:
                if request.json["close"]:
                    support_product.status = 0
                    db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se ha cerrado el caso"
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return {
            **support_schema.dump(support_product),
            "product":support_product.product_schema
        }
    else:
        user_schema = UserSchema(only=("id", "username"))
        page = convert_str_to_int(request.args.get("page"), default_number=1)
        per_page = convert_str_to_int(request.args.get("size", 100), default_number=100)

        verified = request.args.get("verified", None)
        verified = verified if verified in ["true", "false"] else "false"
        query = db.session.query(SupportProducts, User).join(SupportProducts.user).order_by(SupportProducts.id.desc())

        if verified == "true":
            query = query.filter(SupportProducts.status == 0).paginate(page=page, per_page=per_page, max_per_page=500, error_out=False)
            return {
                "last_page":query.pages,
                "data":[{**support_schema.dump(p), "user":user_schema.dump(u)} for p,u in query]
            }
        query = query.filter(SupportProducts.status == 1)
        return [{**support_schema.dump(p), "user":user_schema.dump(u)} for p, u in query]

@system_bp.route("/coupon/", methods=["GET", "POST"])
@system_bp.route("/coupon/<coupon_code>/", methods=["GET", "PUT", "DELETE"])
@system_bp.route("/coupons/", methods=["GET", "POST"])
@system_bp.route("/coupons/<coupon_code>/", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def coupon(coupon_code=None):
    coupon_schema = CouponSchema(session = db.session)
    if coupon_code:
        coupon = Coupon.query.get(coupon_code)
        if not coupon:
            return {
                "status":False,
                "msg":"Ha habido un problema al encontrar este cupón",
            }
        if request.method == "PUT":
            try:
                discount = float(request.json["discount"][:-1])
                discount_type = request.json["discount"][-1:]

                coupon_schema.load({
                    "code":coupon_code,
                    "status":request.json["status"],
                    "resource":request.json["resource"],
                    "resource_id":request.json["resource_id"],
                    "uses":request.json["uses"],
                    "discount":discount,
                    "discount_type":discount_type,
                 }, instance=coupon)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se ha actualizado el cupón",
                    "coupon":coupon_schema.dump(coupon)
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return coupon_schema.dump(coupon)
    else:
        if request.method == "POST":
            try:
                coupon_code = request.json["code"]
                new_coupon = Coupon.query.get(coupon_code)
                if new_coupon:
                    raise Exception("Ese cupón ya existe")

                discount = float(request.json["discount"][:-1])
                discount_type = request.json["discount"][-1:]
                if "$" != discount_type != "%":
                    raise Exception("El descuento debe incluir ( $ | % ) al final")
                
                coupon = coupon_schema.load({
                    "code":coupon_code,
                    "status":request.json["status"],
                    "resource":request.json["resource"],
                    "resource_id":request.json["resource_id"],
                    "uses":request.json["uses"],
                    "discount":discount,
                    "discount_type":discount_type,
                 })
                db.session.add(coupon)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Este cupón se ha creado correctamente",
                    "coupon":coupon_schema.dump(coupon),
                }
            except ValueError as e:
                return { 
                    "status":False,
                    "msg":"Debe ser un numero valido" 
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return get_coupons(coupon_schema)

@system_bp.route("/coupon-resource/<type>/")
@jwt_required()
def coupon_resource(type):
    if type in ("screen", "screens"):
        return [ {"value":p.id, "label":p.name} for p in Platform.query.all() ]
    if type in ("product", "products"):
        return [ {"value":p.id, "label":p.title} for p in ProductsByRequest.query.all() ]
    if type in ("category", "categories"):
        return [ {"value":p.id, "label":p.name} for p in Category.query.all() ]

@system_bp.route("/exchange-rate/")
@system_bp.route("/exchanges-rate/")
@system_bp.route("/exchange-rates/")
@system_bp.route("/exchanges-rates/")
@jwt_required()
def exchange_rate():
    return ExchangeRateSchema(many=True).dump(ExchangeRate.query)

@system_bp.route("/afiliation/", methods = ["GET", "PUT"])
@system_bp.route("/afiliations/", methods = ["GET", "PUT"])
@system_bp.route("/vip/", methods = ["GET", "PUT"])
@jwt_required()
def afiliation():
    vip = Config.query.filter(Config.name == "vip").first()

    if request.method == "PUT":
        vip.options = {
            "price":request.json["price"],
            "reference_reward":request.json["reference_reward"],
            "gift_code_price":request.json["gift_code_price"],
        }
        db.session.commit()
        try:
            return { 
                "status":True,
                "msg":"Se ha actualizado el precio del plan vip",
            }
        except Exception as e: 
            return { 
                "status":False,
                "msg":str(e) 
            }
    return vip.options
    
@system_bp.route("/platinum/", methods = ["GET", "PUT"])
@jwt_required()
def platinum():
    platinum = Config.query.filter(Config.name == "platinum").first()

    if request.method == "PUT":
        platinum.options = {
            "price":request.json["price"],
            "reference_reward":request.json["reference_reward"],
            "gift_code_price":request.json["gift_code_price"],
        }
        db.session.commit()
        try:
            return { 
                "status":True,
                "msg":"Se ha actualizado el precio del plan platinum",
            }
        except Exception as e: 
            return { 
                "status":False,
                "msg":str(e) 
            }
    return platinum.options

@system_bp.route("/afiliation/list/", methods = ["GET", "POST"])
@system_bp.route("/afiliations/list/", methods = ["GET", "POST"])
@system_bp.route("/afiliation/list/<afiliated_id>/", methods = ["PUT"])
@system_bp.route("/afiliations/list/<afiliated_id>/", methods = ["PUT"])
@jwt_required()
def afiliated(afiliated_id=None):
    afiliated_schema = AfiliatedSchema()
    if afiliated_id:
        try:
            return { 
                "status":True
            }
        except Exception as e: 
            return { 
                "status":False,
                "msg":str(e) 
            }
    else:
        if request.method == "POST":
            try:
                return { 
                    "status":True
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        members = db.session.query(Afiliated, User).join(Afiliated.user).order_by(Afiliated.status.desc())
        return afiliated_schema.dump([membership for membership, _ in members], many=True)

@system_bp.route("/platinum/list/", methods = ["GET", "POST"])
@system_bp.route("/platinum/accept/<platinum_member_id>/", methods = ["PUT"])
@jwt_required()
def platinum_members(platinum_member_id=None):
    platinum_schema = PlatinumMembersSchema()
    if platinum_member_id:
        try:
            memebership = PlatinumMembers.query.get(platinum_member_id)
            if not memebership:
                raise Exception("No se encontró esta membresía")
            if memebership.status:
                raise Exception("Ya se habia aceptado")
            memebership.status = True
            memebership.start_date = g.today
            db.session.commit()
            return { 
                "status":True,
                "msg":"Se ha marcado como aceptado"
            }
        except Exception as e: 
            return { 
                "status":False,
                "msg":str(e) 
            }
    else:
        if request.method == "POST":
            try:
                return { 
                    "status":True
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        members = db.session.query(PlatinumMembers, User).join(PlatinumMembers.user).order_by(PlatinumMembers.status.desc())
        if "active" in request.args:
            filter_ = 1 if request.args["active"] == "true" else 0
            members = members.filter(PlatinumMembers.status == filter_)
        return platinum_schema.dump([membership for membership, _ in members], many=True)

@system_bp.route("/frequent-question/", methods = ["GET", "POST"])
@system_bp.route("/frequent-questions/", methods = ["GET", "POST"])
@system_bp.route("/frequent-question/<fq_id>/", methods = ["PUT", "DELETE"])
@system_bp.route("/frequent-questions/<fq_id>/", methods = ["PUT", "DELETE"])
@jwt_required()
def frequent_question(fq_id=None):
    frequent_question_schema = FrequentQuestionSchema()
    if fq_id:
        fq = FrequentQuestion.query.get(fq_id)
        if not fq:
            return { 
                "status":False,
                "msg":"fallo al encontrar esa pregunta frecuente, intente de nuevo o recargue la página" 
            }

        if request.method == "PUT":
            try:
                frequent_question_schema.load(request.json, instance=fq, partial=True)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se ha editado correctamente",
                    "frequent_question":frequent_question_schema.dump(fq)
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        if request.method == "DELETE":
            try:
                db.session.delete(fq)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se ha eliminado correctamente",
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return frequent_question_schema.dump(fq)
    else:
        if request.method == "POST":
            try:
                fq = frequent_question_schema.load(request.json)
                db.session.add(fq)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se ha creado correctamente",
                    "frequent_question":frequent_question_schema.dump(fq)
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return frequent_question_schema.dump(FrequentQuestion.query, many=True)
        

@system_bp.route("/banner/", methods = ["GET", "POST"])
@system_bp.route("/banners/", methods = ["GET", "POST"])
@system_bp.route("/banner/<banner_id>/", methods = ["DELETE"])
@system_bp.route("/banners/<banner_id>/", methods = ["DELETE"])
@jwt_required()
def banner(banner_id=None):
    banner_schema = BannerSchema()
    if banner_id:
        if request.method == "DELETE":
            try:
                banner = Banner.query.get(banner_id)
                if not banner:
                    raise Exception("No existe ese banner")
                msg = "" if delete_file(banner.file_name) else "Ha habido un error al eliminar la imagen. "
                db.session.delete(banner)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":msg+"Se ha eliminado el banner correctamente"
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return {}
    else:
        if request.method == "POST":
            try:
                file = request.files["file"]
                filename = save_file(file)
                url_redirect = request.form["url_redirect"]
                banner = Banner(file_name=filename, url_redirect=url_redirect)

                db.session.add(banner)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se ha creado el banner correctamente"

                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return banner_schema.dump(Banner.query, many=True)
        
@system_bp.route("/document/")
@system_bp.route("/documents/")
@system_bp.route("/document/<document_id>/<action>/", methods = ["Put"])
@system_bp.route("/documents/<document_id>/<action>/", methods = ["Put"])
@jwt_required()
def document(document_id=None, action="set"):
    document_schema = DocumentRequestSchema()
    if document_id:
        try:
            msg = ""
            document_request = DocumentRequest.query.filter(DocumentRequest.id == document_id).filter(DocumentRequest.status == 0).first()
            if not document_request:
                raise Exception("No se ha encontrado esta peticion")

            if action == "set":
                document_request.status = 1
                try: int(request.json["document"])
                except: raise Exception("El documento debe ser un número valido")
                document_request.user.ci = request.json["document"]
                msg = "Se establecio el documento al usuario "
            elif action == "reject":
                document_request.status = 2
                msg = "Se rechazó el documento al usuario "
            else:
                raise Exception("Accion no controlada")
            db.session.commit()
            return { 
                "status":True,
                "msg":msg
            }
        except Exception as e: 
            return { 
                "status":False,
                "msg":str(e) 
            }
    return document_schema.dump(DocumentRequest.query.filter(DocumentRequest.status == 0), many = True)

@system_bp.route("/platinum-products-type/")
def platinum_products_types():
    return [i.value for i in GoogleDriveProductTypeEnum]

@system_bp.route("/platinum-products/", methods=["GET", "POST"])
@system_bp.route("/platinum-products/<product_id>/", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def platinum_products(product_id=None):
    google_drive_product_schema = GoogleDriveProductSchema()
    if product_id:
        google_drive_product = GoogleDriveProduct.query.get(product_id)
        try:
            if not google_drive_product:
                raise Exception("Producto no encontrado")
            if request.method == "PUT":
                pass
            if request.method == "DELETE":
                msg = "" if delete_file(google_drive_product.file_path) else "Ha habido un error al eliminar la imagen. "
                db.session.delete(google_drive_product)
                db.session.commit()
            return { 
                "status":True,
                "msg":"Se ha eliminado el producto correctamente",
            }
        except Exception as e: 
            return { 
                "status":False,
                "msg":str(e) 
            }
    else:
        if request.method == "POST":
            try:
                product = create_google_drive_product(request.form, request.files["img"])
                db.session.add(product)
                db.session.commit()
                return { 
                    "status":True,
                    "product":google_drive_product_schema.dump(product),
                    "msg":"El producto sse ha creado correctamente"
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return google_drive_product_schema.dump(GoogleDriveProduct.query, many=True)

@system_bp.route("/platinum-products-category/", methods=["GET", "POST"])
@system_bp.route("/platinum-products-category/<category_id>/", methods=["GET", "PUT", "DELETE"])
@system_bp.route("/platinum-products-categories/", methods=["GET", "POST"])
@system_bp.route("/platinum-products-categories/<category_id>/", methods=["GET", "PUT", "DELETE"])
@jwt_required()
def platinum_products_category(category_id=None):
    category_schema = GoogleDriveCategoriesSchema()
    if category_id:
        category = GoogleDriveCategories.query.get(category_id)
        if not category:
            return {
                "status":False,
                "msg":"No se ha encontrado la categoría"
            }
        if request.method == "PUT":
            try:
                new_products = (
                    GoogleDriveProduct.query
                    .filter(GoogleDriveProduct.id.in_(request.json["products_for_category"]))
                    .all()
                )
                category.products = new_products
                db.session.commit()
                return { 
                    "status":True,
                    "category":category_schema.dump(category),
                    "msg":"Se han actualizado la categoría"
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        if request.method == "DELETE":
            try:
                db.session.delete(category)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"La categoría se ha eliminado correctamente"
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }

        return category_schema.dump(category)
    else:
        if request.method == "POST":
            try:
                category=GoogleDriveCategories(name=request.json["category_name"])
                db.session.add(category)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se agregó la nueva categoría correctamente",
                    "category":category_schema.dump(category),
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return category_schema.dump(GoogleDriveCategories.query, many=True)

@system_bp.route("/lottery/download/", )
def lottery_download():
    return create_lottery_tickets_to_xlsx(Lottery.query.all())

@system_bp.route("/lottery/", methods=["GET", "PUT"])
@system_bp.route("/lotteries/", methods=["GET", "PUT"])
@system_bp.route("/lottery/<lottery_id>/", methods=["PUT"])
@system_bp.route("/lotteries/<lottery_id>/", methods=["PUT"])
def lottery(lottery_id=None):
    config = Lottery.config()
    if lottery_id:
        lottery = Lottery.query.get(int(lottery_id))
        if not lottery:
            return {"error":"Lotería no encontrada"}
        
        if request.method=="PUT":
            try:
                lottery.amount = request.json["amount"]
                db.session.commit()
            finally:
                return {
                    "lottery":LotterySchema().dump(lottery)
                }
    if request.method == "PUT":
        Lottery.query.delete( synchronize_session=False)
        db.session.commit()
    lotteries = (
        db.session.query(Lottery, User)
        .join(Lottery.user)
        .order_by(User.username.asc())
        .all()
    )
    return {
        "config":config.options,
        "data":LotterySchema(many=True).dump([lottery for lottery, user in lotteries])
    }

    
@system_bp.route("/config/<config_name>/", methods=["GET", "PUT"])
def config(config_name):
    config = Config.query.filter(Config.name == config_name).first()
    if not config:
        return {"error":"Configuración no encontrada"}
    
    if request.method == "PUT":
        config.options = {**request.json["options"]}
        db.session.commit()
        return {
            "status":True,
            "msg":"Configuración actualizada",
            "options":config.options
        }
    else:
        return {
            "status":False,
            "msg":""
        }

    return config.options

@system_bp.route("/affiliation-gift-code/", methods=["GET", "POST"])
@system_bp.route("/affiliation-gift-codes/", methods=["GET", "POST"])
@jwt_required()
def affiliation_gift_code():
    gift_code_schema = AfiliationGiftCodeSchema()
    user_schema = UserSchema(only=("username", "id"))

    if request.method == "POST":
        try:
            owner_id = request.json.get("owner_id")
            type = request.json.get("type")
            owner = None
            if owner_id:
                if "@" in owner_id:
                    owner = User.query.filter(User.email == owner_id).first()
                else:
                    owner = User.query.filter(User.ci == owner_id).first()
                if not owner:
                    raise Exception("No existe usuario con esa identificación")
                owner_id = owner.id
            else:
                owner = current_user
                owner_id = current_user.id
            code = create_affiliation_gift_code(AfiliationGiftCode.query.all())
            gift_code = AfiliationGiftCode(owner_id=owner_id, code=code, type=type)
            
            db.session.add(gift_code)
            db.session.commit()

            return { 
                "status":True,
                "msg":"Todo ha ido como se esperaba",
                "code":{
                    **gift_code_schema.dump(gift_code),
                    "owner":user_schema.dump(owner),
                }
            }
        except Exception as e: 
            return { 
                "status":False,
                "msg":str(e) 
            }
    owner = db.aliased(User, name='owner')
    receiver = db.aliased(User, name='receiver')

    all_codes = (
        db.session.query(AfiliationGiftCode, owner, receiver)
        .join(owner, AfiliationGiftCode.owner_id == owner.id)
        .join(receiver, AfiliationGiftCode.receiver_id == receiver.id, isouter=True)
        .all()
    )
    return [
        {
            **gift_code_schema.dump(code),
            "owner":user_schema.dump(owner),
            "receiver":user_schema.dump(receiver),
        } for code, owner, receiver in all_codes
    ]
    return gift_code_schema.dump()
"""
    if _id:
        if request.method == "PUT":
            try:
                return { 
                    "status":True
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return {}
    else:
        if request.method == "POST":
            try:
                print(request.json)
                return { 
                    "status":True
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return []
"""