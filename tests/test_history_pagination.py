"""Garante respostas pequenas mesmo com milhares de varreduras."""
from datetime import datetime, timedelta
import unittest
from flask import Flask
from sqlalchemy import event
from backend.database import db
from backend.models import HistoricoVarredura
from backend.routes.devices import devices_bp


class HistoryPaginationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = Flask(__name__)
        cls.app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI='sqlite://')
        db.init_app(cls.app)
        cls.app.register_blueprint(devices_bp, url_prefix='/api')
        cls.ctx = cls.app.app_context()
        cls.ctx.push()
        db.create_all()
        base = datetime(2026, 10, 1)
        db.session.bulk_insert_mappings(HistoricoVarredura, [
            {'id':i, 'iniciado_em':base+timedelta(minutes=i),
             'total_escaneado':18, 'total_online':i % 19, 'total_offline':18-i % 19,
             'disparado_por':'manual' if i % 2 else 'automatico'}
            for i in range(1, 4006)
        ])
        db.session.commit()

    @classmethod
    def tearDownClass(cls):
        db.session.remove()
        db.drop_all()
        cls.ctx.pop()

    def get(self, params=None, endpoint='/api/historico'):
        result = self.app.test_client().get(endpoint, query_string=params)
        self.assertEqual(result.status_code, 200)
        return result.json

    def test_default_page_is_limited_in_database(self):
        queries = []
        def capture(conn, cursor, statement, parameters, context, executemany):
            queries.append(statement)
        event.listen(db.engine, 'before_cursor_execute', capture)
        try:
            result = self.get()
        finally:
            event.remove(db.engine, 'before_cursor_execute', capture)
        self.assertEqual(result['recordsTotal'], 4005)
        self.assertEqual(len(result['data']), 15)
        self.assertEqual([r['id'] for r in result['data']], list(range(4005,3990,-1)))
        self.assertTrue(any('LIMIT' in sql.upper() for sql in queries))

    def test_next_page_has_distinct_records_and_draw(self):
        result = self.get({'start':15, 'length':15, 'draw':3})
        self.assertEqual(result['draw'], 3)
        self.assertEqual([r['id'] for r in result['data']], list(range(3990,3975,-1)))

    def test_request_cannot_download_all_records(self):
        for length in [-1, 0, 100000, 'invalid']:
            result = self.get({'length':length})
            self.assertLessEqual(len(result['data']), 50)

    def test_search_and_sort_are_applied_before_pagination(self):
        result = self.get({'search[value]':'manual', 'order[0][column]':0,
                           'order[0][dir]':'asc', 'length':10})
        self.assertEqual(result['recordsTotal'], 4005)
        self.assertEqual(result['recordsFiltered'], 2003)
        self.assertEqual([r['id'] for r in result['data']], list(range(1,21,2)))

    def test_date_and_accented_origin_search(self):
        result = self.get({'search[value]':'01/10/2026'})
        self.assertEqual(result['recordsFiltered'],1439)
        result = self.get({'search[value]':'Automático'})
        self.assertEqual(result['recordsFiltered'],2002)

    def test_empty_and_out_of_range(self):
        self.assertEqual(self.get({'start':9000})['data'], [])
        result = self.get({'search[value]':'%_nao_existe'})
        self.assertEqual(result['recordsFiltered'],0)
        self.assertEqual(result['data'],[])

    def test_invalid_order_and_draw_use_safe_defaults(self):
        result = self.get({'draw':'<script>', 'start':-7, 'order[0][column]':999,
                           'order[0][dir]':'DROP TABLE historico_varreduras'})
        self.assertEqual(result['draw'],0)
        self.assertEqual(result['data'][0]['id'],4005)

    def test_chart_always_returns_only_ten_recent_records(self):
        result = self.get({'length':999999}, '/api/historico/recentes')
        self.assertEqual([r['id'] for r in result],list(range(4005,3995,-1)))
