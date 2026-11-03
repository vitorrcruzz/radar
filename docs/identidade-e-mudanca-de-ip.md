# Identidade e mudança de IP — 28/10/2026

A atualização é exclusiva do servidor. Os agentes já instalados continuam usando seu UUID, token e o mesmo formato de inventário. Não é necessário reinstalar agentes para tratar mudanças de IP.

## Identificação

- Agentes autenticados atualizam o dispositivo vinculado ao UUID/token. IP não é credencial.
- Coletas SNMP procuram um cadastro correspondente por serial ou MAC antes de procurar pelo IP. Campos manuais de identidade têm precedência quando preenchidos.
- MACs são comparados independentemente de caixa e separadores. Endereços nulos, broadcast e multicast não identificam ativos.
- Seriais genéricos como `To Be Filled By O.E.M.` e `Default string` são ignorados.
- O mesmo serial permite reconhecer um dispositivo que mudou de adaptador de rede. Se o MAC coincidir mas os dois seriais válidos forem diferentes, o sistema exige revisão.
- Identificadores repetidos em vários cadastros não causam fusão automática.

## Endereço ocupado

Um host descoberto apenas por ICMP, sem agente, inventário, dados manuais, softwares ou histórico de IP, pode ser removido na mesma transação que atribui o endereço ao equipamento autenticado.

Se o endereço pertencer a outro ativo completo, o registro anterior é preservado, fica offline e sem IP atual somente quando:

1. A identidade de hardware do ativo que mudou de IP corresponde ao seu cadastro.
2. O ocupante anterior não tem atividade recente. A janela usa `AGENT_OFFLINE_AFTER_SECONDS`, no mínimo 60 segundos; o padrão é 900 segundos.
3. No envio por agente, o IP de origem da conexão corresponde ao IP informado. As verificações de token, UUID e redes autorizadas continuam obrigatórias.
4. O ocupante anterior não tem a mesma identidade de hardware, caso que requer revisão de cadastros duplicados.

Se os dois ativos tiverem atividade recente, o servidor mantém o conflito até obter condições suficientes. Isso pode atrasar uma troca simultânea de endereços até o fim da janela de atividade. Instalações com NAT entre agente e servidor não fazem essa transferência automática de um IP ocupado por outro ativo completo.

Cada mudança automática é registrada em `historico_ips`, com dispositivo, IP anterior, IP novo, origem e data. Históricos de coleta, campos manuais, softwares e agentes permanecem vinculados ao mesmo dispositivo. Nenhum token é recuperado ou substituído por comparação de MAC/serial.

## Banco e implantação

Ao iniciar, o servidor permite IP nulo em cadastros antigos. A migração SQLite cria um backup em `database/inventario.db.before-nullable-ip-*`, preserva colunas legadas, índices e vínculos e valida as chaves estrangeiras. Bancos já migrados não são reconstruídos novamente.

```bash
cd /radar
docker compose up -d --build inventario-app
```

Não use os scripts de instalação/atualização dos agentes para essa mudança. O script `release-stale-ip.py` é uma ferramenta de revisão manual específica; não é necessário executá-lo para os casos agora atendidos automaticamente.

A lista de dispositivos visível é atualizada a cada 30 segundos, preservando pesquisa, ordenação e paginação. O polling da lista é suspenso enquanto há um modal aberto ou a aba do navegador está oculta. Um modal já aberto pode exigir fechar e abrir para consultar novamente os dados.

Falhas de autenticação 401 continuam exigindo diagnóstico da credencial. Essa mudança resolve identidade e endereço; não autoriza agentes sem credenciais válidas.

## Validação

Os testes usam bancos temporários e cobrem troca de IP por agente, descoberta SNMP, proteção de atividade recente, identificadores inválidos/ambíguos, preservação de cadastros e rollback. A migração também é verificada em cópia isolada do banco existente. A aplicação no ambiente real deve ser confirmada pelas próximas coletas após reconstruir o contêiner.
