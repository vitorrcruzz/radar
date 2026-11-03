"""Libera um vínculo IP antigo sem excluir ativos, agentes ou históricos.

Execute com inventario-app parado. Sem --apply, apenas mostra a proposta.
"""
import argparse
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
import sqlite3
import ipaddress


def liberar(database, ip, occupant_id, incoming_agent, apply=False):
    ipaddress.IPv4Address(ip)
    path = Path(database).resolve(strict=True)
    c = sqlite3.connect(path.as_uri() + '?mode=rw', uri=True)
    c.row_factory = sqlite3.Row
    try:
        occupied = c.execute('SELECT * FROM dispositivos WHERE id=?', (occupant_id,)).fetchone()
        agent = c.execute('SELECT * FROM agentes WHERE id=?', (incoming_agent,)).fetchone()
        if occupied is None or agent is None or not agent['ativo']:
            raise ValueError('Cadastro ou agente ativo não encontrado.')
        if agent['dispositivo_id'] == occupant_id:
            raise ValueError('O agente já pertence ao cadastro informado.')
        if occupied['ip'] != ip:
            raise ValueError('O cadastro não ocupa mais esse IP; nenhuma alteração aplicada.')
        if occupied['status'] != 'offline':
            raise ValueError('O ocupante está online; liberação automática recusada.')
        recent = c.execute('SELECT ultima_coleta FROM agentes WHERE dispositivo_id=?', (occupant_id,)).fetchone()
        for stamp in (occupied['ultima_vez'], recent['ultima_coleta'] if recent else None):
            if stamp and datetime.fromisoformat(stamp) > datetime.now() - timedelta(minutes=15):
                raise ValueError('O ocupante teve atividade nos últimos 15 minutos. Aguarde e revise.')
        incoming = c.execute('SELECT hostname, serial_number FROM dispositivos WHERE id=?', (agent['dispositivo_id'],)).fetchone()
        proposal = {'ip_liberado': ip, 'cadastro_preservado': occupant_id,
                    'hostname_anterior': occupied['hostname'], 'serial_anterior': occupied['serial_number'],
                    'agente_aguardado': incoming_agent, 'hostname_informante': incoming['hostname'],
                    'serial_informante': incoming['serial_number']}
        if not apply:
            return proposal
        backup = path.with_name(path.name + '.before-release-ip-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        with sqlite3.connect(backup) as dest:
            c.backup(dest)
        backup.chmod(0o600)
        # SQLite exige recriar a tabela para remover NOT NULL. Mantemos o DDL
        # original, inclusive colunas legadas, UNIQUE, índices e gatilhos.
        c.execute('PRAGMA foreign_keys=OFF')
        c.execute('BEGIN IMMEDIATE')
        current = c.execute('SELECT ip,status,ultima_vez FROM dispositivos WHERE id=?', (occupant_id,)).fetchone()
        if tuple(current) != (occupied['ip'], occupied['status'], occupied['ultima_vez']):
            raise ValueError('O cadastro mudou durante a operação; repita a análise.')
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('O banco já possui inconsistências de vínculos; liberação cancelada.')
        info = c.execute('PRAGMA table_info(dispositivos)').fetchall()
        if next(row for row in info if row['name'] == 'ip')['notnull']:
            ddl = c.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='dispositivos'").fetchone()[0]
            ddl, count = re.subn(r'(?im)^(\s*ip\s+VARCHAR\(15\))\s+NOT NULL', r'\1', ddl)
            if count != 1:
                raise ValueError('Esquema IP não reconhecido; nenhuma alteração aplicada.')
            ddl = ddl.replace('CREATE TABLE dispositivos', 'CREATE TABLE dispositivos_ip_migration', 1)
            if 'CREATE TABLE dispositivos_ip_migration' not in ddl:
                raise ValueError('DDL da tabela não reconhecido.')
            extras = c.execute("SELECT sql FROM sqlite_master WHERE tbl_name='dispositivos' AND type IN ('index','trigger') AND sql IS NOT NULL").fetchall()
            cols = ','.join('"' + row['name'].replace('"','""') + '"' for row in info)
            c.execute(ddl)
            c.execute(f'INSERT INTO dispositivos_ip_migration ({cols}) SELECT {cols} FROM dispositivos')
            c.execute('DROP TABLE dispositivos')
            c.execute('ALTER TABLE dispositivos_ip_migration RENAME TO dispositivos')
            for extra in extras:
                c.execute(extra[0])
        c.execute("UPDATE dispositivos SET ip=NULL, rede=NULL, status='offline' WHERE id=?", (occupant_id,))
        if c.execute('PRAGMA foreign_key_check').fetchall():
            raise ValueError('Falha na validação dos vínculos; operação revertida.')
        c.commit()
        proposal['backup'] = str(backup)
        proposal['resultado'] = 'Vínculo liberado; aguardando próxima coleta autenticada.'
        audit = backup.with_suffix(backup.suffix + '.json')
        audit.write_text(json.dumps(proposal, ensure_ascii=False, indent=2), encoding='utf-8')
        audit.chmod(0o600)
        return proposal
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', default=str(Path(__file__).resolve().parents[1] / 'database/inventario.db'))
    parser.add_argument('--ip', required=True)
    parser.add_argument('--occupant-id', type=int, required=True)
    parser.add_argument('--incoming-agent', required=True)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        print(json.dumps(liberar(args.database, args.ip, args.occupant_id, args.incoming_agent, args.apply), ensure_ascii=False, indent=2))
    except (ValueError, sqlite3.Error) as error:
        parser.exit(1, f'Operação cancelada: {error}\n')
