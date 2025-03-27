from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
from werkzeug.utils import secure_filename
import os
import uuid
from datetime import timedelta, datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

# Configuración de Flask
app = Flask(__name__)
app.secret_key = "clave_secreta"
app.permanent_session_lifetime = timedelta(days=1)

# Conexión a MongoDB
client = MongoClient(MONGO_URI)
db = client['recetas_db']
usuarios = db['usuarios']
recetas = db['recetas']

# Crear carpeta de uploads si no existe
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


@app.route("/")
def index():
    recetas_lista = list(recetas.find())
    return render_template("index.html", recetas=recetas_lista)


@app.route("/calificar/<receta_id>", methods=["POST"])
def calificar(receta_id):
    if "usuario" not in session:
        return redirect("/login")
    try:
        puntuacion = int(request.form['puntuacion'])
    except ValueError:
        flash("Puntuación inválida")
        return redirect(url_for('ver_receta', receta_id=receta_id))

    receta = recetas.find_one({"_id": ObjectId(receta_id)})
    if receta:
        recetas.update_one(
            {"_id": ObjectId(receta_id)},
            {"$push": {"calificaciones": {"usuario": session['usuario'], "puntuacion": puntuacion}}}
        )
        flash("Calificación enviada")
    return redirect(url_for('ver_receta', receta_id=receta_id))


@app.route("/receta/editar/<receta_id>", methods=["GET", "POST"])
def editar_receta(receta_id):
    if "usuario" not in session:
        return redirect("/login")
    
    receta = recetas.find_one({"_id": ObjectId(receta_id)})
    if receta and receta['autor'] == session['usuario']:
        if request.method == "POST":
            titulo = request.form['titulo']
            descripcion = request.form['descripcion']
            recetas.update_one(
                {"_id": ObjectId(receta_id)},
                {"$set": {"titulo": titulo, "descripcion": descripcion}}
            )
            flash("Receta actualizada")
            return redirect(url_for('ver_receta', receta_id=receta_id))
        return render_template("editar_receta.html", receta=receta)
    return redirect("/")


@app.route("/receta/eliminar/<receta_id>", methods=["POST"])
def eliminar_receta(receta_id):
    if "usuario" not in session:
        return redirect("/login")
    
    receta = recetas.find_one({"_id": ObjectId(receta_id)})
    if receta and receta['autor'] == session['usuario']:
        recetas.delete_one({"_id": ObjectId(receta_id)})
        flash("Receta eliminada")
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form['usuario']
        email = request.form['email']
        password = generate_password_hash(request.form['password'])
        
        if usuarios.find_one({"$or": [{"usuario": user}, {"email": email}]}):
            flash("El usuario o email ya existe")
            return redirect("/register")

        usuarios.insert_one({"usuario": user, "email": email, "password": password})
        flash("Registro exitoso")
        return redirect("/login")

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form['usuario']
        password = request.form['password']
        usuario = usuarios.find_one({"usuario": user})
        
        if usuario and check_password_hash(usuario['password'], password):
            session.permanent = True
            session['usuario'] = user
            return redirect(url_for('index'))
        else:
            flash("Usuario o contraseña incorrectos")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("usuario", None)
    return redirect("/")
    
@app.route("/receta/<receta_id>")
def ver_receta(receta_id):
    receta = recetas.find_one({"_id": ObjectId(receta_id)})
    if receta:
        return render_template("ver_receta.html", receta=receta)
    else:
        flash("Receta no encontrada")
        return redirect(url_for("index"))


@app.route("/receta/nueva", methods=["GET", "POST"])
def nueva_receta():
    if "usuario" not in session:
        return redirect("/login")

    if request.method == "POST":
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        foto = request.files.get('foto')
        video = request.files.get('video')

        # Generar nombres únicos para los archivos
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        foto_filename = None
        video_filename = None

        if foto and foto.filename:
            foto_filename = f"{UPLOAD_FOLDER}/{timestamp}_{uuid.uuid4().hex}_{secure_filename(foto.filename)}"
            foto.save(foto_filename)

        if video and video.filename:
            video_filename = f"{UPLOAD_FOLDER}/{timestamp}_{uuid.uuid4().hex}_{secure_filename(video.filename)}"
            video.save(video_filename)

        recetas.insert_one({
            "titulo": titulo,
            "descripcion": descripcion,
            "foto": foto_filename,
            "video": video_filename,
            "autor": session['usuario']
        })
        flash("Receta creada con éxito")
        return redirect("/")

    return render_template("recetas.html")


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
