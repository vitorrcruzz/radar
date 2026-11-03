"""Migrações SQLite que preservam colunas legadas e referências."""
from datetime import datetime
from pathlib import Path
import re
import sqlite3


def permitir_dispositivo_sem_ip(database_path):
    path = Path(database_path).resolve()
    with sqlite3.connect(path) as c:
        info = c.execute('PRAGMA table_info(dispositivos)').fetchall()
        if not any(col[1] == 'ip' and col[3] for col in info):
            return None
        backup = path.with_name(path.name + '.before-nullable-ip-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        with sqlite3.connect(backup) as dest:
            c.backup(dest)
        backup.chmod(0o600)
        c.execute('PRAGMA foreign_keys=OFF')
        c.execute('BEGIN IMMEDIATE')
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('Migração de IP cancelada: vínculos inconsistentes no banco.')
        ddl = c.execute("SELECT sql FROM sqlite_master WHERE name='dispositivos' AND type='table'").fetchone()[0]
        ddl, count = re.subn(r'(?im)^(\s*ip\s+VARCHAR\(15\))\s+NOT NULL', r'\1', ddl)
        if count != 1 or 'CREATE TABLE dispositivos' not in ddl:
            raise RuntimeError('Migração de IP cancelada: esquema desconhecido.')
        extras = c.execute("SELECT sql FROM sqlite_master WHERE tbl_name='dispositivos' AND type IN ('index','trigger') AND sql IS NOT NULL").fetchall()
        cols = ','.join('"' + row[1].replace('"','""') + '"' for row in info)
        c.execute(ddl.replace('CREATE TABLE dispositivos', 'CREATE TABLE dispositivos_ip_migration', 1))
        c.execute(f'INSERT INTO dispositivos_ip_migration ({cols}) SELECT {cols} FROM dispositivos')
        c.execute('DROP TABLE dispositivos')
        c.execute('ALTER TABLE dispositivos_ip_migration RENAME TO dispositivos')
        for extra in extras:
            c.execute(extra[0])
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise RuntimeError('Migração de IP cancelada: referências não foram preservadas.')
        return str(backup)
