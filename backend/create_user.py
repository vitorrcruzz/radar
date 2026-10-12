"""Cria ou atualiza uma conta local do RADAR sem colocar senha em argumentos."""
import argparse
from getpass import getpass

from backend.app import criar_app
from backend.database import db
from backend.models import Usuario


def main():
    parser = argparse.ArgumentParser(description="Criar uma conta local do RADAR")
    parser.add_argument("--nome", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--perfil", choices=("admin", "usuario"), default="usuario")
    args = parser.parse_args()

    senha = getpass("Nova senha (mínimo 8 caracteres): ")
    confirmacao = getpass("Confirme a senha: ")
    if len(senha) < 8:
        parser.error("A senha precisa ter pelo menos 8 caracteres.")
    if senha != confirmacao:
        parser.error("As senhas não coincidem.")

    app = criar_app()
    with app.app_context():
        email = args.email.strip().lower()
        usuario = Usuario.query.filter_by(email=email).first()
        if usuario is None:
            usuario = Usuario(nome=args.nome.strip(), email=email, perfil=args.perfil)
            db.session.add(usuario)
        else:
            usuario.nome = args.nome.strip()
            usuario.perfil = args.perfil
            usuario.ativo = True
        usuario.definir_senha(senha)
        db.session.commit()
    print(f"Conta {args.perfil} salva para {email}.")


if __name__ == "__main__":
    main()
