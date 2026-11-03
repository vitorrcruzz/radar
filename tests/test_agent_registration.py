"""Registro de agentes novos e aproveitamento seguro de inventário existente."""
import os
import unittest
import uuid
from unittest.mock import patch
import test_agent_ip_conflicts as fixtures
from backend.database import db
from backend.models import Agente, ColetaAgente, Dispositivo


class AgentRegistrationTests(unittest.TestCase):
    setUp = fixtures.AgentIPConflictTests.setUp
    tearDown = fixtures.AgentIPConflictTests.tearDown

    def register(self, ip='192.168.1.77', serial='7XH7VQ3'):
        self.new_id = str(uuid.uuid4())
        payload = {'agent_id':self.new_id, 'plataforma':'win32',
                   'dados':{'ip':ip, 'hostname':'DELL-G15', 'serial_number':serial}}
        with patch.dict(os.environ, {'RADAR_AGENT_ENROLLMENT_TOKEN':'test-bootstrap'}):
            return self.app.test_client().post('/api/agentes/registrar', json=payload,
                headers={'Authorization':'Bearer test-bootstrap'}, environ_base={'REMOTE_ADDR':ip})

    def test_first_registration_and_subsequent_collection(self):
        response = self.register()
        self.assertEqual(response.status_code, 201)
        agent = db.session.get(Agente,self.new_id)
        self.assertEqual(agent.dispositivo.serial_number, '7XH7VQ3')
        self.assertEqual(agent.dispositivo.ip, '192.168.1.77')
        response = self.app.test_client().post('/api/agentes/inventario',
            json={'agent_id':self.new_id, 'plataforma':'win32', 'dados':{'ip':'192.168.1.77'}},
            headers={'Authorization':'Bearer '+response.json['token']},
            environ_base={'REMOTE_ADDR':'192.168.1.77'})
        self.assertEqual(response.status_code,200)
        self.assertEqual(ColetaAgente.query.count(),2)

    def test_registration_reuses_empty_host(self):
        response = self.register(ip='192.168.1.66')
        self.assertEqual(response.status_code,201)
        self.assertEqual(db.session.get(Agente,self.new_id).dispositivo_id,self.ghost_id)

    def test_registration_reuses_snmp_identity_with_changed_ip(self):
        self.ghost.serial_number='7XH7VQ3'
        self.ghost.tipo='Computador'
        db.session.commit()
        response = self.register()
        self.assertEqual(response.status_code,201)
        self.assertEqual(db.session.get(Agente,self.new_id).dispositivo_id,self.ghost_id)
        self.assertEqual(db.session.get(Dispositivo,self.ghost_id).ip,'192.168.1.77')

    def test_registration_cannot_take_over_another_agent(self):
        self.device.serial_number='7XH7VQ3'
        db.session.commit()
        response = self.register()
        self.assertEqual(response.status_code,409)
        self.assertIsNone(db.session.get(Agente,self.new_id))
