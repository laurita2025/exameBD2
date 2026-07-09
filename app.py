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

    tiempo_inicio = datetime.utcnow()
    tiempo_fin = datetime.utcnow()

    try:
        if request.form.get("tiempo_inicio"):
            tiempo_inicio = datetime.fromisoformat(request.form["tiempo_inicio"])
    except:
        pass

    try:
        if request.form.get("tiempo_fin"):
            tiempo_fin = datetime.fromisoformat(request.form["tiempo_fin"])
    except:
        pass

    respuestas = {}

    for key, value in request.form.items():
        if key.startswith("respuesta_"):
            respuestas[key.replace("respuesta_", "")] = value

    puntaje = 0
    total = 0
    wrong_questions = []

    # Buscar examen
    if examen_id != "aleatorio":

        examen = examenes.find_one({"_id": ObjectId(examen_id)})

        if not examen:
            flash("Examen no encontrado", "danger")
            return redirect(url_for("dashboard"))

        total = len(examen["preguntas"])

    else:

        total = len(respuestas)

    # Calificar examen
    for pid, seleccion in respuestas.items():

        pregunta = preguntas.find_one({"_id": ObjectId(pid)})

        if not pregunta:
            continue

        correcta = str(pregunta["correcta"])

        correcta_idx = int(correcta) - 1

        correcta_texto = pregunta["opciones"][correcta_idx]

        seleccion_texto = "No respondida"

        if seleccion.isdigit():

            idx = int(seleccion) - 1

            if 0 <= idx < len(pregunta["opciones"]):
                seleccion_texto = pregunta["opciones"][idx]

        if correcta == seleccion:

            puntaje += 1

        else:

            wrong_questions.append({

                "texto": pregunta["texto"],

                "correcta": correcta_texto,

                "seleccionada": seleccion_texto,

                "opciones": pregunta["opciones"]

            })

    # ====== CALCULAR RESULTADO ======

    porcentaje = round((puntaje / total) * 100, 2) if total else 0

    estado = "Aprobado" if porcentaje >= 61 else "Reprobado"

    advertencias = int(request.form.get("anti_trampas", 0))

    resultado = {

        "usuario_id": ObjectId(session["usuario"]),

        "examen_id": ObjectId(examen_id) if examen_id != "aleatorio" else "aleatorio",

        "respuestas": respuestas,

        "puntaje": puntaje,

        "total": total,

        "porcentaje": porcentaje,

        "estado": estado,

        "advertencias": advertencias,

        "anti_trampas": advertencias,

        "tiempo_inicio": tiempo_inicio,

        "tiempo_fin": tiempo_fin,

        "fecha": datetime.utcnow(),

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

    # ==========================
    # ADMINISTRADOR
    # ==========================
    if es_admin():

        lista = []

        for r in resultados.find().sort("fecha", -1):

            usuario = usuarios.find_one({"_id": ObjectId(r["usuario_id"])})

            lista.append({

                "_id": r["_id"],

                "nombre": usuario["nombre"] if usuario else "Desconocido",

                "fecha": r.get("fecha"),

                "puntaje": r.get("puntaje", 0),

                "total": r.get("total", 0),

                "porcentaje": r.get("porcentaje", 0),

                "estado": r.get(
                    "estado",
                    "Aprobado" if r.get("porcentaje", 0) >= 61 else "Reprobado"
                ),

                "advertencias": r.get(
                    "advertencias",
                    r.get("anti_trampas", 0)
                )

            })

        aprobados = sum(
            1 for r in lista if r["porcentaje"] >= 61
        )

        reprobados = len(lista) - aprobados

        incidencias = sum(
            1 for r in lista if r["advertencias"] > 0
        )

        return render_template(

            "resultados_admin.html",

            resultados=lista,

            aprobados=aprobados,

            reprobados=reprobados,

            incidencias=incidencias

        )

    # ==========================
    # ESTUDIANTE
    # ==========================

    lista = list(

        resultados.find(

            {"usuario_id": ObjectId(session["usuario"])}

        ).sort("fecha", -1)

    )

    return render_template(

        "resultados.html",

        resultados=lista,

        nombre=session.get("nombre", "Estudiante")

    )
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
