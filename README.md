# Sistema de Gestión de Horas, Actividades y Eventos Estudiantiles

Proyecto de aula · 6.º semestre de Ingeniería de Sistemas · Universidad Cooperativa de Colombia, campus Montería.
Docente: Delia Herazo.

Plataforma web para registrar, controlar y hacer seguimiento a las horas que los estudiantes dedican a
actividades académicas, investigativas, culturales, deportivas y de bienestar. Cada estudiante ve en todo
momento cuántas horas lleva y cuántas le faltan para la meta de su programa.

## Avance de la Semana 3 (Desarrollo)

| Actividad del plan | Qué quedó hecho |
|---|---|
| Implementar base de datos | 8 tablas del modelo entidad-relación en MySQL (XAMPP), con llaves foráneas y restricciones |
| Implementar autenticación y roles | Login con correo institucional, 5 roles, menú por rol, error 403 si un rol entra donde no debe |
| Construir backend | Reglas de negocio en `actividades/services.py` y `horas/services.py` |
| Implementar CRUD | Usuarios, programas, actividades, inscripciones, asistencia, soportes y aprobación de horas |
| Construir frontend | Pantallas del prototipo con Bootstrap 5, adaptadas a celular |
| Integrar componentes | API REST, datos de demostración, instalador y 55 pruebas automáticas |

**Para la Semana 4:** dashboard con gráficas, reportes en Excel y PDF, constancia en PDF, matriz de pruebas
y manual de usuario.

## Requisitos

- **Python 3.10 o superior** (al instalarlo en Windows, marca «Add Python to PATH»).
- **XAMPP** con **MySQL** encendido (botón *Start* en el panel de control).

## Instalación

### Windows (automática)

1. Abre XAMPP y enciende **MySQL**.
2. Doble clic en **`instalar.bat`**. Crea el entorno virtual, instala las dependencias, genera el `.env`,
   crea la base de datos `horas_ucc` en MySQL, crea las tablas y carga datos de demostración.
3. Doble clic en **`iniciar.bat`**. Se abre el navegador en <http://127.0.0.1:8000/>.

### Paso a paso (Windows, macOS o Linux)

```bash
python -m venv venv
venv\Scripts\activate            # Windows
source venv/bin/activate         # macOS / Linux

pip install -r requirements.txt
python crear_env.py              # crea .env (conexión a MySQL de XAMPP: root sin contraseña)
python crear_bd.py               # crea la base de datos horas_ucc
python manage.py migrate         # crea las tablas
python manage.py datos_demo      # usuarios y datos de prueba
python manage.py runserver
```

Si tu MySQL tiene contraseña o usa otro puerto, cámbialo en el archivo `.env`.
Las tablas se pueden revisar en phpMyAdmin (<http://localhost/phpmyadmin>, base `horas_ucc`).

## Usuarios de prueba

Contraseña de todos: **`Horas2026*`**

| Rol | Correo | Qué puede hacer |
|---|---|---|
| Estudiante | laura.martinez@campusucc.edu.co | Ver sus horas, inscribirse en actividades, cargar soportes |
| Líder de actividad | lider@campusucc.edu.co | Crear y publicar actividades, registrar asistencia |
| Bienestar universitario | bienestar@campusucc.edu.co | Aprobar o rechazar horas, gestionar actividades, seguimiento |
| Coordinador de programa | coordinador.sistemas@campusucc.edu.co | Seguimiento de los estudiantes de su programa |
| Administrador | admin@campusucc.edu.co | Usuarios, programas y meta de horas; también entra a `/admin/` |

Para probar el ciclo completo de una hora: entra como **líder** y registra la asistencia de «Caminata
ecológica»; luego entra como **bienestar** y aprueba esas horas; por último entra como **estudiante** y mira
cómo suben en «Mis horas».

## Reglas de negocio implementadas

- Una hora solo suma al acumulado cuando Bienestar la **aprueba**.
- No se permite inscribirse dos veces, inscribirse sin cupos ni en actividades que ya empezaron.
- Cancelar una inscripción libera el cupo; solo se puede antes de que empiece la actividad.
- La asistencia la registra el responsable de la actividad (o Bienestar) cuando la actividad ya empezó; a
  cada asistente se le generan sus horas «Por aprobar».
- Soportes externos: obligatorio el archivo (PDF, JPG o PNG, máximo 5 MB), horas entre 0,5 y 40, fecha no futura.
- Rechazar o ajustar horas exige escribir el motivo; el estudiante recibe una notificación con él.
- Las horas que Bienestar ya revisó no se pueden cambiar desde la asistencia.
- Estado de cumplimiento: **Cumple** (alcanzó la meta), **En riesgo** (8.º semestre o más sin la meta),
  **En progreso** (el resto).
- Los soportes no son públicos: solo los descargan su dueño, Bienestar y el administrador.

## API REST

Requiere sesión iniciada (o usuario y contraseña con autenticación básica).

| Método | Ruta | Qué hace | Rol |
|---|---|---|---|
| GET | `/api/actividades/` | Actividades publicadas con sus cupos libres | Todos |
| POST | `/api/inscripciones/` | Inscribe al estudiante: `{"actividad": 5}` | Estudiante |
| GET | `/api/mis-horas/` | Horas aprobadas, por aprobar y las que faltan | Estudiante |
| GET | `/api/notificaciones/` | Notificaciones sin leer | Todos |
| GET | `/api/dashboard/` | Indicadores generales | Bienestar, Coordinador, Administrador |

Ejemplo: `curl -u laura.martinez@campusucc.edu.co:Horas2026* http://127.0.0.1:8000/api/mis-horas/`

## Pruebas

```bash
python manage.py test
```

Las pruebas crean una base temporal en MySQL (`test_horas_ucc`) y la borran al terminar. Cubren las reglas de
negocio, los permisos por rol, la API y el flujo completo crear → inscribir → asistir → aprobar.

## Arquitectura y estructura

Aplicación web en capas con el patrón MVT de Django: las vistas web y la API llaman a los mismos `services.py`,
que hablan con la base de datos por medio de los modelos (ORM).

```
horas_ucc/
├── config/            settings.py, urls.py y el backend de MySQL para XAMPP
├── usuarios/          usuario, programa, login, roles, menú (M1)
├── actividades/       actividad, tipo_actividad, inscripción, asistencia (M2, M3)
├── horas/             registro_horas, constancia, soportes, aprobación (M4, M5)
├── reportes/          seguimiento por programa (M6)
├── notificaciones/    notificaciones (M7)
├── api/               servicios REST
├── templates/         base.html y las pantallas de cada rol
└── static/            estilos y Bootstrap 5 (incluido, funciona sin internet)
```

### Nota técnica sobre XAMPP

XAMPP trae MariaDB 10.4 y Django 5.2 pide 10.5 o superior. El backend `config/backend_mysql` solo baja esa
versión mínima; las funciones que necesitan 10.5 Django ya las desactiva al detectar una versión anterior.
Para conectarse se usa **PyMySQL**, que se instala en Windows sin compilar nada.

Los archivos `.env`, `venv/` y los soportes subidos (`media/soportes/`) no se guardan en Git.
