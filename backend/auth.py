from functools import wraps

from flask import jsonify, session

from backend.database import db
from backend.models import Usuario


def usuario_atual():
    usuario_id = session.get("usuario_id")
    return db_get_usuario(usuario_id) if usuario_id else None


def db_get_usuario(usuario_id):
    return Usuario.query.filter_by(id=usuario_id, ativo=True).first()


def perfil_requerido(perfil):
    def decorar(funcao):
        @wraps(funcao)
        def protegida(*args, **kwargs):
            usuario = usuario_atual()
            if usuario is None:
                return jsonify({"erro": "Autenticação necessária."}), 401
            if usuario.perfil != perfil:
                return jsonify({"erro": "Ação permitida somente ao administrador."}), 403
            return funcao(*args, **kwargs)
        return protegida
    return decorar
