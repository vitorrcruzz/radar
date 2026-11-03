import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('release_ip', Path(__file__).resolve().parents[1] / 'scripts/release-stale-ip.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ReleaseStaleIPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / 'test.db'
        with sqlite3.connect(self.path) as c:
            c.executescript('''
CREATE TABLE dispositivos (
 id INTEGER PRIMARY KEY,
 ip VARCHAR(15) NOT NULL UNIQUE,
 hostname TEXT, serial_number TEXT, status TEXT, ultima_vez TEXT, rede TEXT,
 legado TEXT
);
CREATE INDEX hostname_idx ON dispositivos(hostname);
CREATE TABLE agentes (id TEXT PRIMARY KEY, dispositivo_id INTEGER REFERENCES dispositivos(id), ativo INTEGER, ultima_coleta TEXT);
CREATE TABLE historico (id INTEGER PRIMARY KEY, dispositivo_id INTEGER REFERENCES dispositivos(id), valor TEXT);
INSERT INTO dispositivos VALUES(89,'192.168.1.33','antigo','serial1','offline','2020-01-01','7º andar','preservar');
INSERT INTO dispositivos VALUES(82,'192.168.1.231','novo','serial2','offline','2020-01-01','7º andar','preservar');
INSERT INTO agentes VALUES('old',89,1,'2020-01-01');
INSERT INTO agentes VALUES('incoming',82,1,'2020-01-01');
INSERT INTO historico VALUES(1,89,'dados antigos');
''')

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, apply=False):
        return module.liberar(self.path, '192.168.1.33', 89, 'incoming', apply)

    def test_preview_does_not_change_database(self):
        before = self.path.read_bytes()
        self.call()
        self.assertEqual(before, self.path.read_bytes())

    def test_release_preserves_history_schema_and_allows_next_collection(self):
        result = self.call(True)
        self.assertTrue(Path(result['backup']).is_file())
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute('SELECT ip,legado FROM dispositivos WHERE id=89').fetchone(), (None,'preservar'))
            self.assertEqual(c.execute('SELECT count(*) FROM agentes').fetchone()[0], 2)
            self.assertEqual(c.execute('SELECT valor FROM historico').fetchone()[0], 'dados antigos')
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
            self.assertIsNotNone(c.execute("SELECT name FROM sqlite_master WHERE name='hostname_idx'").fetchone())
            c.execute("UPDATE dispositivos SET ip='192.168.1.33' WHERE id=82")
            c.execute("UPDATE dispositivos SET ip='192.168.1.90' WHERE id=89")
            with self.assertRaises(sqlite3.IntegrityError):
                c.execute("UPDATE dispositivos SET ip='192.168.1.33' WHERE id=89")
        with self.assertRaises(ValueError):
            self.call(True)

    def test_online_occupant_is_protected(self):
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE dispositivos SET status='online' WHERE id=89")
        with self.assertRaises(ValueError):
            self.call(True)

    def test_recent_collection_is_protected(self):
        with sqlite3.connect(self.path) as c:
            c.execute("UPDATE agentes SET ultima_coleta='2999-01-01' WHERE id='old'")
        with self.assertRaises(ValueError):
            self.call(True)


if __name__ == '__main__':
    unittest.main()
