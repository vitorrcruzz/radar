"""Retenção de resumos de varredura; não altera inventário nem credenciais."""
from contextlib import closing
from datetime import datetime
from pathlib import Path
import sqlite3


def limpar_historico(database, limite=500, backup=False):
    limite = int(limite)
    if limite < 0:
        raise ValueError('O limite de histórico não pode ser negativo.')
    path = Path(database).resolve(strict=True)
    resultado = {'removidos':0, 'backup':None}
    with closing(sqlite3.connect(path.as_uri()+'?mode=rw', uri=True, timeout=5)) as c:
        if limite == 0:
            resultado['mantidos'] = c.execute('SELECT count(*) FROM historico_varreduras').fetchone()[0]
            return resultado
        # Backup consistente inclui todos os cadastros; restrito ao usuário local.
        if backup:
            copia = path.with_name(path.name+'.before-history-cleanup-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            with closing(sqlite3.connect(copia)) as dest:
                c.backup(dest)
            copia.chmod(0o600)
            resultado['backup'] = str(copia)
        with c:
            c.execute('BEGIN IMMEDIATE')
            cursor = c.execute('''DELETE FROM historico_varreduras
                WHERE finalizado_em IS NOT NULL AND id NOT IN (
                    SELECT id FROM historico_varreduras WHERE finalizado_em IS NOT NULL
                    ORDER BY id DESC LIMIT ?
                )''', (limite,))
            resultado['removidos'] = cursor.rowcount
            resultado['mantidos'] = c.execute('SELECT count(*) FROM historico_varreduras').fetchone()[0]
    return resultado
