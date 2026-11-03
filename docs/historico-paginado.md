# Histórico paginado — 28/10/2026

A tabela de histórico usa paginação no servidor, com 15 varreduras por página e opções de 10, 15, 25 ou 50. O servidor consulta somente a página solicitada no banco. A paginação não exclui registros. A política de retenção descrita abaixo limita os resumos guardados no banco.

Pesquisa e ordenação também são executadas no servidor. O número exibido de registros encontrados corresponde ao filtro aplicado. A tabela é criada uma única vez e, ao voltar à tela, recarrega a página atual sem reconstruir milhares de linhas.

A rota `GET /api/historico` passa a retornar o objeto do protocolo DataTables: `draw`, `recordsTotal`, `recordsFiltered` e `data`. Recebe `start`, `length`, `search[value]`, `order[0][column]` e `order[0][dir]`. Tamanhos inválidos usam o padrão de 15 e nenhum pedido retorna mais de 50 registros. Clientes externos que esperavam uma lista completa devem se adaptar à paginação.

O gráfico consulta `GET /api/historico/recentes`, que devolve somente as dez varreduras mais recentes. Assim, a atualização periódica do dashboard deixa de baixar todo o histórico.

Validação: testes com 4.005 varreduras cobrem limite SQL, páginas distintas, busca por data/origem, ordenação, parâmetros inválidos, resultados vazios e limite do gráfico. Esses testes usam uma base temporária.

Para implantar os arquivos atualizados:

```bash
cd /radar
docker compose up -d --build inventario-app
```

Atualize a página com Ctrl+F5 para carregar o JavaScript que usa a nova resposta da API.

## Retenção e otimizações — 29/10/2026

Após cada varredura concluída, o servidor mantém os 500 resumos concluídos mais recentes. Registros sem finalização são preservados. A variável `HISTORICO_MAX_REGISTROS` configura o limite; `0` desativa a limpeza automática. A configuração é repassada pelo Docker Compose.

Essa limpeza não exclui dispositivos, usuários, agentes, credenciais, softwares cadastrados ou coletas de agentes. Estas últimas têm armazenamento independente e não estão abrangidas por essa política. O contador acumulado do dashboard não representa a quantidade de resumos retidos.

Na limpeza inicial foram removidos 3.629 resumos, permanecendo 500 concluídos e quatro sem finalização. Foi criado um backup SQLite consistente em `database/inventario.db.before-history-cleanup-20261029-162837-429154`, com acesso restrito ao proprietário e fora do versionamento. Não se executou VACUUM no banco em uso: o espaço liberado será reutilizado pelo SQLite, sem redução imediata obrigatória do arquivo.

Os gráficos têm altura limitada e reutilizam suas instâncias, atualizando somente quando os dados mudam. A consulta periódica pausa quando a aba fica oculta e evita execuções sobrepostas. O gráfico de histórico só é atualizado periodicamente quando o dashboard está visível.

Validação adicional: testes de retenção verificam backup, limite, preservação dos registros em andamento e das credenciais, repetição segura e rollback em falha. O teste JavaScript simula 50 atualizações sem recriar os gráficos. Ainda é necessário observar o navegador e o servidor em uso para confirmar se os travamentos cessaram.
