from flask import Blueprint, request
# from flask_jwt_extended import jwt_required, current_user
# from libs.models import User, Wallet, Notifications, db
from libs.schemas import UserSchema
from services.responsesService import ErrorResponse, SuccessResponse
from services.clientService.auth_service import verify_user

auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.post('/signin/')
def signin():
    try:
        email = request.json.get("email", None)
        password = request.json.get("password", None)
        user = verify_user(email, password)
        if not user:
            return {
                "status":False,
                "msg":"Correo o contraseña invalida"
            }
        user_schema = UserSchema(exclude=("password", "parent_id", "link", "main_money", ))
        if user.user_type != "admin":
            return {
                "status":False,
                "msg":"El usuario debe ser administrador"
            }
        return {
            "status":True,
            "user_data":user_schema.dump(user)
        }
    except Exception as e:
        return {"msg": str(e)}, 400
