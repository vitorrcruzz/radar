"""Regressões de troca de IP sem acesso aos computadores dos agentes."""
import os
import unittest
import uuid
from unittest.mock import patch

from flask import Flask
from sqlalchemy.exc import IntegrityError

from backend.database import db
from backend.models import Agente, CampoManualDispositivo, ColetaAgente, Dispositivo, SoftwareInstalado
from backend.routes.agents import agents_bp, _hash_token


class AgentIPConflictTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {'RADAR_AGENT_ALLOWED_NETWORKS': '192.168.1.0/24'})
        self.env.start()
        self.app = Flask(__name__)
        self.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://', SQLALCHEMY_TRACK_MODIFICATIONS=False)
        db.init_app(self.app)
        self.app.register_blueprint(agents_bp, url_prefix='/api')
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.create_all()
        self.device = Dispositivo(ip='192.168.1.44', hostname='mini-note', tipo='Computador')
        self.ghost = Dispositivo(ip='192.168.1.66', tipo='Host sem coleta', interfaces=0)
        db.session.add_all([self.device, self.ghost])
        db.session.flush()
        self.device_id, self.ghost_id = self.device.id, self.ghost.id
        self.agent = Agente(id=str(uuid.uuid4()), dispositivo_id=self.device.id,
                            token_hash=_hash_token('test-secret'), plataforma='win32', ativo=True)
        db.session.add(self.agent)
        db.session.add(CampoManualDispositivo(dispositivo_id=self.device.id, campo='modelo', valor='Modelo manual'))
        db.session.commit()
        self.payload = {'agent_id': self.agent.id, 'plataforma': 'win32',
                        'dados': {'ip': '192.168.1.66', 'hostname': 'mini-note'}}

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.env.stop()

    def send(self, token='test-secret', origin='192.168.1.66'):
        return self.app.test_client().post('/api/agentes/inventario', json=self.payload,
            headers={'Authorization': 'Bearer ' + token}, environ_base={'REMOTE_ADDR': origin})

    def test_reclaims_empty_host_and_is_idempotent(self):
        agent_id = self.agent.id
        for _ in range(2):
            self.assertEqual(self.send().status_code, 200)
        self.assertIsNone(db.session.get(Dispositivo, self.ghost_id))
        self.assertEqual(db.session.get(Dispositivo, self.device_id).ip, '192.168.1.66')
        self.assertEqual(db.session.get(Agente, agent_id).dispositivo_id, self.device_id)
        self.assertEqual(CampoManualDispositivo.query.count(), 1)
        self.assertEqual(ColetaAgente.query.count(), 2)

    def test_preserves_real_device(self):
        self.ghost.tipo = 'Computador'
        self.ghost.hostname = 'outro-computador'
        db.session.commit()
        self.assertEqual(self.send().status_code, 409)
        self.assertEqual(self.device.ip, '192.168.1.44')
        self.assertIsNotNone(db.session.get(Dispositivo, self.ghost_id))
        self.assertEqual(ColetaAgente.query.count(), 0)

    def test_preserves_manual_data_on_placeholder(self):
        db.session.add(CampoManualDispositivo(dispositivo_id=self.ghost.id, campo='contato', valor='TI'))
        db.session.commit()
        self.assertEqual(self.send().status_code, 409)
        self.assertEqual(CampoManualDispositivo.query.count(), 2)

    def test_preserves_software_on_placeholder(self):
        db.session.add(SoftwareInstalado(dispositivo_id=self.ghost.id, nome='CAD'))
        db.session.commit()
        self.assertEqual(self.send().status_code, 409)
        self.assertEqual(SoftwareInstalado.query.count(), 1)

    def test_preserves_agent_on_placeholder(self):
        db.session.add(Agente(id=str(uuid.uuid4()), dispositivo_id=self.ghost.id,
                            token_hash=_hash_token('other'), plataforma='win32', ativo=True))
        db.session.commit()
        self.assertEqual(self.send().status_code, 409)
        self.assertEqual(Agente.query.count(), 2)

    def test_unauthenticated_and_external_requests_cannot_reclaim_ip(self):
        self.assertEqual(self.send(token='invalid').status_code, 401)
        self.assertEqual(self.send(origin='10.36.154.211').status_code, 403)
        self.assertIsNotNone(db.session.get(Dispositivo, self.ghost_id))
        self.assertEqual(self.device.ip, '192.168.1.44')

    def test_commit_conflict_rolls_back_deleted_placeholder(self):
        with patch.object(db.session, 'commit', side_effect=IntegrityError('simulated', {}, Exception())):
            self.assertEqual(self.send().status_code, 409)
        self.assertIsNotNone(db.session.get(Dispositivo, self.ghost_id))
        self.assertEqual(db.session.get(Dispositivo, self.device_id).ip, '192.168.1.44')
        self.assertEqual(ColetaAgente.query.count(), 0)


class DHCPIdentityTests(unittest.TestCase):
    setUp = AgentIPConflictTests.setUp
    tearDown = AgentIPConflictTests.tearDown
    send = AgentIPConflictTests.send

    def test_authenticated_hardware_reclaims_stale_real_occupant(self):
        from datetime import datetime, timedelta
        from backend.models import HistoricoIP
        self.device.serial_number = '6582CN4'
        self.ghost.tipo = 'Computador'
        self.ghost.hostname = 'outro'
        self.ghost.serial_number = '1B6SCG4'
        self.ghost.ultima_vez = datetime.now() - timedelta(days=1)
        db.session.add(SoftwareInstalado(dispositivo_id=self.ghost.id, nome='CAD'))
        db.session.commit()
        self.payload['dados']['serial_number'] = '6582cn4'
        self.assertEqual(self.send().status_code, 200)
        self.assertIsNone(db.session.get(Dispositivo, self.ghost_id).ip)
        self.assertEqual(db.session.get(Dispositivo, self.ghost_id).status, 'offline')
        self.assertEqual(SoftwareInstalado.query.count(), 1)
        self.assertEqual(HistoricoIP.query.count(), 2)
        self.assertEqual(db.session.get(Dispositivo, self.ghost_id).to_dict()['ip'], 'Sem IP atual')

    def test_recent_real_occupant_cannot_be_displaced(self):
        self.device.serial_number = '6582CN4'
        self.ghost.tipo = 'Computador'
        self.ghost.serial_number = '1B6SCG4'
        db.session.commit()
        self.payload['dados']['serial_number'] = '6582CN4'
        self.assertEqual(self.send().status_code, 409)
        self.assertEqual(db.session.get(Dispositivo, self.ghost_id).ip, '192.168.1.66')

    def test_nat_origin_cannot_displace_real_device(self):
        from datetime import datetime, timedelta
        self.device.serial_number = '6582CN4'
        self.ghost.tipo = 'Computador'
        self.ghost.ultima_vez = datetime.now() - timedelta(days=1)
        db.session.commit()
        self.payload['dados']['serial_number'] = '6582CN4'
        self.assertEqual(self.send(origin='192.168.1.35').status_code, 409)

    def test_serial_recognizes_changed_network_adapter(self):
        from backend.device_identity import buscar_por_identidade
        self.device.serial_number = '6582CN4'
        self.device.mac_address = '60-C7-27-0F-5B-C7'
        db.session.commit()
        found = buscar_por_identidade({'serial_number':'6582cn4', 'mac_address':'B8:1E:A4:AA:4C:63'})
        self.assertEqual(found.id, self.device_id)

    def test_generic_serial_and_invalid_mac_do_not_match(self):
        from backend.device_identity import buscar_por_identidade, normalizar_mac
        self.device.serial_number = 'To Be Filled By O.E.M.'
        db.session.commit()
        self.assertIsNone(buscar_por_identidade({'serial_number':'To Be Filled By O.E.M.'}))
        self.assertIsNone(normalizar_mac('00:00:00:00:00:00'))
        self.assertIsNone(normalizar_mac('FF:FF:FF:FF:FF:FF'))

    def test_duplicate_hardware_is_ambiguous(self):
        from backend.device_identity import buscar_por_identidade
        self.device.serial_number = self.ghost.serial_number = '6582CN4'
        db.session.commit()
        with self.assertRaises(ValueError):
            buscar_por_identidade({'serial_number':'6582CN4'})

    def test_snmp_moves_existing_device_preserving_manual_fields(self):
        import sys
        import types
        from backend.routes.scan import executar_varredura
        self.device.mac_address = 'D8-44-89-CA-05-8E'
        db.session.commit()
        scanner = types.ModuleType('collector.snmp_scanner')
        scanner.escanear_rede = lambda *args: [{'ip':'192.168.1.66', 'status':'online',
            'dados':{'mac_address':'d8:44:89:ca:05:8e', 'tipo':'Roteador', 'hostname':'ER605'}}]
        wmi = types.ModuleType('collector.wmi_collector')
        wmi.credenciais_configuradas = lambda: False
        wmi.coletar_dados_windows = lambda *args: {}
        with patch.dict(sys.modules, {'collector.snmp_scanner':scanner, 'collector.wmi_collector':wmi}), \
             patch.dict(os.environ, {'SCAN_NETWORK':'192.168.1.0/24','DISCOVERY_ICMP_ENABLED':'false'}):
            executar_varredura(self.app)
        self.assertEqual(db.session.get(Dispositivo,self.device_id).ip, '192.168.1.66')
        self.assertEqual(CampoManualDispositivo.query.count(), 1)
        self.assertIsNone(db.session.get(Dispositivo,self.ghost_id))

    def test_snmp_does_not_overwrite_another_serial_at_same_ip(self):
        from backend.device_identity import validar_identidade_no_ip
        self.device.serial_number = '6582CN4'
        with self.assertRaises(ValueError):
            validar_identidade_no_ip(self.device, {'serial_number':'1B6SCG4'})


if __name__ == '__main__':
    unittest.main()
