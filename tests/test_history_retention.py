import sqlite3
import tempfile
import unittest
from pathlib import Path
from backend.history_retention import limpar_historico


class HistoryRetentionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name)/'test.db'
        with sqlite3.connect(self.path) as c:
            c.executescript('''CREATE TABLE historico_varreduras(id INTEGER PRIMARY KEY, finalizado_em TEXT);
                CREATE TABLE agentes(id INTEGER PRIMARY KEY, token_hash TEXT);
                INSERT INTO agentes VALUES(1,'credential-must-stay');''')
            c.executemany('INSERT INTO historico_varreduras VALUES(?,?)',
                [(i,None if i in (1,2) else '2026-10-29') for i in range(1,601)])

    def tearDown(self):
        self.tmp.cleanup()

    def test_cleanup_keeps_latest_finished_and_all_unfinished_and_credentials(self):
        result = limpar_historico(self.path,500,backup=True)
        self.assertEqual(result['removidos'],98)
        self.assertEqual(result['mantidos'],502)
        with sqlite3.connect(result['backup']) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM historico_varreduras').fetchone()[0],600)
        with sqlite3.connect(self.path) as c:
            ids=[r[0] for r in c.execute('SELECT id FROM historico_varreduras ORDER BY id')]
            self.assertEqual(ids,[1,2]+list(range(101,601)))
            self.assertEqual(c.execute('SELECT token_hash FROM agentes').fetchone()[0],'credential-must-stay')
        self.assertEqual(limpar_historico(self.path,500)['removidos'],0)

    def test_zero_disables_cleanup_and_negative_is_rejected(self):
        self.assertEqual(limpar_historico(self.path,0)['mantidos'],600)
        with self.assertRaises(ValueError):
            limpar_historico(self.path,-1)

    def test_delete_failure_rolls_back_and_backup_remains(self):
        with sqlite3.connect(self.path) as c:
            c.execute("CREATE TRIGGER fail_cleanup BEFORE DELETE ON historico_varreduras WHEN OLD.id=10 BEGIN SELECT RAISE(ABORT,'simulated failure'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            limpar_historico(self.path,500,backup=True)
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute('SELECT count(*) FROM historico_varreduras').fetchone()[0],600)
        self.assertEqual(len(list(Path(self.tmp.name).glob('*.before-history-cleanup-*'))),1)

    def test_missing_database_is_not_created(self):
        with self.assertRaises(FileNotFoundError):
            limpar_historico(Path(self.tmp.name)/'missing.db')
