from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId
import os
from datetime import timedelta
import uuid
from datetime import datetime

app = Flask(__name__)
app.secret_key = "clave_secreta"
app.permanent_session_lifetime = timedelta(days=1)

# Conexión a MongoDB Atlas
client = MongoClient("mongodb+srv://somosutalianos:lBUPolF5VF0Lrhzd@cluster0.kmbazma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0")

db = client['recetas_db']
usuarios = db['usuarios']
recetas = db['recetas']

from dotenv import load_dotenv
load_dotenv()
import os

client = MongoClient(os.getenv("mongodb+srv://somosutalianos:lBUPolF5VF0Lrhzd@cluster0.kmbazma.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"))

@app.route("/")
def index():
    recetas_lista = list(recetas.find())
    return render_template("index.html", recetas=recetas_lista)

@app.route("/calificar/<receta_id>", methods=["POST"])
def calificar(receta_id):
    if "usuario" not in session:
        return redirect("/login")
    puntuacion = int(request.form['puntuacion'])
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
        if usuarios.find_one({"usuario": user}):
            flash("El usuario ya existe")
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

@app.route("/receta/nueva", methods=["GET", "POST"])
def nueva_receta():
    if "usuario" not in session:
        return redirect("/login")
    if request.method == "POST":
        titulo = request.form['titulo']
        descripcion = request.form['descripcion']
        foto = request.files['foto']
        video = request.files['video']
        
        # Generar nombres únicos para los archivos
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        foto_filename = f"{timestamp}_{uuid.uuid4().hex}_{foto.filename}"
        video_filename = f"{timestamp}_{uuid.uuid4().hex}_{video.filename}"
        
        ruta_foto = f"static/uploads/{foto_filename}"
        ruta_video = f"static/uploads/{video_filename}"
        
        foto.save(ruta_foto)
        video.save(ruta_video)
        
        recetas.insert_one({
            "titulo": titulo,
            "descripcion": descripcion,
            "foto": ruta_foto,
            "video": ruta_video,
            "autor": session['usuario']
        })
        return redirect("/")
    return render_template("recetas.html")
if __name__ == "__main__":
    if not os.path.exists("static/uploads"):
        os.makedirs("static/uploads")
    app.run(debug=True)