from flask import jsonify


def ErrorResponse(status_code, error, errors=[]):
    return jsonify({"status": False, "error": error,
                   "errors": errors, "status_code": status_code})


def SuccessResponse(response):
    return jsonify({"status": True, **response})
