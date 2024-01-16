from libs.models import StreamingAccount, Platform, Notifications, User, Screen, ExpiredAccount, Afiliated, UserProducts, ProductsByRequest, ExchangeRate, db
from services.random_password import generate_password as gen_pws
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename
import os
import ssl
import requests
import urllib.request
import random
from bs4 import BeautifulSoup
ssl._create_default_https_context = ssl._create_unverified_context
API_KEY = "kGI2xGgOHouIKwscWTpFEVnlF70IzDuI"

img_path = os.path.join(os.getcwd(), "static", "img")
doc_path = os.path.join(os.getcwd(), "assets", "documents")

def notifify_users_of_accounts(account, content, today):
    notify = []
    notified = set()
    for screen in account.screens:
        client_id = screen.client_id
        if client_id and client_id not in notified:
            notify.append(Notifications(user_id=client_id, date=today, content=content, showed=0))
            notified.add(client_id)
    db.session.add_all(notify)
    db.session.commit()

def notify_user(user:User, today, content):
    notification = Notifications(user=user, date=today, content=content, showed=0)
    db.session.add(notification)
    db.session.commit()

# def notifyUsers(self, users, content):
#     notifications = []
#     for user in users:
#         notification = Notifications(user=user, date=dateV.date_today(), content=content, showed=0)
#         notifications.append(notification)
#     db.session.add_all(notifications)
#     db.session.commit()
#     pass

# def notifyAllUsers(self, content):
#     users = [user.id for user in User.query.all() if user.user_type in ["client", "seller"]]
#     notifications = []
#     for user in users:
#         notification = Notifications(user=user, date=dateV.date_today(), content=content, showed=0)
#         notifications.append(notification)
#     db.session.add_all(notifications)
#     db.session.commit()



def convert_str_to_int(num:str, default_number:int = 0):
    try:
        return int(num)
    except:
        return default_number



def save_file(file:FileStorage, filename=None) -> str:
    name, ext = file.filename.rsplit(".", 1)
    name = filename if filename else name

    filename = secure_filename(f"{name}.{ext}")
    path = os.path.join(img_path, filename)

    file.save(path)
    return filename

def delete_file(filename) -> bool:
    try:
        path = os.path.join(img_path, filename)
        os.remove(path)
        return True
    except Exception as e:
        return False

def save_document(document:FileStorage, user):
    name, ext = document.filename.rsplit(".", 1)
    name = f"{user.id}_{user.username.replace('.', '')}"

    filename = secure_filename(f"{name}.{ext}")
    path = os.path.join(doc_path, filename)

    document.save(path)
    return filename

def update_screens(today):
    screens = (
        db.session.query(Screen, User, StreamingAccount)
        .join(Screen.client)
        .join(Screen.account)
        .filter(Screen.client_id != None)
        .filter(Screen.end_date <= today)
        .all()
    )
    expired = []
    for screen, client, account in screens:
        if today >= screen.end_date:
            expired_account = ExpiredAccount(
                account = account,
                user = client,
                expired_date = today
            )
            screen.client = None
            expired.append(expired_account)
    db.session.add_all(expired)
    db.session.commit()

def update_afiliated(today):
    afiliateds = (
        Afiliated.query
        .filter(Afiliated.status == 1)
        .filter(Afiliated.end_date <= today)
        .all()
    )
    for afiliated in afiliateds:
        afiliated.status = 0
    db.session.commit()

def update_products(today):
    user_products = (
        db.session.query(UserProducts)
        .filter(UserProducts.status == 1)
        .filter(UserProducts.end_date.is_not(None))
        .filter(UserProducts.end_date <= today)
        .all()
    )
    for u in user_products:
        if today >= u.end_date:
            u.status = 3
    db.session.commit()

def exchange_api_bs():
    url = "https://www.bcv.org.ve"

    page = urllib.request.urlopen(url=url)
    soup = BeautifulSoup(page, "html.parser")

    element = soup.find(id="dolar").strong.text
    element = element.strip()
    element = element.replace(",", ".")
    return round( float(element), 2)

def update_exchange_rate(cls):
    try:
        url = "https://api.apilayer.com/exchangerates_data/latest?symbols=COP%2CMXN%2CPEN&base=USD"
        payload = {}
        headers= {
            "apikey": "kGI2xGgOHouIKwscWTpFEVnlF70IzDuI"
        }
        response = requests.request("GET", url, headers=headers, data = payload)
        data = response.json()
        rates = data["rates"]

        _bs_change_rate = exchange_api_bs()
        _mxn_change_rate = round(rates["MXN"], 2)
        _cop_change_rate = round(rates["COP"], 2)
        _sol_change_rate = round(rates["PEN"], 2)

        all_rates = ExchangeRate.query.all()
        for row in all_rates:
            money = row.money_type
            if money == "bs":
                row.amount = _bs_change_rate
            elif money == "mxn":
                row.amount = _mxn_change_rate
            elif money == "cop":
                row.amount = _cop_change_rate
            elif money == "sol":
                row.amount = _sol_change_rate
        db.session.commit()
        return True
    except Exception as e:
        print(f"ERROR: {str(e)}".center(100, "-"))
        return False

def wsphone(phone):
    try:
        import re
        return phone.replace("-", "").replace(".", "").replace(" ", "")
    except Exception as e:
        return str(e)

def generate_password(base, length):
    password = ""
    for i in range(length):
        random_number = int(random.randint(0, len(base)))
        password += base[random_number]
    return password

def generate_standar_code(code_length, contains_numbers=False, contains_symbols=False):
    length = int(code_length)

    base = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    numbers = "0123456789"
    symbols = ".?,;-_¡!¿*%&$/()[]{}|@><"

    if contains_numbers: base += numbers
    if contains_symbols: base += symbols

    return generate_password(base, length)
    

def create_affiliation_gift_code(all_gift_codes:list):
    all_codes = set([ inst.code for inst in all_gift_codes])
    code = ""
    while True:
        code = gen_pws(18)
        if not code in all_codes:
            break
    return code