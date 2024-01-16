import secrets
import string

letters = string.ascii_letters
digits = string.digits

alphabet = letters + digits

def generate_password(pwd_length = 12):
    pwd = ''
    for i in range(pwd_length):
        pwd += ''.join(secrets.choice(alphabet))
    return pwd