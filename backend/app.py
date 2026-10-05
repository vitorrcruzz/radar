import os
import sys

sys.path.insert(0, "/app")

from flask import Flask
from apscheduler.schedulers.background import BackgroundScheduler
from backend.database import db

def criar_app():
    app = Flask(__name__, template_folder="templates", static_folder="static")

    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:////app/database/inventario.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = "tcc-fatec-osasco-2026"

    db.init_app(app)

    from backend.routes.devices   import devices_bp
    from backend.routes.scan      import scan_bp
    from backend.routes.export    import export_bp
    from backend.routes.dashboard import dashboard_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(devices_bp,  url_prefix="/api")
    app.register_blueprint(scan_bp,     url_prefix="/api")
    app.register_blueprint(export_bp,   url_prefix="/api")

    with app.app_context():
        db.create_all()
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
    try:
        app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
    finally:
        scheduler.shutdown()