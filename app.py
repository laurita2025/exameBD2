import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_bcrypt import Bcrypt
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from datetime import datetime, timedelta
import random

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "super-secret-key")
app.config["MONGO_URI"] = os.environ.get(
    "MONGO_URI",
    "mongodb+srv://admin:LauraCordero2026@cluster0.zlolgqj.mongodb.net/examen_bd2?retryWrites=true&w=majority"
)

# Si usas la URI de Atlas desde el panel, asegúrate de que solo haya un signo de pregunta
# al inicio de los parámetros. Ejemplo correcto:
# mongodb+srv://admin:password@cluster0.zlolgqj.mongodb.net/examen_bd2?retryWrites=true&w=majority
# URI incorrecta con dos signos de pregunta:
# mongodb+srv://admin:password@cluster0.zlolgqj.mongodb.net/?appName=Cluster0?retryWrites=true&w=majority

# Reemplaza <db_password> y ajusta el nombre de base de datos, por ejemplo:
# mongodb+srv://admin:MiClave@cluster0.zlolgqj.mongodb.net/examen_bd2?retryWrites=true&w=majority

mongo = PyMongo(app)
bcrypt = Bcrypt(app)

# Colecciones
usuarios = mongo.db.usuarios
preguntas = mongo.db.preguntas
examenes = mongo.db.examenes
resultados = mongo.db.resultados
control_eventos = mongo.db.control_eventos
bloqueos_examenes = mongo.db.bloqueos_examenes

# ==============================
# Verificar Administrador
# ==============================

def es_admin():

    if "usuario" not in session:
        return False

    return session.get("rol") == "admin"

# Página inicial
@app.route("/")
def index():
    if "usuario" in session:
        return redirect(url_for("dashboard"))
    return render_template("index.html")

# Registro
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        if usuarios.find_one({"email": email}):
            flash("El correo ya está registrado", "danger")
            return redirect(url_for("register"))
        password_hash = bcrypt.generate_password_hash(password).decode("utf-8")
        usuarios.insert_one({"nombre": nombre, "email": email, "password": password_hash, "rol": "estudiante","created_at": datetime.utcnow()})
        flash("Registro exitoso, por favor inicia sesión.", "success")
        return redirect(url_for("login"))
    return render_template("register.html")

# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"]
        usuario = usuarios.find_one({"email": email})
        if usuario and bcrypt.check_password_hash(usuario["password"], password):

    # Guardar información del usuario en la sesión
            session["usuario"] = str(usuario["_id"])
            session["nombre"] = usuario["nombre"]
            session["rol"] = usuario.get("rol", "estudiante")

            flash(f"Bienvenido, {usuario['nombre']}", "success")
            return redirect(url_for("dashboard"))
        flash("Credenciales incorrectas", "danger")
        return redirect(url_for("login"))
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada", "info")
    return redirect(url_for("login"))

# Dashboard
@app.route("/dashboard")
def dashboard():
    if "usuario" not in session:
        return redirect(url_for("login"))
    total_preguntas = preguntas.count_documents({})
    total_examenes = examenes.count_documents({})
    total_resultados = resultados.count_documents({"usuario_id": ObjectId(session["usuario"])})
    return render_template("dashboard.html", total_preguntas=total_preguntas, total_examenes=total_examenes, total_resultados=total_resultados)

# CRUD Preguntas
@app.route("/preguntas")
def lista_preguntas():

    if "usuario" not in session:
        return redirect(url_for("login"))

    if not es_admin():
        flash("Acceso denegado.", "danger")
        return redirect(url_for("dashboard"))

    todas = list(preguntas.find())

    return render_template(
        "preguntas.html",
        preguntas=todas
    )

@app.route("/preguntas/nueva", methods=["GET", "POST"])
def nueva_pregunta():

    # Verificar que haya iniciado sesión
    if "usuario" not in session:
        return redirect(url_for("login"))

    # Solo el administrador puede crear preguntas
    if not es_admin():
        flash("Acceso denegado. Solo el administrador puede crear preguntas.", "danger")
        return redirect(url_for("dashboard"))

    if request.method == "POST":

        texto = request.form["texto"].strip()

        opciones = [
            request.form["opcion1"].strip(),
            request.form["opcion2"].strip(),
            request.form["opcion3"].strip(),
            request.form["opcion4"].strip()
        ]

        correcta = request.form["correcta"]

        preguntas.insert_one({
            "texto": texto,
            "opciones": opciones,
            "correcta": correcta,
            "created_at": datetime.utcnow()
        })

        flash("Pregunta creada correctamente.", "success")
        return redirect(url_for("lista_preguntas"))

    return render_template("pregunta_form.html", pregunta=None)

@app.route("/preguntas/editar/<id>", methods=["GET", "POST"])
def editar_pregunta(id):
    if "usuario" not in session:
        return redirect(url_for("login"))
    pregunta = preguntas.find_one({"_id": ObjectId(id)})
    if request.method == "POST":
        texto = request.form["texto"].strip()
        opciones = [request.form["opcion1"].strip(), request.form["opcion2"].strip(), request.form["opcion3"].strip(), request.form["opcion4"].strip()]
        correcta = request.form["correcta"]
        preguntas.update_one({"_id": ObjectId(id)}, {"$set": {"texto": texto, "opciones": opciones, "correcta": correcta}})
        flash("Pregunta actualizada", "success")
        return redirect(url_for("lista_preguntas"))
    return render_template("pregunta_form.html", pregunta=pregunta)

@app.route("/preguntas/eliminar/<id>")
def eliminar_pregunta(id):
    if "usuario" not in session:
        return redirect(url_for("login"))
    preguntas.delete_one({"_id": ObjectId(id)})
    flash("Pregunta eliminada", "warning")
    return redirect(url_for("lista_preguntas"))

# CRUD Exámenes
@app.route("/examenes")
def lista_examenes():
    if "usuario" not in session:
        return redirect(url_for("login"))
    todos = list(examenes.find())
    return render_template("examenes.html", examenes=todos)

@app.route("/examenes/nuevo", methods=["GET", "POST"])
def nuevo_examen():
    if "usuario" not in session:
        return redirect(url_for("login"))
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        descripcion = request.form["descripcion"].strip()
        tiempo = int(request.form["tiempo"])
        pregunta_ids = request.form.getlist("preguntas")
        examenes.insert_one({"nombre": nombre, "descripcion": descripcion, "tiempo": tiempo, "preguntas": [ObjectId(pid) for pid in pregunta_ids], "created_at": datetime.utcnow()})
        flash("Examen creado", "success")
        return redirect(url_for("lista_examenes"))
    todas = list(preguntas.find())
    return render_template("examen_form.html", examen=None, preguntas=todas)

@app.route("/examenes/editar/<id>", methods=["GET", "POST"])
def editar_examen(id):
    if "usuario" not in session:
        return redirect(url_for("login"))
    examen = examenes.find_one({"_id": ObjectId(id)})
    if request.method == "POST":
        nombre = request.form["nombre"].strip()
        descripcion = request.form["descripcion"].strip()
        tiempo = int(request.form["tiempo"])
        pregunta_ids = request.form.getlist("preguntas")
        examenes.update_one({"_id": ObjectId(id)}, {"$set": {"nombre": nombre, "descripcion": descripcion, "tiempo": tiempo, "preguntas": [ObjectId(pid) for pid in pregunta_ids]}})
        flash("Examen actualizado", "success")
        return redirect(url_for("lista_examenes"))
    todas = list(preguntas.find())
    return render_template("examen_form.html", examen=examen, preguntas=todas)

@app.route("/examenes/eliminar/<id>")
def eliminar_examen(id):
    if "usuario" not in session:
        return redirect(url_for("login"))
    examenes.delete_one({"_id": ObjectId(id)})
    flash("Examen eliminado", "warning")
    return redirect(url_for("lista_examenes"))

# Examen aleatorio de banco
@app.route("/examenes/aleatorio")
def examen_aleatorio():
    if "usuario" not in session:
        return redirect(url_for("login"))
    bloqueo = bloqueos_examenes.find_one({
        "usuario_id": ObjectId(session["usuario"]),
        "examen_id": "aleatorio"
    })
    if bloqueo and bloqueo.get("bloqueado"):
        flash("Has sido bloqueado para realizar el examen aleatorio por exceder el límite de advertencias.", "danger")
        return redirect(url_for("dashboard"))
    banco = list(preguntas.find())
    if len(banco) < 20:
        flash("No hay suficientes preguntas en el banco (mínimo 20).", "danger")
        return redirect(url_for("dashboard"))
    seleccion = random.sample(banco, 20)
    examen_data = {
        "nombre": "Examen Aleatorio",
        "descripcion": "20 preguntas seleccionadas aleatoriamente.",
        "tiempo": 20,
        "preguntas": [str(p["_id"]) for p in seleccion]
    }
    return render_template("examen_aleatorio.html", examen=examen_data, preguntas=seleccion)

@app.route("/examenes/comenzar/<id>")
def comenzar_examen(id):
    if "usuario" not in session:
        return redirect(url_for("login"))
    bloqueo = bloqueos_examenes.find_one({
        "usuario_id": ObjectId(session["usuario"]),
        "examen_id": id
    })
    if bloqueo and bloqueo.get("bloqueado"):
        flash("Has sido bloqueado para realizar este examen por exceder el límite de advertencias.", "danger")
        return redirect(url_for("lista_examenes"))
    examen = examenes.find_one({"_id": ObjectId(id)})
    if not examen:
        flash("Examen no encontrado", "danger")
        return redirect(url_for("lista_examenes"))
    preguntas_examen = [preguntas.find_one({"_id": qid}) for qid in examen["preguntas"]]
    examen_data = {
        "id": str(examen["_id"]),
        "nombre": examen["nombre"],
        "descripcion": examen["descripcion"],
        "tiempo": examen["tiempo"],
        "preguntas": preguntas_examen
    }
    return render_template("examen_tomar.html", examen=examen_data)

@app.route("/examenes/guardar_respuestas", methods=["POST"])
def guardar_respuestas():
    if "usuario" not in session:
        return redirect(url_for("login"))
    examen_id = request.form.get("examen_id", "aleatorio")
    tiempo_inicio_raw = request.form.get("tiempo_inicio")
    tiempo_fin_raw = request.form.get("tiempo_fin")
    try:
        tiempo_inicio = datetime.fromisoformat(tiempo_inicio_raw) if tiempo_inicio_raw else datetime.utcnow()
    except ValueError:
        tiempo_inicio = datetime.utcnow()
    try:
        tiempo_fin = datetime.fromisoformat(tiempo_fin_raw) if tiempo_fin_raw else datetime.utcnow()
    except ValueError:
        tiempo_fin = datetime.utcnow()
    respuestas = {}
    for key, value in request.form.items():
        if key.startswith("respuesta_"):
            respuestas[key.replace("respuesta_", "")] = value
    puntaje = 0
    examen_obj = None
    total = 0
    if examen_id != "aleatorio":
        try:
            examen_obj = examenes.find_one({"_id": ObjectId(examen_id)})
        except Exception:
            examen_obj = None
        if not examen_obj:
            flash("Examen no encontrado", "danger")
            return redirect(url_for("dashboard"))
        total = len(examen_obj["preguntas"])
    else:
        total = len(respuestas)
    wrong_questions = []
    for pid, seleccion in respuestas.items():
        try:
            pregunta = preguntas.find_one({"_id": ObjectId(pid)})
        except Exception:
            pregunta = None
        if not pregunta:
            continue
        correcta_idx = int(pregunta["correcta"]) - 1 if pregunta.get("correcta") and str(pregunta["correcta"]).isdigit() else None
        correcta_text = pregunta["opciones"][correcta_idx] if correcta_idx is not None and 0 <= correcta_idx < len(pregunta["opciones"]) else "Desconocida"
        seleccion_text = "No respondida"
        if seleccion and str(seleccion).isdigit():
            idx = int(seleccion) - 1
            if 0 <= idx < len(pregunta["opciones"]):
                seleccion_text = pregunta["opciones"][idx]
        if str(pregunta["correcta"]) == str(seleccion):
            puntaje += 1
        else:
            wrong_questions.append({
                "texto": pregunta["texto"],
                "correcta": correcta_text,
                "seleccionada": seleccion_text,
                "opciones": pregunta["opciones"]
            })
    resultado = {
        "usuario_id": ObjectId(session["usuario"]),
        "examen_id": ObjectId(examen_id) if examen_id != "aleatorio" else "aleatorio",
        "respuestas": respuestas,
        "puntaje": puntaje,
        "total": total,
        "porcentaje": round((puntaje / total) * 100, 2) if total > 0 else 0,
        "tiempo_inicio": tiempo_inicio,
        "tiempo_fin": tiempo_fin,
        "fecha": datetime.utcnow(),
        "anti_trampas": int(request.form.get("anti_trampas", 0)),
        "wrong_questions": wrong_questions
    }
    resultados.insert_one(resultado)
    return render_template(
        "resultado_final.html",
        resultado=resultado,
        wrong_questions=wrong_questions,
        nombre=session.get("nombre", "Estudiante")
    )

@app.route("/resultados")
def lista_resultados():
    if "usuario" not in session:
        return redirect(url_for("login"))
    lista = list(resultados.find({"usuario_id": ObjectId(session["usuario"])}))
    return render_template("resultados.html", resultados=lista, nombre=session.get("nombre", "Estudiante"))

@app.route("/api/control_ventana", methods=["POST"])
def control_ventana():
    if "usuario" not in session:
        return jsonify({"status": "error"}), 401
    evento = request.json.get("evento")
    examen_id = request.json.get("examen_id", "aleatorio")
    control_eventos.insert_one({
        "usuario_id": ObjectId(session["usuario"]),
        "evento": evento,
        "examen_id": examen_id,
        "timestamp": datetime.utcnow()
    })
    response = {"status": "ok", "warning_count": 0, "blocked": False}
    if evento in ["ocultar_pantalla", "salida", "perdio_foco"]:
        registro = bloqueos_examenes.find_one({
            "usuario_id": ObjectId(session["usuario"]),
            "examen_id": examen_id
        })
        warnings = registro["warnings"] if registro and registro.get("warnings") else 0
        warnings += 1
        blocked = warnings >= 3
        bloqueos_examenes.update_one(
            {"usuario_id": ObjectId(session["usuario"]), "examen_id": examen_id},
            {"$set": {"warnings": warnings, "bloqueado": blocked}},
            upsert=True
        )
        response["warning_count"] = warnings
        response["blocked"] = blocked
    return jsonify(response)

if __name__ == "__main__":
    app.run(debug=True)
