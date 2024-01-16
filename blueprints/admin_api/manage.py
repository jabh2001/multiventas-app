from flask import Blueprint, request
from flask_jwt_extended import jwt_required, current_user

manage_bp = Blueprint('manage_bp', __name__)