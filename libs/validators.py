from marshmallow import validate
from services.money_change_service import MONEY_TYPES

is_valid_email = validate.Email(error="Este email no es valido")
is_valid_phone = validate.Regexp(
    r"[\d]{6,}$",
    error="El telefono debe contener unicamente numeros sin signos")


def range(value, min=None, max=None, equal=None):
    message = f"La longitud debe ser {f'mínimo {min}, 'if min!=None else''}{f'maximo {max}, 'if max!=None else''}"
    return validate.Length(min=min, max=max, equal=equal, error=message)(value)

is_valid_money_type = validate.OneOf(MONEY_TYPES)