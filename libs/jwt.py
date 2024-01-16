from flask_jwt_extended import JWTManager
from libs.models import User


def create_jwt(app):
    jwt = JWTManager(app)

    @jwt.user_identity_loader
    def user_identity_lookup(user):
        return user.id

    @jwt.user_lookup_loader
    def user_lookup_callback(_jwt_header, jwt_data) -> User:
        identity = jwt_data["sub"]

        return User.query.filter(User.id == identity).first()
    return jwt
