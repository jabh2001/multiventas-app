from flask import Blueprint, send_from_directory
from flask_jwt_extended import jwt_required, current_user
from services.general_service import doc_path
import os

# BLUEPRINTS
assets = Blueprint('assets_Bp', __name__)


@assets.route("/img/<filename>/")
def image_manager(filename):
    return send_from_directory(os.path.join(
        os.getcwd(), "static/img"), path=filename, as_attachment=False)


@assets.route("/support_img/<filename>/")
def sup_image_manager(filename):
    return send_from_directory(os.path.join(
        os.getcwd(), "assets/support_img"), path=filename, as_attachment=False)

@assets.route("/document/<filename>/")
@assets.route("/documents/<filename>/")
def doc_image_manager(filename):
    return send_from_directory(doc_path, path=filename, as_attachment=False)
