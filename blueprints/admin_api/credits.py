from flask import Blueprint, request

from libs.models import CreditsTitaniumPrice, CreditsVipPrice, db
from libs.schemas import UserSchema, CreditsTitaniumPriceSchema, CreditsVipPriceSchema
credits_bp = Blueprint('credits_bp', __name__)


def update_order(model, ids):
    for index, id in enumerate(ids):
        record = model.query.get(id)
        if record:
            record.order = index + 1
            db.session.commit()

@credits_bp.get('/')
def index():
    try:
        titaniumSchema = CreditsTitaniumPriceSchema(many=True)
        vipSchema = CreditsVipPriceSchema(many=True)
        return {
            "creditsTitaniumPrice":titaniumSchema.dump(CreditsTitaniumPrice.query.order_by(CreditsTitaniumPrice.order).all()),
            "creditsVipPrice":vipSchema.dump(CreditsVipPrice.query.order_by(CreditsVipPrice.order).all()),
        }
    except Exception as e:
        return {"msg": str(e)}, 400

@credits_bp.post('/order/')
def order():
    try:
        titaniumSchema = CreditsTitaniumPriceSchema(many=True)
        vipSchema = CreditsVipPriceSchema(many=True)

        titaniumOrder = request.json["creditsTitaniumPrice"]
        vipOrder = request.json["creditsVipPrice"]

        update_order(CreditsTitaniumPrice, titaniumOrder)
        update_order(CreditsVipPrice, vipOrder)
        
        return {
            "creditsTitaniumPrice":titaniumSchema.dump(CreditsTitaniumPrice.query.order_by(CreditsTitaniumPrice.order).all()),
            "creditsVipPrice":vipSchema.dump(CreditsVipPrice.query.order_by(CreditsVipPrice.order).all()),
        }
    except Exception as e:
        return {"msg": str(e)}, 400

@credits_bp.post('/titanium/')
def titanium():
    try:
        titaniumSchema = CreditsTitaniumPriceSchema()
        titaniumPrice = titaniumSchema.load(request.json)

        db.session.add(titaniumPrice)
        db.session.commit()

        return titaniumSchema.dump(titaniumPrice)
    except Exception as e:
        return {"msg": str(e)}, 400

@credits_bp.route("/titanium/<titanium_id>/", methods=["PUT", "DELETE"])
def editTitanium(titanium_id):
    if request.method == "PUT":
        try:
            titaniumSchema = CreditsTitaniumPriceSchema()
            titaniumPrice = CreditsTitaniumPrice.query.get(titanium_id)

            titaniumSchema.load(request.json, instance=titaniumPrice, partial=True)

            db.session.add(titaniumPrice)
            db.session.commit()

            return titaniumSchema.dump(titaniumPrice)
        except Exception as e:
            return {"msg": str(e)}, 400
    if request.method == "DELETE":
        try:
            titaniumSchema = CreditsTitaniumPriceSchema()
            titaniumPrice = CreditsTitaniumPrice.query.get(titanium_id)
            db.session.delete(titaniumPrice)
            db.session.commit()

            return titaniumSchema.dump(titaniumPrice)
        except Exception as e:
            return {"msg": str(e)}, 400

@credits_bp.post('/vip/')
def vip():
    try:
        vipSchema = CreditsVipPriceSchema()
        vipPrice = vipSchema.load(request.json)

        db.session.add(vipPrice)
        db.session.commit()

        return vipSchema.dump(vipPrice)
    except Exception as e:
        return {"msg": str(e)}, 400


@credits_bp.route("/vip/<vip_id>/", methods=["PUT", "DELETE"])
def editVip(vip_id):
    vipSchema = CreditsVipPriceSchema()
    vipPrice = CreditsVipPrice.query.get(vip_id)
    
    if request.method == "PUT":
        try:
            vipSchema.load(request.json, instance=vipPrice, partial=True)

            db.session.add(vipPrice)
            db.session.commit()

            return vipSchema.dump(vipPrice)
        except Exception as e:
            return {"msg": str(e)}, 400
    if request.method == "DELETE":
        try:
            db.session.delete(vipPrice)
            db.session.commit()

            return vipSchema.dump(vipPrice)
        except Exception as e:
            return {"msg": str(e)}, 400