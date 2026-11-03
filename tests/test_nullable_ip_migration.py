import sqlite3
import unittest
from backend.migrations import permitir_dispositivo_sem_ip
import test_release_stale_ip as fixtures


class NullableIPMigrationTests(unittest.TestCase):
    setUp = fixtures.ReleaseStaleIPTests.setUp
    tearDown = fixtures.ReleaseStaleIPTests.tearDown

    def test_migration_preserves_legacy_columns_and_is_idempotent(self):
        backup = permitir_dispositivo_sem_ip(self.path)
        self.assertIsNotNone(backup)
        self.assertIsNone(permitir_dispositivo_sem_ip(self.path))
        with sqlite3.connect(self.path) as c:
            self.assertEqual(c.execute('SELECT ip,legado FROM dispositivos WHERE id=89').fetchone(),
                             ('192.168.1.33', 'preservar'))
            self.assertEqual(c.execute('SELECT count(*) FROM historico').fetchone()[0], 1)
            c.execute('UPDATE dispositivos SET ip=NULL WHERE id=89')
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])

    def test_broken_references_cancel_migration(self):
        with sqlite3.connect(self.path) as c:
            c.execute("INSERT INTO historico VALUES(2,9999,'invalido')")
        with self.assertRaises(RuntimeError):
            permitir_dispositivo_sem_ip(self.path)
        with sqlite3.connect(self.path) as c:
            self.assertEqual(next(r for r in c.execute('PRAGMA table_info(dispositivos)') if r[1]=='ip')[3], 1)
            self.assertEqual(c.execute('SELECT count(*) FROM dispositivos').fetchone()[0], 2)
