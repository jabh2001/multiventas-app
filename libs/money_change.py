import ssl
import requests
import urllib.request
from bs4 import BeautifulSoup
ssl._create_default_https_context = ssl._create_unverified_context
API_KEY = "kGI2xGgOHouIKwscWTpFEVnlF70IzDuI"


class MoneyChange:
    instance = None

    def __init__(self) -> None:
        from libs.models import ExchangeRate
        for row in ExchangeRate.query.all():
            money = row.money_type
            if money == "bs":
                self._bs = row.amount
            elif money == "mxn":
                self._mxn = row.amount
            elif money == "cop":
                self._cop = row.amount
            elif money == "sol":
                self._sol = row.amount

    @classmethod
    def getInstance(cls):
        if not cls.instance:
            cls.instance = cls()
            return cls.instance
        return cls.instance

    @classmethod
    def update(cls):
        from libs.models import ExchangeRate, db
        try:
            url = "https://api.apilayer.com/exchangerates_data/latest?symbols=COP%2CMXN%2CPEN&base=USD"
            payload = {}
            headers = {
                "apikey": "kGI2xGgOHouIKwscWTpFEVnlF70IzDuI"
            }
            response = requests.request(
                "GET", url, headers=headers, data=payload)
            data = response.json()
            rates = data["rates"]

            _bs_change_rate = cls.exchange_api_bs(None)
            _mxn_change_rate = round(rates["COP"], 2)
            _cop_change_rate = round(rates["MXN"], 2)
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
            db.session.add_all(all_rates)
            db.session.commit()
            return True
        except Exception as e:
            print(f"ERROR: {str(e)}".center(100, "-"))
            return False

    def change_to_usd(self, amount, from_country: str):
        ret = 0
        country = from_country.lower()

        if country == "ve":
            ret = amount / self.exchange_rate_bs()
        elif country == "mx":
            ret = amount / self.exchange_rate_mxn()
        elif country == "co":
            ret = amount / self.exchange_rate_cop()
        elif country == "pe":
            ret = amount / self.exchange_rate_sol()
        elif country == "us":
            ret = amount
        else:
            raise Exception("Este país de destino no esta soportado")
        return ret

    def change_from_usd(self, amount, to_money):
        ret = 0
        money = to_money.lower()

        if money == "bs":
            ret = amount * self.exchange_rate_bs()
        elif money == "mxn":
            ret = amount * self.exchange_rate_mxn()
        elif money == "cop":
            ret = amount * self.exchange_rate_cop()
        elif money == "sol":
            ret = amount * self.exchange_rate_sol()
        elif money == "usd":
            ret = amount
        else:
            raise Exception("Este país de destino no esta soportado")
        return ret

    def exchange_rate_bs(self):
        if not self._bs:
            from libs.models import ExchangeRate
            self._bs = ExchangeRate.query.filter(
                ExchangeRate.money_type == "bs").first().amount
        return self._bs

    def exchange_rate_mxn(self):
        if not self._mxn:
            from libs.models import ExchangeRate
            self._mxn = ExchangeRate.query.filter(
                ExchangeRate.money_type == "mxn").first().amount
        return self._mxn

    def exchange_rate_cop(self):
        if not self._cop:
            from libs.models import ExchangeRate
            self._cop = ExchangeRate.query.filter(
                ExchangeRate.money_type == "cop").first().amount
        return self._cop

    def exchange_rate_sol(self):
        if not self._sol:
            from libs.models import ExchangeRate
            self._sol = ExchangeRate.query.filter(
                ExchangeRate.money_type == "sol").first().amount
        return self._sol

    def exchange_api_bs(self):
        url = "https://www.bcv.org.ve"

        page = urllib.request.urlopen(url=url)
        soup = BeautifulSoup(page, "html.parser")

        element = soup.find(id="dolar").strong.text
        element = element.strip()
        element = element.replace(",", ".")
        return round(float(element), 2)

    def exchange_api(self, money_type):
        money_type = money_type.upper()
        url = f"https://api.apilayer.com/exchangerates_data/latest?symbols={money_type}&base=USD"
        payload = {}
        headers = {
            "apikey": "kGI2xGgOHouIKwscWTpFEVnlF70IzDuI"
        }
        response = requests.request("GET", url, headers=headers, data=payload)
        data = response.json()
        amount = data["rates"]["{money_type}"]
        return round(amount, 2)

    def __str__(self) -> str:
        return f'{self._bs=}\n{self._mxn=}\n{self._cop=}\n{self._sol=}'
