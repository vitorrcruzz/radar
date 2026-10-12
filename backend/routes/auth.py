from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from backend.auth import usuario_atual
from backend.database import db
from backend.models import Usuario

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if usuario_atual():
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        usuario = Usuario.query.filter_by(email=email, ativo=True).first()
        if usuario is None or not usuario.verificar_senha(senha):
            flash("E-mail ou senha inválidos.", "danger")
            return render_template("login.html"), 401

        session.clear()
        session["usuario_id"] = usuario.id
        session.permanent = True
        return redirect(url_for("dashboard.index"))

    return render_template("login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("auth.login"))
