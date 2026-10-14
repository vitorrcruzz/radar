import os
import secrets
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, request, session, url_for
from apscheduler.schedulers.background import BackgroundScheduler
from backend.database import db
from sqlalchemy import inspect, text

load_dotenv(PROJECT_ROOT / ".env")

def criar_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    database_path = Path(os.getenv("RADAR_DATABASE_PATH", PROJECT_ROOT / "database" / "inventario.db")).expanduser()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    sqlite_path = database_path.resolve().as_posix()
    app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{sqlite_path}"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = os.getenv("RADAR_SECRET_KEY") or secrets.token_urlsafe(32)
    app.config["PERMANENT_SESSION_LIFETIME"] = 60 * 60 * 8
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
    app.config["SESSION_COOKIE_SECURE"] = os.getenv("RADAR_COOKIE_SECURE", "false").lower() == "true"

    db.init_app(app)

    from backend.routes.devices   import devices_bp
    from backend.routes.scan      import scan_bp
    from backend.routes.agents    import agents_bp
    from backend.routes.export    import export_bp
    from backend.routes.dashboard import dashboard_bp
    from backend.routes.auth      import auth_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(devices_bp,  url_prefix="/api")
    app.register_blueprint(scan_bp,     url_prefix="/api")
    app.register_blueprint(agents_bp,   url_prefix="/api")
    app.register_blueprint(export_bp,   url_prefix="/api")

    @app.context_processor
    def contexto_usuario():
        from backend.auth import usuario_atual
        return {"usuario_logado": usuario_atual()}

    @app.before_request
    def exigir_login():
        from backend.auth import usuario_atual
        endpoint = request.endpoint or ""
        if endpoint in {"auth.login", "auth.logout"} or endpoint.startswith("static"):
            return None
        # Agentes usam token individual por dispositivo, não a sessão do navegador.
        if endpoint in {"agents.registrar_agente", "agents.receber_inventario"}:
            return None
        if usuario_atual() is None:
            session.clear()
            if request.path.startswith("/api/"):
                return jsonify({"erro": "Autenticação necessária."}), 401
            return redirect(url_for("auth.login"))
        return None

    with app.app_context():
        db.create_all()
        colunas_dispositivo = {
            coluna["name"] for coluna in inspect(db.engine).get_columns("dispositivos")
        }
        if "rede" not in colunas_dispositivo:
            with db.engine.begin() as conexao:
                conexao.execute(text("ALTER TABLE dispositivos ADD COLUMN rede VARCHAR(100)"))
        # from backend.seed import popular_dispositivos_offline
        # popular_dispositivos_offline()

    return app

def iniciar_agendador(app):
    from backend.routes.scan import executar_varredura
    scheduler = BackgroundScheduler()
    interval  = int(os.getenv("SCAN_INTERVAL", 60))
    scheduler.add_job(
        func=executar_varredura,
        args=[app],
        trigger="interval",
        seconds=interval,
        id="varredura_automatica",
    )
    scheduler.start()
    return scheduler

if __name__ == "__main__":
    app = criar_app()
    scheduler = iniciar_agendador(app)
    cert_file = os.getenv("RADAR_TLS_CERT_FILE")
    key_file = os.getenv("RADAR_TLS_KEY_FILE")
    if bool(cert_file) != bool(key_file):
        scheduler.shutdown()
        raise RuntimeError("Configure RADAR_TLS_CERT_FILE e RADAR_TLS_KEY_FILE juntos.")
    ssl_context = (cert_file, key_file) if cert_file and key_file else None
    try:
        app.run(host="0.0.0.0", port=int(os.getenv("RADAR_PORT", "5000")), debug=False, use_reloader=False, ssl_context=ssl_context)
    finally:
        scheduler.shutdown()
