from flask import Flask
from dotenv import load_dotenv
import pytz
import os
import datetime

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
ENV = os.getenv("MYSQL_HOST")
MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")
MYSQL_DB = os.getenv("MYSQL_DB")
CORS_ORIGINS = '*'
MAIL_SERVER=os.getenv("MAIL_SERVER")
MAIL_PORT=os.getenv("MAIL_PORT")
MAIL_USE_TLS=False
MAIL_USE_SSL=True
MAIL_USERNAME=os.getenv("MAIL_USERNAME")
MAIL_DEFAULT_SENDER =os.getenv("MAIL_USERNAME")
MAIL_PASSWORD=os.getenv("MAIL_PASSWORD")

def create_app():
    # ENVIRONMENT
    app = Flask(__name__, static_folder='static', )
    app.config.update(**{
        "SECRET_KEY": SECRET_KEY,
        "JWT_SECRET_KEY": JWT_SECRET_KEY,
        "JWT_ACCESS_TOKEN_EXPIRES": False,
        "CORS_ORIGINS": CORS_ORIGINS,
        "TEMPLATES_PATH": "../templates/",
        "TZ_INFO": pytz.timezone('America/Caracas'),
        "SQLALCHEMY_TRACK_MODIFICATIONS": False,
        "SQLALCHEMY_DATABASE_URI": f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}/{MYSQL_DB}",
        "MAIL_SERVER":MAIL_SERVER,
        "MAIL_PORT":MAIL_PORT,
        "MAIL_USE_TLS":MAIL_USE_TLS,
        "MAIL_USE_SSL":MAIL_USE_SSL,
        "MAIL_USERNAME":MAIL_USERNAME,
        "MAIL_PASSWORD":MAIL_PASSWORD,
        "MAIL_DEFAULT_SENDER":MAIL_DEFAULT_SENDER,
    })
    return app
