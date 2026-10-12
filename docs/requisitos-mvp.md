# Requisitos do MVP do RADAR

**Projeto:** R.A.D.A.R. — Rastreamento Automático de Ativos de Rede  
**Prazo acadêmico informado:** 29/11/2026  
**Estado:** requisitos iniciais acordados; implementação ainda em andamento.

## Objetivo

Desenvolver uma aplicação multiplataforma, baseada em Python, para inventariar ativos de TI por meio de dois mecanismos: um agente RADAR instalado nos computadores Windows/Linux e consultas SNMP a equipamentos de rede que ofereçam esse protocolo. O servidor RADAR será instalado na rede monitorada, iniciado localmente e acessado pelo navegador através da rede autorizada.

## Green TI e gestão do ciclo de vida dos ativos

Alinhado ao TCC, o RADAR deve apoiar o controle do ciclo de vida dos ativos de TI. O inventário deve ajudar a equipe a identificar equipamentos que precisam de manutenção, avaliar a necessidade de substituição e registrar a destinação adequada dos equipamentos desativados.

No MVP, o cadastro patrimonial poderá incluir, por preenchimento manual:
- data de aquisição e início de uso;
- condição e situação atual do equipamento;
- histórico de manutenções e reparos;
- avaliação administrativa sobre obsolescência ou necessidade de substituição;
- data e forma de desativação e destinação final, com responsável e comprovante quando disponíveis.

Os relatórios poderão apresentar os equipamentos por condição e etapa do ciclo de vida, manutenções registradas e ativos aguardando destinação. A idade do equipamento, sozinha, não deve classificá-lo automaticamente como obsoleto; essa avaliação cabe à equipe responsável.

Esses recursos apoiam decisões de gestão e práticas de destinação adequada. O MVP não calculará economia de energia, redução de resíduos ou impacto de carbono.

## Escopo do MVP

- Compatibilidade de execução com Linux e Windows, sem exigir Docker para executar a aplicação principal.
- Agente RADAR para coletar localmente dados dos computadores Windows da empresa; a implementação deve permanecer compatível com Linux. Computadores macOS ficam fora do escopo do piloto.
- Consultas SNMP v1, v2c e v3 para equipamentos de rede e outros ativos que ofereçam esse protocolo.
- O agente consulta os dados do Windows localmente pelo WMI/COM via Python; isso não habilita WinRM remoto nem exige armazenar credenciais administrativas das estações no servidor RADAR. A prova WinRM anterior permanece registrada como validação técnica complementar.
- A instalação inicial do agente requer autorização e privilégio administrativo no computador. A senha administrativa será usada somente no processo de instalação aprovado e não será enviada nem armazenada pelo agente. Após instalado como serviço, o agente executará com a identidade de serviço do sistema operacional e enviará os dados ao servidor RADAR autenticando-se por credencial própria do agente.
- Sem acesso à console de administração ESET PROTECT, não assumimos que o ESET possa distribuir ou configurar o agente. A implantação piloto será manual ou por ferramenta corporativa que a empresa autorize.
- Permitir corrigir ou complementar manualmente os dados do cadastro; valores manuais devem permanecer preservados nas varreduras seguintes e podem ser apagados para voltar ao valor coletado.
- Rede inicial informada para o piloto: `192.168.1.0/24`, no 7º andar. A quantidade de ativos é desconhecida; a estimativa de cerca de 10 computadores não limita o inventário, cujo objetivo é identificar o parque completo na faixa autorizada.
- Consultas SNMP restritas às faixas autorizadas e alcançáveis a partir do servidor. Computadores com agente podem se registrar enviando dados ao servidor, sem depender de varredura SNMP para serem inventariados.
- A descoberta inicial tenta localizar hosts respondendo a SNMP ou ICMP na sub-rede autorizada para apoiar a contagem e a implantação do agente. Ping é indício de presença, não substitui dados completos; hosts que bloqueiem ICMP e não respondam a SNMP podem não aparecer. Lista de concessões DHCP, quando fornecida pela equipe de rede, complementa o levantamento.
- Cobrir os tipos do projeto base: computadores, servidores, impressoras, switches, roteadores, access points, câmeras IP e nobreaks, sem prioridade de fabricante.
- Exibir hostname, tipo, modelo, sistema operacional, processador, memória, armazenamento, número de série, MAC, localização e uptime. Exibir “não informado” quando um método de coleta não disponibilizar determinado dado.
- Para computadores Windows, o agente deverá coletar a versão comercial do sistema operacional, identificação do processador e contagem de processadores lógicos. A identificação de hardware não será apresentada como modelo comercial do processador.
- Dashboard web com autenticação e perfis de administrador e usuário comum.
- No piloto, limitar o escopo a duas contas por instalação (uma de cada perfil); manter a solução extensível para aumentar esse limite depois.
- Varreduras manuais e agendadas, com histórico de cada execução.
- Marcar como offline os equipamentos conhecidos que não responderem, mantendo os dados existentes.
- Permitir configurar um prazo desde a última resposta para arquivar ou excluir o cadastro do equipamento. Preservar o histórico das varreduras.
- Gerenciar licenças, com cadastro manual e importação/exportação em CSV e Excel. Dados desejados: nome, vencimento, quantidade, fornecedor, chave, responsável e equipamentos associados.
- Manter o Docker apenas como apoio opcional para simulação durante desenvolvimento e demonstrações.

## Fora do escopo inicial

- Coletar automaticamente computadores sem agente e equipamentos sem SNMP; a descoberta auxiliar poderá indicar hosts alcançáveis, mas não fornecerá inventário completo sem um método de coleta autorizado.
- Distribuir o agente para todo o parque antes da validação inicial. A primeira instalação será feita em um grupo de validação acordado com a equipe; depois, a implantação poderá ser ampliada para os computadores identificados e autorizados, sem limite fixo de quantidade no inventário.
- Acesso do painel pela internet ou VPN (incluindo Tailscale).
- Hospedagem pública do painel. O piloto será acessado pela rede local.
- Priorização por fabricante ou modelo.

## Limites e premissas técnicas

- A máquina do RADAR deve ter conectividade de rede até as sub-redes configuradas. O administrador é responsável por informar os intervalos autorizados.
- Credenciais do sistema operacional não autenticam SNMP. O administrador deverá configurar perfis SNMP (community somente leitura para v1/v2c; usuário e parâmetros de segurança para v3) adequados aos dispositivos de rede.
- O agente iniciará conexões de saída para a API do RADAR; não será necessário abrir conexão de entrada do servidor para cada estação. A API deverá exigir credencial individual do agente e HTTPS com certificado confiável antes da implantação real. Para o piloto, o servidor deverá ser alcançável a partir da rede `192.168.1.0/24` do 7º andar.
- O acesso administrativo local será necessário para instalar o agente como serviço. O agente não deve guardar a senha do administrador. A empresa aprovará a identidade e as permissões usadas pelo serviço em cada sistema operacional.
- O protocolo e os dados disponibilizados variam por equipamento. Campos indisponíveis devem ser apresentados como “não informado”, sem impedir que o ativo seja inventariado.
- Quando disponibilizados, os endereços MAC serão associados à interface que contém o endereço IP consultado, cruzando as informações da IP-MIB com `ifPhysAddress` da IF-MIB. Se o agente não expuser essa associação ou o endereço físico, o MAC será apresentado como “não informado”; não será escolhido um MAC arbitrário entre interfaces virtuais.
- SNMP v1/v2c podem transmitir credenciais sem criptografia. Preferir SNMPv3 com autenticação e privacidade quando os dispositivos oferecerem suporte.
- Informações de hardware e sistema operacional dos computadores serão coletadas localmente pelo agente. Equipamentos sem agente e sem SNMP continuarão fora da coleta automática do MVP.
- O coletor SNMP consulta modelo e serial de chassi na ENTITY-MIB quando o equipamento de rede a expõe. A coleta local do agente deverá fornecer os dados disponíveis do computador sem habilitar WinRM ou guardar credenciais administrativas no servidor.
- O cadastro manual tem prioridade visual sobre os dados coletados e sobrevive a novas coletas; apagar uma correção manual retorna o campo à coleta do agente ou SNMP. SSH, citado no contexto técnico do TCC, poderá ser avaliado como alternativa para ativos Linux sem agente em etapa posterior.
- O acesso externo ao painel e uma implantação pública poderão ser avaliados após validar a coleta na rede da empresa. O HTTPS na rede local é necessário para proteger a comunicação entre os agentes e o servidor.

## Critérios de aceite iniciais

1. Instalar e iniciar a aplicação em Linux e Windows seguindo documentação do projeto, sem Docker para o uso normal.
2. Instalar o agente em computadores autorizados, registrar cada um e receber os dados no servidor via HTTPS autenticado; manter compatibilidade Linux validada em ambiente de laboratório se a empresa não tiver equipamento Linux no escopo.
3. Configurar uma ou mais sub-redes autorizadas e consultar equipamentos SNMP com as versões e credenciais configuradas, sem guardar credenciais em código-fonte ou exibi-las a usuários comuns.
4. Exibir os dados encontrados e indicar claramente campos ausentes.
5. Permitir corrigir campos manualmente sem que novas varreduras apaguem essas correções; remover uma correção devolve o campo à coleta automática.
6. Registrar execução, horários, resultados e estado dos equipamentos conhecidos.
7. Exigir login e aplicar permissões de administrador e usuário comum.
8. Importar licenças por CSV e Excel e cadastrar licenças manualmente.
9. Exportar relatórios do inventário.
10. Permitir configurar retenção de ativos não vistos, mantendo histórico de coleta.

## Questões para validar no piloto

- Quais versões e configurações SNMP os equipamentos da empresa realmente oferecem?
- O servidor RADAR conseguirá alcançar toda a sub-rede `192.168.1.0/24`?
- Qual procedimento aprovado será usado para instalar o agente nas estações Windows, já que a equipe do projeto não tem acesso ao painel ESET PROTECT?
- Quais versões de Windows precisam ser cobertas no piloto? Linux permanece como requisito de compatibilidade, embora o parque piloto seja quase todo Windows.
- A empresa fornecerá certificado TLS interno ou permitirá outra forma de confiar no HTTPS do servidor RADAR?
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
