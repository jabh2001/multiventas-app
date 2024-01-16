from flask import Blueprint, request, g
from flask_jwt_extended import jwt_required, current_user
from libs.models import ProductsByRequest, UserProducts, User, db
from libs.schemas import ProductsByRequestSchema, UserProductsSchema, UserSchema
from services.admin_service.produc_sales_services import create_product_by_request
from services.admin_service.produc_sales_services import update_product_by_request
from services.admin_service.produc_sales_services import active_user_product
from services.admin_service.produc_sales_services import reject_user_product


products_sales_bp = Blueprint('products_sales_bp', __name__)

@products_sales_bp.route("/product/", methods=["GET", "POST"])
@products_sales_bp.route("/product/<product_slug>/", methods=["GET", "PUT"])
@products_sales_bp.route("/products/", methods=["GET", "POST"])
@products_sales_bp.route("/products/<product_slug>/", methods=["GET", "PUT"])
@jwt_required()
def product_by_request(product_slug=None):
    if product_slug:
        product_schema = ProductsByRequestSchema()
        product = ProductsByRequest.query.filter(ProductsByRequest.title_slug == product_slug).first()

        if request.method == "PUT":
            try:
                file = request.files.get("photo")
                update_product_by_request(product, request.form, file)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se ha guardado el producto correctamente",
                    "product":product_schema.dump(product, many = False)
                }
            except Exception as e: 
                raise e
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        return product_schema.dump(product)
    else:
        product_schema = ProductsByRequestSchema(only=("id", "title", "title_slug"))
        if request.method == "POST":
            try:

                product = create_product_by_request(request.form, request.files["photo"])
                db.session.add(product)
                db.session.commit()
                return { 
                    "status":True,
                    "msg":"Se ha creado el producto correctamente",
                    "product":product_schema.dump(product)
                }
            except Exception as e: 
                return { 
                    "status":False,
                    "msg":str(e) 
                }
        notify = (
            db.session.query(
                    db.func.count(UserProducts.id)
                )
            .filter(UserProducts.product_id == ProductsByRequest.id)
            .filter(UserProducts.status == 0)
            .label("notify")
        )
        products = (
            db.session.query(
                notify,
                ProductsByRequest
            ).order_by(db.desc(notify))
        )
        return [
            {**product_schema.dump(p), "notification":n} for n, p in products
        ]

@products_sales_bp.route("/user-product/<product_slug>/", methods=["GET"])
@products_sales_bp.route("/user-products/<product_slug>/", methods=["GET"])
@products_sales_bp.route("/user-product/<product_slug>/<user_product_id>/", methods=["PUT"])
@products_sales_bp.route("/user-products/<product_slug>/<user_product_id>/", methods=["PUT"])
@jwt_required()
def user_products(product_slug, user_product_id=None):
    product = ProductsByRequest.query.filter(ProductsByRequest.title_slug == product_slug).first()
    if request.method == "PUT":
        user_product = UserProducts.query.get(user_product_id)
        status = request.json["status"]
        msg = request.json.get("description")
        if status == 1:
            active_user_product(user_product, g.today, msg)
        elif status == 2:
            reject_user_product(user_product, g.today, msg)
        try:
            return { 
                "status":True,
                "msg":"Se ha actualizado este producto correctamente",
            }
        except Exception as e: 
            return { 
                "status":False,
                "msg":str(e) 
            }
    user_products_schema = UserProductsSchema()
    user_schema = UserSchema(only=("id", "username"))
    status_options = {
        "requests":0,
        "accepts":1,
        "rejects":2,
        "expired":3,
        "config":-1,
    }
    status = 0

    try:status = status_options[request.args.get("status", "requests")]
    except Exception as e:pass

    if status != -1:

        user_products = (
            db.session.query(UserProducts, User)
            .join(UserProducts.user)
            .filter(UserProducts.product_id == product.id)
            .filter(UserProducts.status == status)
        )
        return [
            {
                **user_products_schema.dump(up),
                "user": user_schema.dump(user)
            } for up, user in user_products
        ]
    else:
        return {
            "campos":product.config["campos"],
            "price":product.config["price"],
        }

