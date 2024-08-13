from flask import Blueprint, request

from libs.models import Prize, PrizeHistory, User, dateV, db, Config
from libs.schemas import PrizeSchema, PrizeHistorySchema, UserSchema
from services.general_service import save_file, notify_user

prize_bp = Blueprint('prize_bp', __name__)

@prize_bp.route("/", methods=["GET", "POST"])
def index():
    prizeSchema = PrizeSchema(many=True)

    if request.method == "POST":
        img_url = save_file(request.files["photo"], request.form["title"].lower().replace("-", "_").replace(" ", "_"))
        newPrize = Prize(
            title=request.form["title"],
            description=request.form["description"],
            img_url=img_url,
            points=request.form["points"],
            public=True,
        )
        db.session.add(newPrize)
        db.session.commit()
        return PrizeSchema().dump(newPrize)

    return prizeSchema.dump(Prize.query.all())

@prize_bp.route("/<prize_id>/", methods=["GET", "PUT"])
def prize(prize_id):
    prize = Prize.query.get(prize_id)
    prizeSchema = PrizeSchema()

    if request.method == "PUT":
        pass
        title = request.form.get("title")
        description = request.form.get("description")
        points = request.form.get("points")
        public = request.form.get("public") == "1"
        photo = request.files.get("photo")

        newData = dict()
        if title:
            newData["title"] = title
        if description:
            newData["description"] = description
        if points:
            newData["points"] = points
        if public:
            newData["public"] = public
        if photo:
            photo_name
            newData["img_url"] = save_file(photo, title.lower().replace("-", "_").replace(" ", "_"))

        prizeSchema.load(newData, instance=prize, partial=True)
        db.session.add(prize)
        db.session.commit()
    if request.method == "DELETE":
        db.session.delete(prize)
        db.session.commit()
        
    return prizeSchema.dump(prize)

@prize_bp.route("/history/", methods=["GET"])
def history():
    base_query = db.session.query(PrizeHistory, Prize, User).join(PrizeHistory.user).join(PrizeHistory.prize)
    return {
        "request":[transform_history(prize_history, prize, user) for prize_history, prize, user in base_query.filter(PrizeHistory.status == 0)],
        "accept":[transform_history(prize_history, prize, user) for prize_history, prize, user in base_query.filter(PrizeHistory.status == 1)],
        "reject":[transform_history(prize_history, prize, user) for prize_history, prize, user in base_query.filter(PrizeHistory.status == 2)],
    }

@prize_bp.route("/history/<history_id>/", methods=["GET", "PUT"])
def history_edit(history_id):
    history = PrizeHistory.query.get(history_id)
    if not history:
        return {"error": "Not found"}, 404
    
    if request.method == "PUT":
        try:
            if 1 != request.json["status"] != 2:
                return {"error": "Invalid status"}, 400

            history.status = request.json["status"]
            if history.status == 2:
                history.user.prize_wallet.points += history.points
                db.session.add(history.user.prize_wallet)
            db.session.add(history)
            db.session.commit()
            
            notify_user(User.query.get(history.user_id), dateV.date_today(), "Su lista de premios ha sido actualizada, por favor verifique")
            return {
                "status":True,
                "msg":"Pedido procesado",
                "prize_history":PrizeHistorySchema().dump(history)
            }
        except Exception as e:
            return {
                "status":False,
                "msg":f"Error al procesar {str(e)}",
                "prize_history":PrizeHistorySchema().dump(history)
            }
            
    return PrizeHistorySchema().dump(history)

@prize_bp.route("/<prize_id>/history/", methods=["GET", "PUT"])
def prize_history(prize_id):
    prize = Prize.query.get(prize_id)
    prizeSchema = PrizeSchema()

    if request.method == "PUT":
        prizeSchema.load(request.json, instance=prize, partial=True)
        db.session.add(prize)
        db.session.commit()
        
    return prizeSchema.dump(prize)

@prize_bp.route("/points/", methods=["GET", "PUT"])
def points_():
    points = Config.get_points()
    if request.method == "PUT":
        try:
            points.options = request.json
            db.session.commit()
            return {"status":True, "msg":"Puntos actualizados"}, 200
        except Exception as e:
            return {"status":False, "msg":f"Error al actualizar puntos {str(e)}"}
    return points.options

    
def transform_history(prize_history, prize, user):
    return {
        **PrizeHistorySchema().dump(prize_history),
        "prize":PrizeSchema().dump(prize),
        "user":UserSchema().dump(user),
    }
