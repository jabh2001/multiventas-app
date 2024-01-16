from flask import Blueprint, render_template, send_from_directory

from blueprints.client_api.auth import auth_bp
from blueprints.client_api.my_products import my_products_bp
from blueprints.client_api.products import products_bp
from blueprints.client_api.profile import profile_bp
from blueprints.client_api.recharges import recharges_bp
from blueprints.client_api.seller import seller_bp
from blueprints.client_api.support import support_bp
from blueprints.client_api.system import system_bp

from libs.exceptions import *

import os

client_bp = Blueprint('client_bp', __name__)
api = Blueprint('api', __name__)

api.register_blueprint(auth_bp, url_prefix='/auth')
api.register_blueprint(my_products_bp, url_prefix='/my-products')
api.register_blueprint(products_bp, url_prefix='/products')
api.register_blueprint(profile_bp, url_prefix='/profile')
api.register_blueprint(recharges_bp, url_prefix='/recharges')
api.register_blueprint(seller_bp, url_prefix='/seller')
api.register_blueprint(support_bp, url_prefix='/support')
api.register_blueprint(system_bp, url_prefix='/system')

client_bp.register_blueprint(api, url_prefix='/api')

@client_bp.route('/', defaults={"path":""})
@client_bp.route('/<path:path>')
def index(path):
    return send_from_directory(os.path.join(os.getcwd(), "templates", "client"), "index.html")