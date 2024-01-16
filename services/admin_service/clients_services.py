from flask import Response
import io
from openpyxl import Workbook

def convert_clientlist_to_xlsx(query):
    
    # Crear un archivo Excel
    workbook = Workbook()
    sheet = workbook.active
    sheet['A1'] = 'ID'
    sheet['B1'] = 'Nombre'
    sheet['C1'] = 'telefono'

    for idx, usuario in enumerate(query, start=2):
        sheet[f'A{idx}'] = usuario.id
        sheet[f'B{idx}'] = usuario.username
        sheet[f'C{idx}'] = wsphone(usuario.phone)

    # Guardar el libro en un objeto BytesIO
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    # Crear una respuesta Flask con el archivo adjunto
    response = Response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=usuarios.xlsx'
    return response
def convert_client_list_with_buy_count_to_xlsx(query):
    
    # Crear un archivo Excel
    workbook = Workbook()
    sheet = workbook.active
    sheet['A1'] = 'ID'
    sheet['B1'] = 'Nombre'
    sheet['C1'] = 'telefono'
    sheet['D1'] = 'cantidad de compras'

    for idx, row in enumerate(query, start=2):
        usuario, count = row

        sheet[f'A{idx}'] = usuario.id
        sheet[f'B{idx}'] = usuario.username
        sheet[f'C{idx}'] = wsphone(usuario.phone)
        sheet[f'D{idx}'] = count

    # Guardar el libro en un objeto BytesIO
    output = io.BytesIO()
    workbook.save(output)
    output.seek(0)

    # Crear una respuesta Flask con el archivo adjunto
    response = Response(output.read())
    response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    response.headers['Content-Disposition'] = 'attachment; filename=usuarios.xlsx'
    return response

def wsphone(phone):
    try:
        import re

        if phone.startswith("+"):
            phone= phone[1:]
        if phone.startswith("0"): 
            phone= phone[1:]
        if phone[0] in ["1", "2", "3", "4", "5", "6", "7", "8", "9"]: 
            phone = f"58{phone}"
        return phone.replace("-", "").replace(".", "").replace(" ", "")
    except Exception as e:
        return str(e)