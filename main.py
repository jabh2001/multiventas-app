from flask import g, redirect
from flask_cors import CORS
from flask_mail import Message
from libs.models import init_DB, dateV
from libs.schemas import init_schemas
from libs.mail import init_mail
from libs.jwt import create_jwt
from libs.exceptions import register_handle_error
from __init__ import create_app

from blueprints.client import client_bp
from blueprints.admin import admin_bp
from blueprints.assets import assets

# APP
app = create_app()
with app.app_context():
    db = init_DB(app)
    ma = init_schemas(app)
    CORS(app)
    jwt = create_jwt(app)
    mail = init_mail(app)

    app.register_blueprint(client_bp, url_prefix='/client')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(assets, url_prefix='/assets')
    register_handle_error(app)


@app.before_request
def app_before_request():
    from flask import request
    g.TZ_INFO = app.config["TZ_INFO"]
    g.today = dateV.date_today()
    g.now = dateV.datetime_now()

    valid = False
    url = request.path[1:].lower()
    valid_start = ["api", "static", "assets"]
    for end_point in valid_start:
        if url.startswith(end_point):
            valid = True
            break
@app.route("/")
def env():
    return redirect("/client")

try:
    if __name__ == '__main__':
        app.run(port=6000, host="0.0.0.0")
except Exception as e:
    input(e)
