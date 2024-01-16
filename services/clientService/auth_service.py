from libs.models import User, GoogleData, db


def verify_user(email, password = None, google_id = None, withgoogle = False):
    if withgoogle:
        # user = User.query.filter(GoogleData.email == email).join(User.google_data).first()
        result = db.session.query(User, GoogleData).filter(GoogleData.email == email).join(User.google_data).first()
        if not result:
            raise Exception("Esta cuenta de google no esta ligada a ninguna cuanta de multiventas")
        user, google_data =result
        return user if (user and google_data.google_id == google_id) else None
    else:
        user = User.query.filter(User.email == email).first()
        return user if (user and user.password == password) else None
