from flask import Flask, render_template, request, jsonify, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
import bcrypt
from datetime import datetime

import os
from dotenv import load_dotenv
import requests

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)

# ─── CONFIGURACIÓN ──────────────────────────────────────
app.config['SECRET_KEY'] = 'clave_secreta_para_login'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///usuarios.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ─── OPENROUTER ─────────────────────────────────────────
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# ─── CORREO (GMAIL) ─────────────────────────────────────
SMTP_SERVIDOR = "smtp.gmail.com"
SMTP_PUERTO = 587
CORREO_EMISOR = os.getenv("GMAIL_USER")
CONTRASENA_APP = os.getenv("GMAIL_APP_PASSWORD")
CORREO_DESTINO = os.getenv("MAIL_DESTINO", CORREO_EMISOR)

# ─── LÍMITE DE MENSAJES DEL CHATBOT ─────────────────────
LIMITE_MENSAJES_POR_HORA = 10
historial_limites = {}

# ─── BASE DE DATOS ──────────────────────────────────────
db = SQLAlchemy(app)

class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    fecha_registro = db.Column(db.DateTime, default=datetime.utcnow)
    
    def verificar_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    @staticmethod
    def hash_password(password):
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# ─── LOGIN MANAGER ──────────────────────────────────────
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# ─────────────────────────────────────────────
#  Base de datos de áreas y carreras
# ─────────────────────────────────────────────
CARRERAS = {
    "arte": {
        "nombre": "Arte y Creatividad",
        "icono": "🎨",
        "carreras": [
            "Diseño Gráfico", "Diseño de Interiores", "Diseño de Jardines",
            "Diseño de Modas", "Diseño de Joyas", "Artes Plásticas",
            "Pintura", "Escultura", "Danza", "Teatro", "Artesanía",
            "Cerámica", "Dibujo Publicitario", "Restauración y Museología",
            "Modelaje", "Fotografía", "Gestión Gráfica y Publicitaria",
            "Locución y Publicidad", "Actuación", "Camarógrafo",
            "Arte Industrial", "Producción Audiovisual y Multimedia",
            "Comunicación y Producción en Radio y TV", "Diseño del Paisaje",
            "Cine y Video", "Comunicación Escénica para TV", "Música"
        ],
        "descripcion": "Para personas creativas, expresivas y con sensibilidad estética, que buscan transformar el mundo a través del arte, el diseño y la comunicación visual.",
        "universidades": [
            "Universidad de los Andes", "Universidad Nacional de Colombia",
            "Bellas Artes Bogotá", "Universidad Jorge Tadeo Lozano", "Universidad de Boyacá"
        ]
    },
    "sociales": {
        "nombre": "Ciencias Sociales",
        "icono": "📚",
        "carreras": [
            "Psicología", "Trabajo Social", "Idiomas", "Educación Internacional",
            "Historia y Geografía", "Periodismo", "Periodismo Digital", "Derecho",
            "Ciencias Políticas", "Sociología", "Antropología", "Arqueología",
            "Gestión Social y Desarrollo", "Consejería Familiar",
            "Comunicación y Publicidad", "Administración Educativa",
            "Educación Especial", "Psicopedagogía", "Estimulación Temprana",
            "Traducción Simultánea", "Lingüística", "Educación de Párvulos",
            "Bibliotecología", "Museología", "Relaciones Internacionales",
            "Diplomacia", "Comunicación Social", "Redacción Creativa y Publicitaria",
            "Relaciones Públicas", "Comunicación Organizacional",
            "Hotelería y Turismo", "Teología", "Institución Sacerdotal"
        ],
        "descripcion": "Para personas empáticas, reflexivas y comprometidas con el bienestar social, la justicia y la transformación cultural.",
        "universidades": [
            "Universidad Externado", "Universidad Javeriana",
            "Universidad Nacional de Colombia", "Universidad de Boyacá", "UPTC Tunja"
        ]
    },
    "administrativa": {
        "nombre": "Economía, Administración y Finanzas",
        "icono": "📊",
        "carreras": [
            "Administración de Empresas", "Contabilidad", "Auditoría", "Ventas",
            "Márquetin Estratégico", "Gestión y Negocios Internacionales",
            "Gestión Empresarial", "Gestión Financiera", "Ingeniería Comercial",
            "Comercio Exterior", "Banca y Finanzas", "Gestión de Recursos Humanos",
            "Comunicaciones Integradas en Márquetin",
            "Administración de Empresas Ecoturísticas y de Hospitalidad",
            "Ciencias Económicas y Financieras",
            "Administración y Ciencias Políticas", "Ciencias Empresariales",
            "Comercio Electrónico", "Emprendimiento",
            "Gestión de Organismos Públicos", "Gestión de Centros Educativos"
        ],
        "descripcion": "Para personas organizadas, líderes y con visión estratégica, capaces de gestionar recursos y generar desarrollo económico.",
        "universidades": [
            "Universidad EAN", "Universidad de los Andes", "Uninorte",
            "Universidad de Boyacá", "UPTC Tunja"
        ]
    },
    "tecnologia": {
        "nombre": "Ciencia y Tecnología",
        "icono": "💻",
        "carreras": [
            "Ingeniería en Sistemas Computacionales", "Geología", "Ingeniería Civil",
            "Arquitectura", "Electrónica", "Telemática", "Telecomunicaciones",
            "Ingeniería Mecatrónica (Robótica)", "Imagen y Sonido", "Minas",
            "Petróleo y Metalurgia", "Ingeniería Mecánica", "Ingeniería Industrial",
            "Física", "Matemáticas Aplicadas", "Ingeniería en Estadística",
            "Ingeniería Automotriz", "Biotecnología Ambiental",
            "Ingeniería Geográfica", "Carreras Militares (Marina, Aviación, Ejército)",
            "Ingeniería en Costas y Obras Portuarias", "Estadística",
            "Informática", "Programación y Desarrollo de Sistemas",
            "Tecnología en Informática Educativa", "Astronomía",
            "Ingeniería en Ciencias Geográficas", "Desarrollo Sustentable"
        ],
        "descripcion": "Para mentes analíticas, curiosas y apasionadas por resolver problemas lógicos, científicos y tecnológicos.",
        "universidades": [
            "Universidad Nacional de Colombia", "UPTC Tunja",
            "Universidad de los Andes", "SENA", "Politécnico Grancolombiano"
        ]
    },
    "salud": {
        "nombre": "Ciencias Ecológicas, Biológicas y de la Salud",
        "icono": "🔬",
        "carreras": [
            "Biología", "Bioquímica", "Farmacia", "Biología Marina", "Bioanálisis",
            "Biotecnología", "Ciencias Ambientales", "Zootecnia", "Veterinaria",
            "Nutrición y Estética", "Cosmetología", "Dietética y Estética",
            "Medicina", "Obstetricia", "Urgencias Médicas", "Odontología",
            "Enfermería", "Tecnología", "Oceanografía y Ciencias Ambientales",
            "Agronomía", "Horticultura y Fruticultura", "Ingeniería de Alimentos",
            "Gastronomía", "Cultura Física", "Deportes y Rehabilitación",
            "Gestión Ambiental", "Ingeniería Ambiental", "Optometría",
            "Homeopatía", "Reflexología"
        ],
        "descripcion": "Para personas vocacionadas al servicio, interesadas en la salud, el cuidado del medio ambiente y el bienestar de los seres vivos.",
        "universidades": [
            "Universidad Nacional de Colombia", "UPTC Tunja",
            "Universidad de los Andes", "Universidad de Boyacá", "Universidad Javeriana"
        ]
    }
}

# ─────────────────────────────────────────────
#  Preguntas del test vocacional (80 preguntas)
# ─────────────────────────────────────────────
TEST_PREGUNTAS = [
    {"id": 1, "pregunta": "Diseñar programas de computación y explorar nuevas aplicaciones tecnológicas para uso del internet.", "area": "tecnologia"},
    {"id": 2, "pregunta": "Criar, cuidar y tratar animales domésticos y de campo.", "area": "salud"},
    {"id": 3, "pregunta": "Investigar sobre áreas verdes, medioambiente y cambios climáticos.", "area": "salud"},
    {"id": 4, "pregunta": "Ilustrar, dibujar y animar digitalmente.", "area": "arte"},
    {"id": 5, "pregunta": "Seleccionar, capacitar y motivar al personal de una organización o empresa.", "area": "administrativa"},
    {"id": 6, "pregunta": "Realizar excavaciones para descubrir restos del pasado.", "area": "sociales"},
    {"id": 7, "pregunta": "Resolver problemas de cálculo para construir un puente.", "area": "tecnologia"},
    {"id": 8, "pregunta": "Diseñar cursos para enseñar a la gente sobre temas de salud e higiene.", "area": "salud"},
    {"id": 9, "pregunta": "Tocar un instrumento y componer música.", "area": "arte"},
    {"id": 10, "pregunta": "Planificar cuáles son las metas de una organización pública o privada a mediano y largo plazo.", "area": "administrativa"},
    {"id": 11, "pregunta": "Diseñar y planificar la producción masiva de artículos como muebles, autos, equipos de oficina, empaques y envases para alimentos y otros.", "area": "tecnologia"},
    {"id": 12, "pregunta": "Diseñar logotipos y portadas de una revista.", "area": "arte"},
    {"id": 13, "pregunta": "Organizar eventos y atender a sus asistentes.", "area": "sociales"},
    {"id": 14, "pregunta": "Atender la salud de personas enfermas.", "area": "salud"},
    {"id": 15, "pregunta": "Controlar ingresos y egresos de fondos y presentar el balance final de una institución.", "area": "administrativa"},
    {"id": 16, "pregunta": "Hacer experimentos con plantas (frutas, árboles, flores).", "area": "salud"},
    {"id": 17, "pregunta": "Concebir planos para viviendas, edificios y ciudadelas.", "area": "tecnologia"},
    {"id": 18, "pregunta": "Investigar y probar nuevos productos farmacéuticos.", "area": "tecnologia"},
    {"id": 19, "pregunta": "Hacer propuestas y formular estrategias para aprovechar las relaciones económicas entre dos países.", "area": "administrativa"},
    {"id": 20, "pregunta": "Pintar, hacer esculturas, ilustrar libros de arte, etcétera.", "area": "arte"},
    {"id": 21, "pregunta": "Elaborar campañas para introducir un nuevo producto al mercado.", "area": "administrativa"},
    {"id": 22, "pregunta": "Examinar y tratar los problemas visuales.", "area": "salud"},
    {"id": 23, "pregunta": "Defender a clientes individuales o empresas en juicios de diferente naturaleza.", "area": "sociales"},
    {"id": 24, "pregunta": "Diseñar máquinas que puedan simular actividades humanas.", "area": "tecnologia"},
    {"id": 25, "pregunta": "Investigar las causas y efectos de los trastornos emocionales.", "area": "sociales"},
    {"id": 26, "pregunta": "Supervisar las ventas de un centro comercial.", "area": "administrativa"},
    {"id": 27, "pregunta": "Atender y realizar ejercicios a personas que tienen limitaciones físicas, problemas de lenguaje, etc.", "area": "salud"},
    {"id": 28, "pregunta": "Prepararse para ser modelo profesional.", "area": "arte"},
    {"id": 29, "pregunta": "Aconsejar a las personas sobre planes de ahorro e inversiones.", "area": "administrativa"},
    {"id": 30, "pregunta": "Elaborar mapas, planos e imágenes para el estudio y análisis de datos geográficos.", "area": "tecnologia"},
    {"id": 31, "pregunta": "Diseñar juegos interactivos electrónicos para computadora.", "area": "arte"},
    {"id": 32, "pregunta": "Realizar el control de calidad de los alimentos.", "area": "salud"},
    {"id": 33, "pregunta": "Tener un negocio propio de tipo comercial.", "area": "administrativa"},
    {"id": 34, "pregunta": "Escribir artículos periodísticos, cuentos, novelas y otros.", "area": "sociales"},
    {"id": 35, "pregunta": "Redactar guiones y libretos para un programa de televisión.", "area": "arte"},
    {"id": 36, "pregunta": "Organizar un plan de distribución y venta de un gran almacén.", "area": "administrativa"},
    {"id": 37, "pregunta": "Estudiar la diversidad cultural en el ámbito rural y urbano.", "area": "sociales"},
    {"id": 38, "pregunta": "Gestionar y evaluar convenios internacionales de cooperación para el desarrollo social.", "area": "sociales"},
    {"id": 39, "pregunta": "Crear campañas publicitarias.", "area": "arte"},
    {"id": 40, "pregunta": "Trabajar investigando la reproducción de peces, camarones y otros animales marinos.", "area": "salud"},
    {"id": 41, "pregunta": "Dedicarse a fabricar productos alimenticios de consumo masivo.", "area": "tecnologia"},
    {"id": 42, "pregunta": "Gestionar y evaluar proyectos de desarrollo en una institución educativa y/o fundación.", "area": "sociales"},
    {"id": 43, "pregunta": "Rediseñar y decorar espacios físicos en viviendas, oficinas y locales comerciales.", "area": "arte"},
    {"id": 44, "pregunta": "Administrar una empresa de turismo o agencias de viaje.", "area": "administrativa"},
    {"id": 45, "pregunta": "Aplicar métodos alternativos a la medicina tradicional, para atender personas con dolencias de diversa índole.", "area": "salud"},
    {"id": 46, "pregunta": "Diseñar ropa para niños, jóvenes y adultos.", "area": "arte"},
    {"id": 47, "pregunta": "Investigar organismos vivos para elaborar vacunas.", "area": "salud"},
    {"id": 48, "pregunta": "Manejar o hacerle mantenimiento a dispositivos tecnológicos en aviones, barcos, radares, etc.", "area": "tecnologia"},
    {"id": 49, "pregunta": "Estudiar idiomas extranjeros —actuales y antiguos— para hacer traducción.", "area": "sociales"},
    {"id": 50, "pregunta": "Restaurar piezas y obras de arte.", "area": "arte"},
    {"id": 51, "pregunta": "Revisar y dar mantenimiento a artefactos eléctricos, electrónicos y computadoras.", "area": "tecnologia"},
    {"id": 52, "pregunta": "Enseñar a niños de cero a cinco años.", "area": "sociales"},
    {"id": 53, "pregunta": "Investigar o sondear nuevos mercados.", "area": "administrativa"},
    {"id": 54, "pregunta": "Atender la salud dental de las personas.", "area": "salud"},
    {"id": 55, "pregunta": "Tratar a niños, jóvenes y adultos con problemas psicológicos.", "area": "sociales"},
    {"id": 56, "pregunta": "Crear estrategias de promoción y venta de nuevos productos nacionales en el mercado internacional.", "area": "administrativa"},
    {"id": 57, "pregunta": "Planificar y recomendar dietas para personas diabéticas o con sobrepeso.", "area": "salud"},
    {"id": 58, "pregunta": "Trabajar en una empresa petrolera en un cargo técnico como control de la producción.", "area": "tecnologia"},
    {"id": 59, "pregunta": "Administrar una empresa (familiar, privada o pública).", "area": "administrativa"},
    {"id": 60, "pregunta": "Tener un taller de reparación y mantenimiento de carros, tractores, etcétera.", "area": "tecnologia"},
    {"id": 61, "pregunta": "Ejecutar proyectos de extracción minera y metalúrgica.", "area": "tecnologia"},
    {"id": 62, "pregunta": "Asistir a directivos de multinacionales con manejo de varios idiomas.", "area": "administrativa"},
    {"id": 63, "pregunta": "Diseñar programas educativos para niños con discapacidad.", "area": "sociales"},
    {"id": 64, "pregunta": "Aplicar conocimientos de estadística en investigaciones en diversas áreas (social, administrativa, salud, etcétera).", "area": "tecnologia"},
    {"id": 65, "pregunta": "Fotografiar hechos históricos, lugares significativos, rostros, paisajes para el área publicitaria, artística, periodística y social.", "area": "arte"},
    {"id": 66, "pregunta": "Trabajar en museos y bibliotecas nacionales e internacionales.", "area": "sociales"},
    {"id": 67, "pregunta": "Ser parte de un grupo de teatro.", "area": "arte"},
    {"id": 68, "pregunta": "Producir cortometrajes, spots publicitarios, programas educativos, de ficción, etc.", "area": "arte"},
    {"id": 69, "pregunta": "Estudiar la influencia entre las corrientes marinas y el clima y sus consecuencias ecológicas.", "area": "salud"},
    {"id": 70, "pregunta": "Conocer las distintas religiones (su filosofía) y transmitirlas a la comunidad en general.", "area": "sociales"},
    {"id": 71, "pregunta": "Asesorar a inversionistas en la compra de bienes y acciones en mercados nacionales e internacionales.", "area": "administrativa"},
    {"id": 72, "pregunta": "Estudiar grupos étnicos, sus costumbres, tradiciones, cultura y compartir sus vivencias.", "area": "sociales"},
    {"id": 73, "pregunta": "Explorar el espacio sideral, los planetas, características y componentes.", "area": "tecnologia"},
    {"id": 74, "pregunta": "Mejorar la imagen facial y corporal de las personas, aplicando diferentes técnicas.", "area": "salud"},
    {"id": 75, "pregunta": "Decorar jardines de casas y parques públicos.", "area": "arte"},
    {"id": 76, "pregunta": "Administrar y renovar menús de comidas en un hotel o restaurante.", "area": "salud"},
    {"id": 77, "pregunta": "Trabajar como presentador de televisión, locutor de radio y televisión, animador de programas culturales y concursos.", "area": "arte"},
    {"id": 78, "pregunta": "Diseñar y ejecutar programas de turismo.", "area": "sociales"},
    {"id": 79, "pregunta": "Administrar y ordenar (planificar) adecuadamente la ocupación del espacio.", "area": "tecnologia"},
    {"id": 80, "pregunta": "Gestionar y evaluar proyectos de desarrollo en una institución pública o privada.", "area": "administrativa"}
]

# ─────────────────────────────────────────────
#  FUNCIÓN DE ENVÍO DE CORREO
# ─────────────────────────────────────────────
def enviar_correo_contacto(nombre, correo_usuario, grado, mensaje):
    if not CORREO_EMISOR or not CONTRASENA_APP:
        raise Exception("Faltan GMAIL_USER o GMAIL_APP_PASSWORD en el archivo .env")

    asunto = f"Nuevo mensaje de {nombre} ({grado}) - Voca-IA"
    cuerpo = f"""
──────────────────────────────
NUEVO MENSAJE DE CONTACTO
──────────────────────────────
Nombre:  {nombre}
Correo:  {correo_usuario}
Grado:   {grado}
Fecha:   {datetime.now().strftime('%d/%m/%Y %H:%M')}
──────────────────────────────
Mensaje:
{mensaje}
──────────────────────────────
"""

    msg = MIMEMultipart()
    msg["From"] = formataddr((nombre, CORREO_EMISOR))
    msg["To"] = CORREO_DESTINO
    msg["Reply-To"] = formataddr((nombre, correo_usuario))
    msg["Subject"] = asunto
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))

    with smtplib.SMTP(SMTP_SERVIDOR, SMTP_PUERTO) as servidor:
        servidor.starttls()
        servidor.login(CORREO_EMISOR, CONTRASENA_APP)
        servidor.sendmail(CORREO_EMISOR, CORREO_DESTINO, msg.as_string())

# ─────────────────────────────────────────────
#  RUTAS DE LOGIN
# ─────────────────────────────────────────────

@app.route('/')
def raiz():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        usuario = Usuario.query.filter_by(email=request.form['email']).first()
        if usuario and usuario.verificar_password(request.form['password']):
            login_user(usuario)
            return redirect(url_for('dashboard'))
        return render_template('login.html', error='Email o contraseña incorrectos')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        if Usuario.query.filter_by(email=request.form['email']).first():
            return render_template('registro.html', error='Email ya registrado')
        usuario = Usuario(
            nombre=request.form['nombre'],
            email=request.form['email'],
            password_hash=Usuario.hash_password(request.form['password'])
        )
        db.session.add(usuario)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', usuario=current_user)

# ─────────────────────────────────────────────
#  RUTAS DE LA APLICACIÓN (PROTEGIDAS)
# ─────────────────────────────────────────────

@app.route('/inicio')
@login_required
def inicio():
    return render_template('index.html')

# Alias para que url_for('index') también funcione
app.add_url_rule('/index', endpoint='index', view_func=inicio)

@app.route('/test')
@login_required
def test():
    return render_template('test.html')

@app.route('/chatbot')
@login_required
def chatbot():
    return render_template('chatbot.html')

@app.route('/areas')
@login_required
def areas():
    return render_template('areas.html')

@app.route('/vision')
@login_required
def vision():
    return render_template('vision.html')

@app.route('/contacto')
def contacto():
    return render_template('index.html')

# ─────────────────────────────────────────────
#  API RUTAS
# ─────────────────────────────────────────────

@app.route('/api/preguntas')
def get_preguntas():
    return jsonify(TEST_PREGUNTAS)

@app.route('/api/resultado', methods=['POST'])
def calcular_resultado():
    data = request.get_json()
    respuestas = data.get('respuestas', [])
    conteo = {area: 0 for area in CARRERAS.keys()}
    total_por_area = {area: 0 for area in CARRERAS.keys()}
    for respuesta in respuestas:
        area = respuesta.get('area')
        if area in conteo:
            total_por_area[area] += 1
            if respuesta.get('me_interesa'):
                conteo[area] += 1
    resultados = []
    for area in CARRERAS.keys():
        total = total_por_area[area]
        aciertos = conteo[area]
        porcentaje = round((aciertos / total) * 100) if total > 0 else 0
        info = CARRERAS[area].copy()
        info['area'] = area
        info['puntaje'] = aciertos
        info['total'] = total
        info['porcentaje'] = porcentaje
        resultados.append(info)
    ranking = sorted(resultados, key=lambda x: (x['puntaje'], x['porcentaje']), reverse=True)
    return jsonify({
        'perfil_principal': ranking[0],
        'otros_perfiles': ranking[1:3],
        'todos_los_perfiles': ranking,
        'total_preguntas': len(respuestas)
    })

@app.route('/api/carreras')
def get_todas_carreras():
    return jsonify(CARRERAS)

# ─────────────────────────────────────────────
#  API DE CONTACTO
# ─────────────────────────────────────────────
@app.route('/api/contacto', methods=['POST'])
def api_contacto():
    try:
        data = request.get_json() or {}
        nombre         = (data.get("nombre")  or "").strip()
        correo_usuario = (data.get("correo")  or "").strip()
        grado          = (data.get("grado")   or "").strip()
        mensaje        = (data.get("mensaje") or "").strip()

        if not (nombre and correo_usuario and grado and mensaje):
            return jsonify({"ok": False, "error": "Campos incompletos"}), 400

        if "@" not in correo_usuario or "." not in correo_usuario.split("@")[-1]:
            return jsonify({"ok": False, "error": "Correo electrónico inválido"}), 400

        enviar_correo_contacto(nombre, correo_usuario, grado, mensaje)
        return jsonify({"ok": True, "mensaje": "Correo enviado correctamente"})

    except Exception as e:
        print(f"Error al enviar correo: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500

# ─────────────────────────────────────────────
#  API DEL CHATBOT (CON MEMORIA)
# ─────────────────────────────────────────────
@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # ─── LÍMITE DE MENSAJES POR HORA ───
        if current_user.is_authenticated:
            usuario_id = current_user.id
            ahora = datetime.utcnow()
            if usuario_id not in historial_limites:
                historial_limites[usuario_id] = []
            historial_limites[usuario_id] = [
                t for t in historial_limites[usuario_id]
                if (ahora - t).total_seconds() < 3600
            ]
            if len(historial_limites[usuario_id]) >= LIMITE_MENSAJES_POR_HORA:
                return jsonify({
                    'respuesta': f'⚠️ Has alcanzado el límite de {LIMITE_MENSAJES_POR_HORA} mensajes por hora. Por favor, espera un rato antes de seguir preguntando.'
                })
            historial_limites[usuario_id].append(ahora)

        # ─── DATOS DEL MENSAJE ───
        data = request.get_json()
        mensaje = data.get('mensaje', '').strip()

        if not mensaje:
            return jsonify({'respuesta': 'Por favor, escribe una pregunta.'})

        if not OPENROUTER_API_KEY:
            return jsonify({'respuesta': 'Error: falta la API Key en el archivo .env'})

        # ─── MEMORIA: RECUPERAR HISTORIAL DE LA SESIÓN ───
        historial = session.get('chat_historial', [])

        # Agregar el mensaje del usuario al historial
        historial.append({'role': 'user', 'content': mensaje})

        # Limitar el historial a los últimos 10 mensajes (para no gastar tokens)
        historial_reciente = historial[-10:] if len(historial) > 10 else historial

        # ─── SYSTEM PROMPT ───
        system_prompt = """Eres un orientador vocacional de la I.E. San Luis de Gaceno en Boyacá, Colombia.
Ayudas a estudiantes de grado 9°, 10° y 11° a elegir su carrera profesional.
Conoces las universidades colombianas (UPTC Tunja, Universidad Nacional, SENA, Universidad de Boyacá, UNAD, etc.).
Responde de forma amable, clara, motivadora y breve (máximo 120 palabras).
Recuerda el contexto de la conversación para dar respuestas coherentes."""

        # ─── CONSTRUIR MENSAJES CON HISTORIAL ───
        mensajes_para_ia = [{"role": "system", "content": system_prompt}] + historial_reciente

        # ─── LLAMADA A OPENROUTER ───
        response = requests.post(
            url=OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "http://localhost:5000",
                "X-Title": "Voca-IA"
            },
            json={
                "model": "nvidia/nemotron-3-super-120b-a12b:free",
                "messages": mensajes_para_ia
            },
            timeout=30
        )

        if response.status_code == 200:
            respuesta_ia = response.json()["choices"][0]["message"]["content"]

            # ─── GUARDAR RESPUESTA EN EL HISTORIAL ───
            historial.append({'role': 'assistant', 'content': respuesta_ia})
            session['chat_historial'] = historial
            session.modified = True

            return jsonify({'respuesta': respuesta_ia})
        else:
            print(f"Error OpenRouter: {response.status_code} - {response.text}")
            return jsonify({'respuesta': 'Error al conectar con la IA. Intenta de nuevo.'})
    
    except Exception as e:
        print(f"Error en chat: {e}")
        return jsonify({'respuesta': 'Lo siento, hubo un error. Intenta de nuevo.'})

# ─────────────────────────────────────────────
#  API PARA LIMPIAR EL HISTORIAL DEL CHAT
# ─────────────────────────────────────────────
@app.route('/api/chat/limpiar', methods=['POST'])
def limpiar_chat():
    session.pop('chat_historial', None)
    return jsonify({'mensaje': 'Historial borrado correctamente'})

# ─────────────────────────────────────────────
#  CREAR TABLAS Y EJECUTAR
# ─────────────────────────────────────────────

with app.app_context():
    db.create_all()

if __name__ == '__main__':
    print("\n" + "=" * 55)
    print("  ✅  Orientación Vocacional - I.E. San Luis de Gaceno")
    print("  🌐  Abre tu navegador en: http://localhost:5000")
    print("  📧  Contacto con correo del usuario habilitado")
    print("  🧠  Chatbot con memoria activada")
    print("=" * 55 + "\n")
    app.run(debug=True, port=5000)