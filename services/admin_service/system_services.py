from flask import Response
from libs.models import Category, ProductCategories, Platform, ProductsByRequest, Coupon, UserProducts, CompleteAccountRequest, PagoMovilRequest, RechargeRequest, DocumentRequest, GoogleDriveProduct, PlatinumMembers, db
from libs.schemas import CouponSchema, GoogleDriveProductSchema
from services.general_service import save_file, delete_file
from openpyxl import Workbook
import io

def update_product_category(category:Category, form):
    products_category = [ p for p, *_ in (
        db.session.query(
            db.func.concat(ProductCategories.product_id, "_", ProductCategories.product_type)
        )
        .filter(ProductCategories.category_id==category.id)
    )]
    new_set = []
    watch_delete = []
    delete = []
    for name, value in form.items():
        if not name.startswith("product_check"):
            continue
        if value not in products_category:
            product_id, product_type = value.split("_")
            new_set.append(ProductCategories(category_id=category.id, product_id=product_id, product_type=product_type))
        watch_delete.append(value)

    if len(new_set):
        db.session.add_all(new_set)

    type_platform = []
    type_products = []
    for pc in products_category:
        if pc not in watch_delete:
            product_id, product_type = pc.split("_")
            if product_type == "platform":
                type_platform.append(product_id)
            if product_type == "product":
                type_products.append(product_id)
    filter_category_id=ProductCategories.category_id == category.id
    platforms_query = (
        ProductCategories.query
        .filter(filter_category_id)
        .filter(ProductCategories.product_id.in_(type_platform))
        .filter(ProductCategories.product_type == "platform")
    )
    products_query = (
        ProductCategories.query
        .filter(filter_category_id)
        .filter(ProductCategories.product_id.in_(type_products))
        .filter(ProductCategories.product_type == "product")
    )
    
    for pc in platforms_query.union(products_query):
        db.session.delete(pc)
    db.session.commit()
    return "Se ha actualizado correctamente esta categoría"

resouce = {
    "screen":"Pantallas de una plataforma",
    "all_screen":"Todas las pantallas",
    "complete_account_request":"Cuentas completas de una plataforma",
    "all_complete":"Todas las cuentas completas",
    "platform":"Todas lo que sea parte de plataformas",
    "product_by_request":"Un producto dínamico",
    "product":"Todos los productos dínamicos",
    # "category":"Todos los productos en esta categoría",
    # "all":"TODO",
}

is_platform = Coupon.resource.in_(["screen", "complete_account_request", "all_screen", "all_complete", "platform"])
is_product = Coupon.resource.in_(["product_by_request", "product"])
is_category = Coupon.resource == "category"

def get_coupons(coupon_schema):
    type = db.func.if_(
        is_category,
        db.text("'Todos los productos en esta categoría'"),
        db.text("'Todo'")
    ).label("type")
    for resource, text in resouce.items():
        type = db.func.if_(
            Coupon.resource == resource,
            db.text(f"'{text}'"),
            type
        )
    title = db.func.if_(
        is_platform,
        db.session.query(Platform.name).filter(Platform.id == Coupon.resource_id).scalar_subquery(),
        db.func.if_(
            is_product,
            db.session.query(ProductsByRequest.title).filter(ProductsByRequest.id == Coupon.resource_id).scalar_subquery(),
            db.func.if_(
                is_category,
                db.session.query(Category.name).filter(Category.id == Coupon.resource_id).scalar_subquery(),
                db.text("'Todo'")
            )
        )
    ).label("title")
    query = (
        db.session.query(Coupon, type, title)
    )
    return [ {**coupon_schema.dump(coupon), "type":type, "title":title, } for coupon, type, title in query]

def get_notifications():
    query = (
        db.session.query(
            db.session.query(db.func.count(UserProducts.id)).filter(UserProducts.status == 0).label("products"),
            db.session.query(db.func.count(CompleteAccountRequest.id)).filter(CompleteAccountRequest.status == 0).label("complete"),
            db.session.query(db.func.count(PagoMovilRequest.id)).filter(PagoMovilRequest.status == 0).label("pago_movil"),
            db.session.query(db.func.count(RechargeRequest.id)).filter(RechargeRequest.status == "no verificado").label("recharges"),
            db.session.query(db.func.count(DocumentRequest.id)).filter(DocumentRequest.status == 0).label("documents"),
            db.session.query(db.func.count(PlatinumMembers.id)).filter(PlatinumMembers.status == 0).label("platinum_members"),
        ).first()
    )
    return query

def create_google_drive_product(form, file):
    title = form.get("title")
    file_path = save_file(file)
    url_redirect = form.get("url_redirect")
    product_type = form.get("product_type")

    return GoogleDriveProduct(
        title=title,
        file_path=file_path,
        url_redirect=url_redirect,
        product_type=product_type,
    )

def edit_google_drive_product(product:GoogleDriveProduct, form, file):
    schema = GoogleDriveProductSchema(exclude=["id", "file_path"])
    file_path = product.file_path
    if file:
        delete_file(product.file_path)
        file_path = save_file(file)

    data = {
        "title": form.get("title") or product.title,
        "url_redirect": form.get("url_redirect") or product.url_redirect,
        "product_type": form.get("product_type") or product.product_type,
        "file_path": file_path
    }
    schema.load(data, instance=product, partial=True)

def create_lottery_tickets_to_xlsx(query):
    
    # Crear un archivo Excel
    workbook = Workbook()
    sheet = workbook.active
    # sheet['A1'] = 'Nombre'
    # sheet['B1'] = 'Email'

    row = 1
    for lottery in query:
        for i in range(lottery.amount):
            # sheet[f'A{row}'] = lottery.user.username
            sheet[f'A{row}'] = lottery.user.email
            row += 1
    # for idx, lottery in enumerate(query, start=2):
    #     sheet[f'A{idx}'] = lottery.user.username
    #     sheet[f'B{idx}'] = lottery.user.email

    # Guardar el libro en un objeto BytesIO
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    # Crear una respuesta Flask con el archivo adjunto
    response = Response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=tickets.xlsx'
    return response