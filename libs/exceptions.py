from services.responsesService import ErrorResponse, SuccessResponse


class MultiventasError(Exception):
    status_code = 452
    description = "Un error no controlado de multiventas.vip"


class CustomMessageError(MultiventasError):
    status_code: 455

    def __init__(self, message: str) -> None:
        self.description = message


class NotAmountInWalletError(MultiventasError):
    status_code = 453
    description = "No tiene suficiente dinero para realizar la compra"

    def __init__(self, description=None):
        if description:
            self.description = description


class ProductNotFoundError(MultiventasError):
    status_code = 454
    description = "El producto al que intesta acceder no existe"


def register_handle_error(app):
    @app.errorhandler(MultiventasError)
    def multiventas_error_handler(e):
        return ErrorResponse(error=e.description, status_code=e.status_code)
