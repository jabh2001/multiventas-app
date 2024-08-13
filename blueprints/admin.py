from flask import Blueprint, send_from_directory, g
from blueprints.admin_api.auth import auth_bp
from blueprints.admin_api.clients import clients_bp
from blueprints.admin_api.manage import manage_bp
from blueprints.admin_api.platform_sales import platform_sales_bp
from blueprints.admin_api.products_sales import products_sales_bp
from blueprints.admin_api.system import system_bp
from blueprints.admin_api.transaction import transactions_bp
from blueprints.admin_api.prize import prize_bp
from blueprints.admin_api.credits import credits_bp
from services.general_service import update_screens
from services.general_service import update_products
from services.general_service import update_afiliated
from services.general_service import update_exchange_rate
from services.general_service import update_prize_points
from services.admin_service.system_services import get_notifications
from libs.models import Platform, ProductsByRequest, Prize, db
import os

admin_bp = Blueprint('admin_bp', __name__)
api = Blueprint('api', __name__)

api.register_blueprint(auth_bp, url_prefix='/auth')
api.register_blueprint(clients_bp, url_prefix='/clients')
api.register_blueprint(manage_bp, url_prefix='/manage')
api.register_blueprint(platform_sales_bp, url_prefix='/platform-sales')
api.register_blueprint(products_sales_bp, url_prefix='/products-sales')
api.register_blueprint(system_bp, url_prefix='/system')
api.register_blueprint(transactions_bp, url_prefix='/transactions')
api.register_blueprint(credits_bp, url_prefix='/credits')
api.register_blueprint(prize_bp, url_prefix='/prize')

@api.route("/notification/")
@api.route("/notifications/")
def notification():
    notify = get_notifications()
    return dict(notify)

admin_bp.register_blueprint(api, url_prefix='/api')

@admin_bp.route("/update/")
@admin_bp.route("/updates/")
def updates():
    try:
        update_screens(g.today)
        update_products(g.today)
        update_afiliated(g.today)
        update_exchange_rate(g.today)
        update_prize_points(g.today)
        print("Update done!")

        return {
            "error":False,
            "msg":"success update!"
        }
    except Exception as e:
        raise e
        return {
            "error":True,
            "msg":str(e)
        }
    
@admin_bp.route('/', defaults={"path":""})
@admin_bp.route('/<path:path>')
def index(path):
    return send_from_directory(os.path.join(os.getcwd(), "templates", "admin"), "index.html")

def deleteNotUsage():
    platform_query = db.session.query(Platform.file_name.label("file_name"))
    products_query = db.session.query(ProductsByRequest.file_path.label("file_name"))
    prize_query = db.session.query(Prize.img_url.label("file_name"))
    files = platform_query.union(products_query).union(prize_query)
    images = [ name for name, *_ in files]
    for img in os.listdir(path="static/img/"):
        if os.path.isfile(img) and img not in images:
            os.remove(path="static/img/"+img)
    pass
