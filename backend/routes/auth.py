import hmac
import secrets

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError

from backend.auth import usuario_atual
from backend.database import db
from backend.models import Usuario

auth_bp = Blueprint("auth", __name__)


def _token_csrf():
    token = session.get("csrf_token")
    if not token:
        token = secrets.token_urlsafe(32)
        session["csrf_token"] = token
    return token


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


@auth_bp.route("/usuarios", methods=["GET", "POST"])
def usuarios():
    administrador = usuario_atual()
    if administrador is None or administrador.perfil != "admin":
        abort(403)

    if request.method == "POST":
        token_enviado = request.form.get("csrf_token", "")
        token_sessao = session.get("csrf_token", "")
        if not token_sessao or not hmac.compare_digest(token_enviado, token_sessao):
            abort(400, "Sessão expirada. Atualize a página e tente novamente.")

        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        perfil = request.form.get("perfil", "usuario")
        senha = request.form.get("senha", "")
        confirmacao = request.form.get("confirmacao_senha", "")

        if not nome or len(nome) > 120:
            flash("Informe um nome com até 120 caracteres.", "danger")
        elif not email or len(email) > 254 or "@" not in email:
            flash("Informe um e-mail válido.", "danger")
        elif perfil not in {"admin", "usuario"}:
            flash("Selecione um perfil válido.", "danger")
        elif len(senha) < 12:
            flash("A senha deve ter pelo menos 12 caracteres.", "danger")
        elif senha != confirmacao:
            flash("A confirmação da senha não confere.", "danger")
        else:
            usuario = Usuario(nome=nome, email=email, perfil=perfil, ativo=True)
            usuario.definir_senha(senha)
            db.session.add(usuario)
            try:
                db.session.commit()
            except IntegrityError:
                db.session.rollback()
                flash("Já existe uma conta cadastrada com esse e-mail.", "warning")
            else:
                flash("Conta criada e salva com sucesso.", "success")
                return redirect(url_for("auth.usuarios"))

    contas = Usuario.query.order_by(Usuario.nome.asc(), Usuario.email.asc()).all()
    return render_template("usuarios.html", contas=contas, csrf_token=_token_csrf())
