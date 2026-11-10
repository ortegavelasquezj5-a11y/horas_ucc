"""Reporte en Excel del seguimiento de horas (HU-11). Usa los mismos filtros de la pantalla."""
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from horas import services
from usuarios.permisos import SeguimientoMixin

from .views import programa_elegido

AZUL = "003865"
COLORES_ESTADO = {"cumple": "E3F2E8", "en-progreso": "FFF4E5", "en-riesgo": "FDECEC"}
COLUMNAS = [("Código", 14), ("Estudiante", 34), ("Programa", 26), ("Semestre", 13),
            ("Horas aprobadas", 20), ("Meta", 10), ("Faltan", 11), ("Avance %", 13), ("Estado", 16)]


class ExportarExcelView(SeguimientoMixin, View):
    def get(self, request):
        programa, _ = programa_elegido(request)
        semestre = request.GET.get("semestre", "")
        estado = request.GET.get("estado", "")
        filas = services.seguimiento(programa=programa, semestre=int(semestre) if semestre.isdigit() else None)
        if estado in services.ESTADOS_CUMPLIMIENTO:
            filas = [f for f in filas if f["estado"] == estado]

        libro = Workbook()
        hoja = libro.active
        hoja.title = "Seguimiento"
        ultima = get_column_letter(len(COLUMNAS))

        # Encabezado del reporte
        hoja.merge_cells(f"A1:{ultima}1")
        hoja["A1"] = "Reporte de seguimiento de horas de bienestar"
        hoja["A1"].font = Font(bold=True, size=14, color=AZUL)
        filtros = [
            f"Programa: {programa.nombre if programa else 'Todos'}",
            f"Semestre: {semestre + '.º' if semestre else 'Todos'}",
            f"Estado: {services.ESTADOS_CUMPLIMIENTO.get(estado, 'Todos')}",
            f"Generado: {timezone.localtime().strftime('%d/%m/%Y %H:%M')} por {request.user.nombre_completo}",
        ]
        hoja.merge_cells(f"A2:{ultima}2")
        hoja["A2"] = " · ".join(filtros)
        hoja["A2"].font = Font(italic=True, color="5A6675")

        # Tabla
        borde = Border(bottom=Side(style="thin", color="DDE3EA"))
        for col, (titulo, ancho) in enumerate(COLUMNAS, start=1):
            celda = hoja.cell(row=4, column=col, value=titulo)
            celda.font = Font(bold=True, color="FFFFFF")
            celda.fill = PatternFill("solid", fgColor=AZUL)
            celda.alignment = Alignment(horizontal="center", vertical="center")
            hoja.column_dimensions[get_column_letter(col)].width = ancho

        fila = 5
        for f in filas:
            e = f["estudiante"]
            faltan = max(f["meta"] - f["horas"], 0)
            valores = [e.codigo, e.nombre_completo, e.programa.nombre if e.programa else "", e.semestre,
                       float(f["horas"]), f["meta"], float(faltan), f["porcentaje"] / 100, f["estado_texto"]]
            for col, valor in enumerate(valores, start=1):
                celda = hoja.cell(row=fila, column=col, value=valor)
                celda.border = borde
            hoja.cell(row=fila, column=8).number_format = "0%"
            hoja.cell(row=fila, column=9).fill = PatternFill("solid", fgColor=COLORES_ESTADO[f["estado"]])
            fila += 1

        # Totales
        if filas:
            promedio = round(sum(float(f["horas"]) for f in filas) / len(filas), 1)
            totales = [("Total estudiantes", len(filas)), ("Promedio de horas aprobadas", promedio)]
            totales += [(f"Estudiantes: {texto}", sum(1 for f in filas if f["estado"] == clave))
                        for clave, texto in services.ESTADOS_CUMPLIMIENTO.items()]
            for i, (texto, valor) in enumerate(totales, start=1):
                hoja.cell(row=fila + i, column=2, value=texto).font = Font(bold=True)
                hoja.cell(row=fila + i, column=5, value=valor)
        else:
            hoja.cell(row=5, column=1, value="No hay estudiantes con esos filtros.")

        hoja.freeze_panes = "A5"
        hoja.page_setup.orientation = "landscape"
        hoja.page_setup.fitToWidth = 1
        hoja.page_setup.fitToHeight = 0
        hoja.sheet_properties.pageSetUpPr.fitToPage = True
        hoja.auto_filter.ref = f"A4:{ultima}{max(fila - 1, 4)}"

        nombre = f"seguimiento_horas_{timezone.localdate():%Y%m%d}.xlsx"
        respuesta = HttpResponse(content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        respuesta["Content-Disposition"] = f'attachment; filename="{nombre}"'
        libro.save(respuesta)
        return respuesta