from flask import Blueprint, request, render_template, jsonify, g
from flask_jwt_extended import jwt_required, current_user, create_access_token, set_access_cookies, unset_jwt_cookies
from flask_mail import Message
from marshmallow import ValidationError
from libs.models import User, Wallet, Notifications, DocumentRequest, EmailCode, GoogleData, db, dateV, PrizeWallet
from libs.schemas import UserSchema, WalletSchema, NotificationsSchema
from libs.mail import mail
from services.responsesService import ErrorResponse, SuccessResponse
from services.clientService.auth_service import verify_user
from services.clientService.profile_service import dict_of_user_data
from services.general_service import save_document, generate_standar_code

auth_bp = Blueprint('auth_bp', __name__)


@auth_bp.post('/signin/')
def signin():
    try:
        email = request.json.get("email", None)
        password = request.json.get("password", None)
        google_id = request.json.get("google_id", None)
        user = verify_user(email, password, google_id, withgoogle = "withgoogle" in request.args)
        if not user:
            return {"msg": "Correo o contraseña invalida"}, 401
        if not user.wallet:
            user.wallet = Wallet()
            db.session.add(user.wallet)
        if not user.prize_wallet:
            user.prize_wallet = PrizeWallet()
            db.session.add(user.prize_wallet)
        db.session.commit()
        user_schema = UserSchema(exclude=("password", "parent_id"))
        return user_schema.dump(user)
    except Exception as e:
        return {"msg": str(e)}, 400
@auth_bp.post('/sign-out/')
def sign_out():
    try:
        response = jsonify({"msg": "logout successful"})
        unset_jwt_cookies(response)
        return response
    except Exception as e:
        return {"msg": str(e)}, 400

@auth_bp.post('/v2/sign-in/')
def v2_sign_in():
    try:
        email = request.json.get("email", None)
        password = request.json.get("password", None)
        google_id = request.json.get("google_id", None)
        user = verify_user(email, password, google_id, withgoogle = "withgoogle" in request.args)
        if not user:
            return {"msg": "Correo o contraseña invalida"}, 401

        response = jsonify(dict_of_user_data(user))

        token = create_access_token(user)
        set_access_cookies(response, token,)
        return response
    except Exception as e:
        raise e
        return {"msg": str(e)}, 400

@auth_bp.post('/signup/')
def signup():
    try:
        user_schema = UserSchema()
        username = request.json.get("name", None)
        email = request.json.get("email", None)
        password = request.json.get("password", None)
        phone = request.json.get("phone", None)
        parent_id = request.json.get("parent_id", None)
        confirm_email_code = request.json.get("confirm_email_code", None)
        data = {
            "username": username,
            "email": email,
            "password": password,
            "phone": phone[1:] if phone else None,
            "user_type": "client"
        }
        if parent_id:
            data["parent_id"] = parent_id

        saved_google_data = None
        if "withgoogle" in request.args:
            data["password"] = request.json["googleId"]
            other_google_data = GoogleData.query.filter(GoogleData.email == request.json["email"]).first()
            if other_google_data:
                raise Exception("Ese cuanta de google ya se encuentra registrada")

            saved_google_data = GoogleData(
                email=request.json["email"],
                image_url=request.json["imageUrl"],
                google_id=request.json["googleId"],
                is_google_register=True,
            )
        # else:
        #     email_code_instance = EmailCode.query.filter(EmailCode.email==email).first()
        #     if not email_code_instance:
        #         raise Exception("El código de confirmación es incorrecto")
        #     email_code_instance.verify_validation(code=confirm_email_code, now=g.now)
        
        user = user_schema.load(data)
        user.is_valid_email = True
        user.save_me()

        wallet = Wallet(user_id=user.id)
        if saved_google_data:
            saved_google_data.user = user
            db.session.add(saved_google_data)

        wallet.save_me()

        return {
            "status":True,
            "user": user_schema.dump(user)
        }
    except ValidationError as ve:
        error_msg = []
        for field, errors in ve.messages.items():
            field_name = fields_names[field]
            for e in errors:
                error_msg.append(f"{field_name} - {e}")
        return ErrorResponse(400, "Datos invalidos", errors = error_msg)
    except Exception as e:
        return ErrorResponse("Ha ocurrido un error: " + str(e), error=str(e), errors=[str(e)])

@auth_bp.post('/v2/sign-up/')
def sign_up_v2():
    try:
        user_schema = UserSchema()
        username = request.json.get("name", None)
        email = request.json.get("email", None)
        password = request.json.get("password", None)
        phone = request.json.get("phone", None)
        parent_id = request.json.get("parent_id", None)
        confirm_email_code = request.json.get("confirm_email_code", None)
        data = {
            "username": username,
            "email": email,
            "password": password,
            "phone": phone[1:] if phone else None,
            "user_type": "client"
        }
        if parent_id:
            data["parent_id"] = parent_id

        saved_google_data = None
        if "withgoogle" in request.args:
            data["password"] = request.json["googleId"]
            other_google_data = GoogleData.query.filter(GoogleData.email == request.json["email"]).first()
            if other_google_data:
                raise Exception("Ese cuenta de google ya se encuentra registrada")

            saved_google_data = GoogleData(
                email=request.json["email"],
                image_url=request.json["imageUrl"],
                google_id=request.json["googleId"],
                is_google_register=True,
            )
        # else:
        #     email_code_instance = EmailCode.query.filter(EmailCode.email==email).first()
        #     if not email_code_instance:
        #         raise Exception("El código de confirmación es incorrecto")
        #     email_code_instance.verify_validation(code=confirm_email_code, now=g.now)
        
        user = user_schema.load(data)
        user.is_valid_email = True
        user.save_me()

        wallet = Wallet(user_id=user.id)
        if saved_google_data:
            saved_google_data.user = user
            db.session.add(saved_google_data)

        wallet.save_me()

        response = jsonify({**dict_of_user_data(user), "status":True })

        token = create_access_token(user)
        set_access_cookies(response, token,)
        return response
    except ValidationError as ve:
        error_msg = []
        for field, errors in ve.messages.items():
            field_name = fields_names[field]
            for e in errors:
                error_msg.append(f"{field_name} - {e}")
        return ErrorResponse(400, "Datos invalidos", errors = error_msg)
    except Exception as e:
        return ErrorResponse("Ha ocurrido un error: " + str(e), error=str(e), errors=[str(e)])

@auth_bp.post('/confirm-email/')
def confirm_email():
    try:
        user_schema = UserSchema()
        user = User.query.filter(User.email == request.json.get("email", None)).first() 
        if not user:
            raise Exception("Problema al encontrar el usuario")
        confirm_email_code = request.json.get("confirm_email_code", None)

        email_code_instance = EmailCode.query.filter(EmailCode.email==user.email).first()
        if not email_code_instance:
            raise Exception("El código de confirmación es incorrecto")
        email_code_instance.verify_validation(code=confirm_email_code, now=g.now)
        
        user.is_valid_email = True
        user.save_me()

        return {
            "status":True,
            "user": user_schema.dump(user)
        }
    except Exception as e:
        return ErrorResponse("Ha ocurrido un error: " + str(e), error=str(e), errors=[str(e)])

@auth_bp.post('/email-code/')
def email_code():
    try:
        email = request.json.get("email", None)
        if not "existing_user" in request.args:
            a_user = User.query.filter(User.email == email).first()
            if a_user:
                raise Exception("Ya existe un usuario con ese correo registrado")

        generated_email_code = generate_standar_code(6)
        
        # Verificamos si el codigo de verificacion ya esta en la base de datos para evitar duplicados
        instance = EmailCode.query.filter(EmailCode.email==email).first()
        if instance:
            instance.code = generated_email_code
            instance.generated_date = dateV.datetime_now()
        else:
            instance = EmailCode(email=email, code=generated_email_code, generated_date = dateV.datetime_now())
            db.session.add(instance)
        db.session.commit()
        
    
        msg = Message("Confirmation code", recipients=[email])
        msg.html = render_template("mail_format.html", code = generated_email_code, email = email)
        mail.send(msg)
        
        return {
            "status":True,
            "message":"Se ha enviado el codigo de confirmacion al correo electronico",
        }
    except Exception as e:
        return ErrorResponse("Ha ocurrido un error: " + str(e), error=str(e), errors=[str(e)])

@auth_bp.post('/linked-google/')
def linked_google():
    try:
        user_schema = UserSchema()

        user_email = request.json.get("user_email", None)
        google_email = request.json.get("google_email", None)

        user = User.query.filter(User.email == user_email).first()
        if not user:
            raise Exception("Problema al encontrar el usuario")

        other_google_data = GoogleData.query.filter(GoogleData.email == google_email).first()
        if other_google_data:
            raise Exception("Esa cuenta de google ya esta ligada a otra cuenta")


        saved_google_data = GoogleData(
            email=google_email,
            image_url=request.json["image_url"],
            google_id=request.json["google_id"],
            is_google_register=False,
            user=user
        )
        
        if user_email == google_email:
            user.is_valid_email = True
        db.session.add(saved_google_data)
        db.session.commit()

        return {
            "status":True,
            "user": user_schema.dump(user)
        }
    except Exception as e:
        return ErrorResponse("Ha ocurrido un error: " + str(e), error=str(e), errors=[str(e)])

fields_names = {
    "username":"Nombre de usuario",
    "email":"Correo",
    "password":"Contraseña",
    "phone":"Teléfono",
}

@auth_bp.route("/wallet/", methods=["GET"])
@jwt_required()
def get_wallet():
    wallet_schema = WalletSchema(exclude=["id"])
    notifications, *_ = db.session.query(db.func.count(Notifications.id))\
        .filter(Notifications.user_id == current_user.id)\
        .filter(Notifications.showed == 0)\
        .first()

    return {
        "notifications": notifications,
        "wallet": wallet_schema.dump(current_user.wallet)
    }, 200

@auth_bp.route("/document/", methods=["POST"])
@jwt_required()
def document():
    try:
        if current_user.ci:
            raise Exception("Ya el usuario tiene un documento registrado")
        if not "document_file" in request.files:
            raise Exception("Debes incluir el documento")
        document_file = request.files["document_file"]
        filename = save_document(document_file, current_user)
        document_instance = DocumentRequest(user = current_user,file_name = filename)
        db.session.add(document_instance)
        db.session.commit()
        return {
            "msg":"Se ha enviado el documento, espera la respuesta - " + filename
        }
    except Exception as e:
        return {
            "msg":str(e)
        }

@auth_bp.route("/change-data-code/", methods=["POST"])
@jwt_required()
def change_data_code():
    try:
        email = None
        if current_user.is_valid_email:
            email = current_user.email
        elif current_user.google_data:
            email = current_user.google_data.email
        else:
            raise Exception("Debes tener un email valido para esto")

        generated_email_code = generate_standar_code(6)
        
        # Verificamos si el codigo de verificacion ya esta en la base de datos para evitar duplicados
        send_email = True
        instance = EmailCode.query.filter(EmailCode.email==email).first()
        if instance and not instance.is_valid_time(g.now):
            instance.code = generated_email_code
            instance.generated_date = dateV.datetime_now()
        elif not instance:
            instance = EmailCode(email=email, code=generated_email_code, generated_date = dateV.datetime_now())
            db.session.add(instance)
        else:
            send_email = False
        db.session.commit()

        if send_email:
            msg = Message("Confirmation code", recipients=[email])
            msg.html = render_template("change_data_format.html", code = generated_email_code, username = current_user.username)
            mail.send(msg)
        return {
            "status":True,
        }
    except Exception as e:
        return ErrorResponse("Ha ocurrido un error: " + str(e), error=str(e), errors=[str(e)])

@auth_bp.route("/change-data/", methods=["POST"])
@jwt_required()
def change_data():
    try:
        user_schema = UserSchema()

        confirm_email_code = request.json.get("confirm_email_code", None)
        data = request.json.get("data", None)
        data_changed = request.json.get("data_changed", None)
        if not all([confirm_email_code, data, data_changed]):
            raise ValueError("Faltan parametros")

        email = None
        if current_user.is_valid_email:
            email = current_user.email
        elif current_user.google_data:
            email = current_user.google_data.email
        else:
            raise Exception("Debes tener un email valido para esto")

        email_code_instance = EmailCode.query.filter(EmailCode.email==email).first()
        if not email_code_instance:
            raise Exception("El código de confirmación es incorrecto")
        email_code_instance.verify_validation(code=confirm_email_code, now=g.now)

        if data == "password":
            current_user.password = data_changed
        elif data == "phone":
            current_user.phone = data_changed[1:]
        db.session.commit()

        return {
            "status":True,
            "msg":"la informacion se ha cambiado correctamente",
            "user": user_schema.dump(current_user)
        }
    except Exception as e:
        return ErrorResponse("Ha ocurrido un error: " + str(e), error=str(e), errors=[str(e)])