from datetime import datetime, date
from backend.database import db

class Dispositivo(db.Model):
    __tablename__ = "dispositivos"

    id               = db.Column(db.Integer, primary_key=True)
    ip               = db.Column(db.String(15), unique=True, nullable=False)
    hostname         = db.Column(db.String(100))
    tipo             = db.Column(db.String(50))
    modelo           = db.Column(db.String(150))
    sistema_op       = db.Column(db.String(100))
    armazenamento    = db.Column(db.String(50))
    memoria          = db.Column(db.String(50))
    processador      = db.Column(db.String(100))
    mac_address      = db.Column(db.String(17))
    serial_number    = db.Column(db.String(50))
    descricao        = db.Column(db.Text)
    localizacao      = db.Column(db.String(200))
    contato          = db.Column(db.String(200))
    interfaces       = db.Column(db.Integer)
    uptime           = db.Column(db.String(50))
    status           = db.Column(db.String(10), default="offline")
    licenca_software = db.Column(db.String(100))
    licenca_expira   = db.Column(db.Date)
    ultima_vez       = db.Column(db.DateTime, default=datetime.now)
    criado_em        = db.Column(db.DateTime, default=datetime.now)

    def dias_para_expirar(self):
        if self.licenca_expira is None:
            return None
        delta = (self.licenca_expira - date.today()).days
        return delta

    def status_licenca(self):
        dias = self.dias_para_expirar()
        if dias is None:
            return "sem-licenca"
        if dias < 0:
            return "expirada"
        if dias <= 30:
            return "critica"
        if dias <= 90:
            return "atencao"
        return "ok"

    def to_dict(self):
        dias = self.dias_para_expirar()
        return {
            "id":               self.id,
            "ip":               self.ip,
            "hostname":         self.hostname         or "—",
            "tipo":             self.tipo             or "Desconhecido",
            "modelo":           self.modelo           or "—",
            "sistema_op":       self.sistema_op       or "—",
            "armazenamento":    self.armazenamento    or "—",
            "memoria":          self.memoria          or "—",
            "processador":      self.processador      or "—",
            "mac_address":      self.mac_address       or "—",
            "serial_number":    self.serial_number     or "—",
            "descricao":        self.descricao        or "—",
            "localizacao":      self.localizacao      or "—",
            "contato":          self.contato          or "—",
            "interfaces":       self.interfaces,
            "uptime":           self.uptime           or "—",
            "status":           self.status,
            "licenca_software": self.licenca_software or "—",
            "licenca_expira":   self.licenca_expira.strftime("%d/%m/%Y") if self.licenca_expira else "—",
            "dias_para_expirar": dias,
            "status_licenca":   self.status_licenca(),
            "ultima_vez":       self.ultima_vez.strftime("%d/%m/%Y %H:%M:%S") if self.ultima_vez else "—",
            "criado_em":        self.criado_em.strftime("%d/%m/%Y %H:%M:%S") if self.criado_em else "—",
        }


class HistoricoVarredura(db.Model):
    __tablename__ = "historico_varreduras"

    id              = db.Column(db.Integer, primary_key=True)
    iniciado_em     = db.Column(db.DateTime, default=datetime.now)
    finalizado_em   = db.Column(db.DateTime)
    total_escaneado = db.Column(db.Integer, default=0)
    total_online    = db.Column(db.Integer, default=0)
    total_offline   = db.Column(db.Integer, default=0)
    disparado_por   = db.Column(db.String(20), default="manual")

    def to_dict(self):
        return {
            "id":              self.id,
            "iniciado_em":     self.iniciado_em.strftime("%d/%m/%Y %H:%M:%S") if self.iniciado_em else "—",
            "finalizado_em":   self.finalizado_em.strftime("%d/%m/%Y %H:%M:%S") if self.finalizado_em else "—",
            "total_escaneado": self.total_escaneado,
            "total_online":    self.total_online,
            "total_offline":   self.total_offline,
            "disparado_por":   self.disparado_por,
        }