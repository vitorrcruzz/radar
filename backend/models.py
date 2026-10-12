from datetime import datetime, date
from werkzeug.security import check_password_hash, generate_password_hash
from backend.database import db


class Usuario(db.Model):
    __tablename__ = "usuarios"

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(254), unique=True, nullable=False, index=True)
    senha_hash = db.Column(db.String(256), nullable=False)
    perfil = db.Column(db.String(20), nullable=False, default="usuario")
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)

    def definir_senha(self, senha):
        self.senha_hash = generate_password_hash(senha)

    def verificar_senha(self, senha):
        return check_password_hash(self.senha_hash, senha)

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
    campos_manuais   = db.relationship(
        "CampoManualDispositivo",
        back_populates="dispositivo",
        cascade="all, delete-orphan",
        lazy="select",
    )

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
        dados = {
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
        dados["fontes_manuais"] = []
        for campo_manual in self.campos_manuais:
            dados[campo_manual.campo] = campo_manual.valor or "—"
            dados["fontes_manuais"].append(campo_manual.campo)
        return dados


class CampoManualDispositivo(db.Model):
    __tablename__ = "campos_manuais_dispositivo"

    id             = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey("dispositivos.id"), nullable=False)
    campo          = db.Column(db.String(50), nullable=False)
    valor          = db.Column(db.Text)
    atualizado_em  = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

    dispositivo = db.relationship("Dispositivo", back_populates="campos_manuais")
    __table_args__ = (db.UniqueConstraint("dispositivo_id", "campo"),)


class Agente(db.Model):
    __tablename__ = "agentes"

    id             = db.Column(db.String(36), primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey("dispositivos.id"), unique=True, nullable=False)
    token_hash     = db.Column(db.String(64), nullable=False)
    plataforma     = db.Column(db.String(40), nullable=False)
    ativo          = db.Column(db.Boolean, default=True, nullable=False)
    registrado_em = db.Column(db.DateTime, default=datetime.now, nullable=False)
    ultima_coleta  = db.Column(db.DateTime)

    dispositivo = db.relationship("Dispositivo")


class ColetaAgente(db.Model):
    __tablename__ = "coletas_agente"

    id          = db.Column(db.Integer, primary_key=True)
    agente_id   = db.Column(db.String(36), db.ForeignKey("agentes.id"), nullable=False, index=True)
    recebido_em = db.Column(db.DateTime, default=datetime.now, nullable=False, index=True)
    dados_json  = db.Column(db.Text, nullable=False)

    agente = db.relationship("Agente")


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
