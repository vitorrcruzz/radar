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
    rede             = db.Column(db.String(100))
    contato          = db.Column(db.String(200))
    interfaces       = db.Column(db.Integer)
    uptime           = db.Column(db.String(50))
    status           = db.Column(db.String(10), default="offline")
    licenca_software = db.Column(db.String(100))
    licenca_expira   = db.Column(db.Date)
    edicao_windows   = db.Column(db.String(100))
    status_ativacao_windows = db.Column(db.String(60))
    licenca_windows_expira = db.Column(db.Date)
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

    def to_dict(self, incluir_software=False):
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
            "rede":             self.rede             or "—",
            "contato":          self.contato          or "—",
            "interfaces":       self.interfaces,
            "uptime":           self.uptime           or "—",
            "status":           self.status,
            "licenca_software": self.licenca_software or "—",
            "licenca_expira":   self.licenca_expira.strftime("%d/%m/%Y") if self.licenca_expira else "—",
            "licenca_expira_iso": self.licenca_expira.isoformat() if self.licenca_expira else "",
            "dias_para_expirar": dias,
            "status_licenca":   self.status_licenca(),
            "edicao_windows":   self.edicao_windows or "—",
            "status_ativacao_windows": self.status_ativacao_windows or "Não coletado",
            "licenca_windows_expira": self.licenca_windows_expira.strftime("%d/%m/%Y") if self.licenca_windows_expira else "Sem expiração informada",
            "licenca_windows_expira_iso": self.licenca_windows_expira.isoformat() if self.licenca_windows_expira else "",
            "ultima_vez":       self.ultima_vez.strftime("%d/%m/%Y %H:%M:%S") if self.ultima_vez else "—",
            "criado_em":        self.criado_em.strftime("%d/%m/%Y %H:%M:%S") if self.criado_em else "—",
        }
        dados["fontes_manuais"] = []
        for campo_manual in self.campos_manuais:
            valor_manual = campo_manual.valor or "—"
            if campo_manual.campo == "licenca_windows_expira":
                try:
                    data_manual = date.fromisoformat(campo_manual.valor)
                    dados[campo_manual.campo] = data_manual.strftime("%d/%m/%Y")
                    dados["licenca_windows_expira_iso"] = data_manual.isoformat()
                except (TypeError, ValueError):
                    dados[campo_manual.campo] = valor_manual
                    dados["licenca_windows_expira_iso"] = ""
            elif campo_manual.campo == "interfaces":
                try:
                    dados[campo_manual.campo] = int(campo_manual.valor)
                except (TypeError, ValueError):
                    dados[campo_manual.campo] = valor_manual
            else:
                dados[campo_manual.campo] = valor_manual
            dados["fontes_manuais"].append(campo_manual.campo)
        if incluir_software:
            dados["softwares_instalados"] = [software.to_dict() for software in self.softwares_instalados]
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


class SoftwareInstalado(db.Model):
    __tablename__ = "softwares_instalados"

    id = db.Column(db.Integer, primary_key=True)
    dispositivo_id = db.Column(db.Integer, db.ForeignKey("dispositivos.id", ondelete="CASCADE"), nullable=False, index=True)
    nome = db.Column(db.String(150), nullable=False)
    fabricante = db.Column(db.String(120))
    versao = db.Column(db.String(80))
    tipo_licenca = db.Column(db.String(80))
    expira_em = db.Column(db.Date)
    observacao = db.Column(db.Text)
    criado_em = db.Column(db.DateTime, nullable=False, default=datetime.now)
    atualizado_em = db.Column(db.DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)

    dispositivo = db.relationship("Dispositivo", backref=db.backref("softwares_instalados", lazy="select"))

    def to_dict(self):
        return {
            "id": self.id,
            "nome": self.nome,
            "fabricante": self.fabricante or "",
            "versao": self.versao or "",
            "tipo_licenca": self.tipo_licenca or "",
            "expira_em": self.expira_em.isoformat() if self.expira_em else "",
            "observacao": self.observacao or "",
        }


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
