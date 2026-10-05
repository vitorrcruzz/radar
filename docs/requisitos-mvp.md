# Requisitos do MVP do RADAR

**Projeto:** R.A.D.A.R. — Rastreamento Automático de Ativos de Rede  
**Prazo acadêmico informado:** 29/11/2026  
**Estado:** requisitos iniciais acordados; implementação ainda em andamento.

## Objetivo

Desenvolver uma aplicação multiplataforma, baseada em Python, para inventariar equipamentos de TI que respondam a consultas SNMP. A aplicação será instalada na rede monitorada, iniciada por comando e acessada pelo navegador através da rede local.

## Escopo do MVP

- Compatibilidade de execução com Linux e Windows, sem exigir Docker para executar a aplicação principal.
- Coleta SNMP v1, v2c e v3, conforme suporte e configuração dos dispositivos.
- Configuração administrativa de várias sub-redes autorizadas e de faixas excluídas.
- Considerar no inventário de descoberta somente equipamentos que respondam a SNMP.
- Cobrir os tipos do projeto base: computadores, servidores, impressoras, switches, roteadores, access points, câmeras IP e nobreaks, sem prioridade de fabricante.
- Exibir hostname, tipo, modelo, sistema operacional, processador, memória, armazenamento, número de série, MAC, localização e uptime. Exibir “não informado” quando o dispositivo não disponibilizar um dado via SNMP.
- Dashboard web com autenticação e perfis de administrador e usuário comum.
- No piloto, limitar o escopo a duas contas por instalação (uma de cada perfil); manter a solução extensível para aumentar esse limite depois.
- Varreduras manuais e agendadas, com histórico de cada execução.
- Marcar como offline os equipamentos conhecidos que não responderem, mantendo os dados existentes.
- Permitir configurar um prazo desde a última resposta para arquivar ou excluir o cadastro do equipamento. Preservar o histórico das varreduras.
- Gerenciar licenças, com cadastro manual e importação/exportação em CSV e Excel. Dados desejados: nome, vencimento, quantidade, fornecedor, chave, responsável e equipamentos associados.
- Manter o Docker apenas como apoio opcional para simulação durante desenvolvimento e demonstrações.

## Fora do escopo inicial

- Coletar dados de equipamentos sem suporte SNMP.
- Instalar agentes nos computadores monitorados.
- Acesso remoto pela internet ou VPN (incluindo Tailscale).
- Hospedagem pública do painel. O piloto será acessado pela rede local.
- Priorização por fabricante ou modelo.

## Limites e premissas técnicas

- A máquina do RADAR deve ter conectividade de rede até as sub-redes configuradas. O administrador é responsável por informar os intervalos autorizados.
- Credenciais do sistema operacional não autenticam SNMP. O administrador deverá configurar perfis SNMP (community para v1/v2c; usuário e parâmetros de segurança para v3) adequados aos dispositivos.
- O protocolo e os dados disponibilizados variam por equipamento. Campos indisponíveis devem ser apresentados como “não informado”, sem impedir que o ativo seja inventariado.
- SNMP v1/v2c podem transmitir credenciais sem criptografia. Preferir SNMPv3 com autenticação e privacidade quando os dispositivos oferecerem suporte.
- Informações como processador, RAM, disco, serial e sistema operacional nem sempre são fornecidas pelo SNMP padrão; a disponibilidade será validada durante o piloto.
- O acesso externo via HTTPS e uma implantação pública poderão ser avaliados após validar a coleta na rede da empresa.

## Critérios de aceite iniciais

1. Instalar e iniciar a aplicação em Linux e Windows seguindo documentação do projeto, sem Docker para o uso normal.
2. Configurar uma ou mais sub-redes autorizadas e iniciar uma varredura manual.
3. Consultar dispositivos SNMP com as versões e credenciais configuradas, sem guardar credenciais em código-fonte ou exibi-las a usuários comuns.
4. Exibir os dados encontrados e indicar claramente campos ausentes.
5. Registrar execução, horários, resultados e estado dos equipamentos conhecidos.
6. Exigir login e aplicar permissões de administrador e usuário comum.
7. Importar licenças por CSV e Excel e cadastrar licenças manualmente.
8. Exportar relatórios do inventário.
9. Permitir configurar retenção de ativos não vistos, mantendo histórico de coleta.

## Questões para validar no piloto

- Quais versões e configurações SNMP os equipamentos da empresa realmente oferecem?
- Quais dos campos planejados são retornados pelos modelos encontrados?
- Qual volume e tamanho de sub-redes será necessário varrer e qual intervalo de coleta é aceitável?
- Qual prazo de retenção padrão faz sentido para ativos sem resposta?
- Quais informações de licença serão obrigatórias e qual será o modelo de planilha de importação?
- Quais ações cada perfil poderá realizar?

## Entregas sugeridas

1. Consolidar requisitos, modelo de dados e estrutura multiplataforma.
2. Remover dependências do scanner que exigem binários externos e implementar coleta SNMP multiplataforma.
3. Adaptar descoberta e varredura a múltiplas sub-redes, credenciais e limites configuráveis.
4. Implementar autenticação, perfis e administração de redes/credenciais.
5. Implementar histórico, retenção e gestão/importação de licenças.
6. Documentar instalação e operação em Linux e Windows.
7. Validar com simuladores e, com autorização, em equipamentos reais da empresa piloto.
8. Revisar o resumo e a documentação acadêmica conforme os resultados práticos e as normas ABNT aplicáveis.
