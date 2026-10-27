"""Carga datos de demostración para probar el sistema con todos los roles.

Uso: python manage.py datos_demo
Se puede ejecutar varias veces: si los datos ya existen, no los duplica.
"""
from datetime import timedelta
from decimal import Decimal

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from actividades.models import Actividad, Inscripcion, TipoActividad
from horas.models import RegistroHoras
from notificaciones.models import Notificacion
from usuarios.models import Programa, Usuario

Rol = Usuario.Rol
CLAVE = "Horas2026*"
DOMINIO = "campusucc.edu.co"

PDF_EJEMPLO = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]/Contents 4 0 R"
    b"/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 66>>stream\nBT /F1 18 Tf 72 700 Td (Certificado de ejemplo - 2 horas) Tj ET\nendstream endobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)


class Command(BaseCommand):
    help = "Crea programas, usuarios de cada rol, actividades, inscripciones y horas de ejemplo."

    @transaction.atomic
    def handle(self, *args, **options):
        if Usuario.objects.filter(correo=f"admin@{DOMINIO}").exists():
            self.stdout.write("Los datos de demostración ya existen: no se crean de nuevo.")
            self._imprimir_usuarios()
            return

        ahora = timezone.now()
        hoy = timezone.localdate()

        # Programas y tipos -----------------------------------------------------
        sistemas = Programa.objects.create(nombre="Ingeniería de Sistemas", meta_horas=60)
        derecho = Programa.objects.create(nombre="Derecho", meta_horas=60)
        psicologia = Programa.objects.create(nombre="Psicología", meta_horas=50)
        Programa.objects.create(nombre="Contaduría Pública", meta_horas=50)
        tipos = {n: TipoActividad.objects.create(nombre=n)
                 for n in ("Académica", "Investigativa", "Cultural", "Deportiva", "Bienestar")}

        # Usuarios --------------------------------------------------------------
        def usuario(correo, codigo, nombres, apellidos, rol, programa=None, semestre=None, activo=True):
            return Usuario.objects.create_user(
                correo=f"{correo}@{DOMINIO}", password=CLAVE, codigo=codigo, nombres=nombres,
                apellidos=apellidos, rol=rol, programa=programa, semestre=semestre, is_active=activo,
                is_superuser=(rol == Rol.ADMIN),
            )

        usuario("admin", "A0001", "Diana", "Lora", Rol.ADMIN)
        bienestar = usuario("bienestar", "B2001", "Marcela", "Ruiz", Rol.BIENESTAR)
        usuario("coordinador.sistemas", "C3007", "Roberto", "Petro", Rol.COORDINADOR, sistemas)
        andrea = usuario("lider", "D1045", "Andrea", "Díaz", Rol.LIDER)
        carlos = usuario("carlos.perez", "D1102", "Carlos", "Pérez", Rol.LIDER)

        laura = usuario("laura.martinez", "U2026003", "Laura Sofía", "Martínez Vega", Rol.ESTUDIANTE, sistemas, 6)
        estudiantes = {
            "mateo": usuario("mateo.arrieta", "U2023014", "Mateo", "Arrieta Cogollo", Rol.ESTUDIANTE, sistemas, 10),
            "isabella": usuario("isabella.doria", "U2023027", "Isabella", "Doria Ramos", Rol.ESTUDIANTE, sistemas, 9),
            "mariana": usuario("mariana.negrete", "U2024008", "Mariana", "Negrete Paz", Rol.ESTUDIANTE, sistemas, 8),
            "sofia": usuario("sofia.montes", "U2025004", "Sofía", "Montes Ortiz", Rol.ESTUDIANTE, sistemas, 7),
            "sebastian": usuario("sebastian.morales", "U2026010", "Sebastián", "Morales Pineda", Rol.ESTUDIANTE, sistemas, 6),
            "valentina": usuario("valentina.hoyos", "U2026005", "Valentina", "Hoyos Petro", Rol.ESTUDIANTE, derecho, 5),
            "daniela": usuario("daniela.castro", "U2026007", "Daniela", "Castro Arrieta", Rol.ESTUDIANTE, psicologia, 4),
            "andres": usuario("andres.ramos", "U2026008", "Andrés Felipe", "Ramos Negrete", Rol.ESTUDIANTE, derecho, 3),
        }
        usuario("kevin.arrieta", "U2024031", "Kevin", "Arrieta Cogollo", Rol.ESTUDIANTE, derecho, 7, activo=False)

        # Actividades -----------------------------------------------------------
        def actividad(nombre, tipo, dias, horas, cupo, responsable, lugar, estado=Actividad.Estado.PUBLICADA, hora=8):
            inicio = (timezone.localtime(ahora) + timedelta(days=dias)).replace(
                hour=hora, minute=0, second=0, microsecond=0
            )
            return Actividad.objects.create(
                nombre=nombre, tipo=tipos[tipo], responsable=responsable, lugar=lugar,
                fecha_inicio=inicio, fecha_fin=inicio + timedelta(hours=3), cupo=cupo,
                horas_otorga=Decimal(horas), estado=estado,
            )

        F = Actividad.Estado.FINALIZADA
        ciencia = actividad("Semana de la ciencia", "Académica", -60, "8", 100, carlos, "Auditorio principal", F)
        danza = actividad("Muestra de danza folclórica", "Cultural", -40, "5", 40, carlos, "Teatro", F)
        voluntariado = actividad("Voluntariado banco de alimentos", "Bienestar", -15, "6", 30, bienestar, "Banco de alimentos", F)
        futbol = actividad("Torneo interno de fútbol sala", "Deportiva", -7, "4", 40, andrea, "Coliseo", F)
        caminata = actividad("Caminata ecológica", "Bienestar", -1, "3", 25, andrea, "Ronda del Sinú")
        ingenieria = actividad("Semana de la ingeniería: charlas y talleres", "Académica", 4, "8", 120, carlos, "Auditorio principal")
        voleibol = actividad("Torneo relámpago de voleibol", "Deportiva", 6, "4", 3, andrea, "Coliseo", hora=7)
        actividad("Club de lectura: autores del Caribe", "Cultural", 8, "2", 25, carlos, "Biblioteca, sala 2", hora=16)
        actividad("Semillero de investigación: IA aplicada", "Investigativa", 10, "6", 20, carlos, "Laboratorio de sistemas", hora=14)
        actividad("Taller de manejo del estrés", "Bienestar", 12, "2", 30, bienestar, "Sala de bienestar", hora=10)
        actividad("Torneo de baloncesto 3x3", "Deportiva", 18, "4", 36, andrea, "Coliseo", Actividad.Estado.BORRADOR)

        # Inscripciones con asistencia y sus horas --------------------------------
        def asistencia(act, est, asistio=True, estado_horas=RegistroHoras.Estado.APROBADA):
            insc = Inscripcion.objects.create(estudiante=est, actividad=act, asistio=asistio)
            if asistio:
                revisada = estado_horas != RegistroHoras.Estado.POR_APROBAR
                RegistroHoras.objects.create(
                    estudiante=est, inscripcion=insc, nombre_actividad=act.nombre, tipo=act.tipo,
                    fecha_actividad=timezone.localtime(act.fecha_inicio).date(), horas=act.horas_otorga,
                    estado=estado_horas, aprobador=bienestar if revisada else None,
                    fecha_revision=act.fecha_inicio + timedelta(days=2) if revisada else None,
                )
            return insc

        POR_APROBAR = RegistroHoras.Estado.POR_APROBAR
        for act in (ciencia, danza, voluntariado):
            asistencia(act, laura)
        asistencia(futbol, laura, estado_horas=POR_APROBAR)
        asistencia(ciencia, estudiantes["mateo"])
        asistencia(ciencia, estudiantes["isabella"])
        asistencia(danza, estudiantes["valentina"])
        asistencia(danza, estudiantes["sebastian"], asistio=False)
        asistencia(voluntariado, estudiantes["daniela"])
        asistencia(futbol, estudiantes["sebastian"], estado_horas=POR_APROBAR)
        asistencia(futbol, estudiantes["valentina"], estado_horas=POR_APROBAR)
        asistencia(futbol, estudiantes["andres"], asistio=False)

        # Caminata: ya pasó y falta registrar asistencia (para probar al líder)
        for est in (laura, estudiantes["sofia"], estudiantes["andres"], estudiantes["daniela"]):
            Inscripcion.objects.create(estudiante=est, actividad=caminata)
        # Futuras: inscripciones y un torneo con cupo lleno
        Inscripcion.objects.create(estudiante=laura, actividad=ingenieria)
        for est in (estudiantes["mateo"], estudiantes["sebastian"], estudiantes["valentina"]):
            Inscripcion.objects.create(estudiante=est, actividad=voleibol)

        # Horas de actividades externas -----------------------------------------
        def externa(est, nombre, tipo, dias, horas, estado=RegistroHoras.Estado.APROBADA, motivo="", soporte=True):
            registro = RegistroHoras(
                estudiante=est, nombre_actividad=nombre, tipo=tipos[tipo],
                fecha_actividad=hoy - timedelta(days=dias), horas=Decimal(horas), estado=estado, motivo=motivo,
            )
            if estado != POR_APROBAR:
                registro.aprobador = bienestar
                registro.fecha_revision = ahora - timedelta(days=max(dias - 3, 1))
            if soporte:
                registro.soporte.save(f"certificado_{est.codigo}_{dias}.pdf", ContentFile(PDF_EJEMPLO), save=False)
            registro.save()

        externa(laura, "Cine foro latinoamericano", "Cultural", 150, "5")
        externa(laura, "Taller de redacción científica", "Investigativa", 66, "2")
        externa(laura, "Charla de ética profesional", "Académica", 190, "4")
        externa(laura, "Carrera atlética 5K", "Deportiva", 140, "4")
        externa(laura, "Torneo de ajedrez", "Deportiva", 180, "4")
        externa(laura, "Taller externo de liderazgo", "Bienestar", 40, "2", POR_APROBAR)
        externa(laura, "Charla de emprendimiento", "Académica", 55, "3", RegistroHoras.Estado.RECHAZADA,
                "El soporte no muestra la fecha ni el nombre del estudiante.")
        externa(estudiantes["daniela"], "Curso de primeros auxilios - Cruz Roja", "Bienestar", 10, "8", POR_APROBAR)

        historico = {  # horas aprobadas de semestres anteriores
            "mateo": [("Brigada de salud comunitaria", "Bienestar", "20"), ("Congreso de ingeniería", "Académica", "16"),
                      ("Coro institucional", "Cultural", "12"), ("Liga de baloncesto", "Deportiva", "8")],
            "isabella": [("Monitoría de programación", "Académica", "16"), ("Festival de teatro", "Cultural", "9"),
                         ("Semillero de redes", "Investigativa", "8")],
            "mariana": [("Jornada de reciclaje", "Bienestar", "10"), ("Feria de emprendimiento", "Académica", "12")],
            "sofia": [("Grupo de danza", "Cultural", "15"), ("Voluntariado en hogar infantil", "Bienestar", "12"),
                      ("Olimpiadas de matemáticas", "Académica", "8")],
            "sebastian": [("Torneo de microfútbol", "Deportiva", "6"), ("Conversatorio de software libre", "Académica", "6")],
            "valentina": [("Consultorio jurídico abierto", "Académica", "10")],
        }
        for clave, filas in historico.items():
            for i, (nombre, tipo, horas) in enumerate(filas):
                externa(estudiantes[clave], nombre, tipo, 200 + 30 * i, horas)

        # Notificaciones ----------------------------------------------------------
        for mensaje, leida in [
            ("Nueva actividad: «Semana de la ingeniería: charlas y talleres» · Académica · 8 h.", True),
            ("Tu solicitud de «Charla de emprendimiento» fue rechazada. Motivo: El soporte no muestra la fecha ni el nombre del estudiante.", True),
            ("Se registró tu asistencia a «Torneo interno de fútbol sala». Tus 4 h quedaron por aprobar.", False),
            ("Bienestar aprobó 6 h de «Voluntariado banco de alimentos». Ya suman a tu acumulado.", False),
        ]:
            Notificacion.objects.create(usuario=laura, mensaje=mensaje, leida=leida)
        Notificacion.objects.create(usuario=andrea, mensaje="Recuerda registrar la asistencia de «Caminata ecológica».")

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {Usuario.objects.count()} usuarios, {Actividad.objects.count()} actividades, "
            f"{RegistroHoras.objects.count()} registros de horas."
        ))
        self._imprimir_usuarios()

    def _imprimir_usuarios(self):
        self.stdout.write(f"\nUsuarios de prueba (contraseña de todos: {CLAVE})")
        for rol, correo in [
            ("Estudiante", "laura.martinez"), ("Líder de actividad", "lider"), ("Bienestar", "bienestar"),
            ("Coordinador", "coordinador.sistemas"), ("Administrador", "admin"),
        ]:
            self.stdout.write(f"  {rol:20} {correo}@{DOMINIO}")
