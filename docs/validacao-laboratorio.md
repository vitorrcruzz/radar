# Registro de validação em laboratório

**Projeto:** R.A.D.A.R. — Rastreamento Automático de Ativos de Rede
**Data:** 07/10/2026
**Ambiente:** laboratório doméstico; servidor RADAR Linux e computador cliente Windows 11 Pro (build 26200).

Este registro descreve o resultado técnico sem incluir IPs, hostname, endereço MAC, número de série, nome de usuário ou credenciais. Esses dados identificam equipamentos e não devem ser versionados no repositório público.

## Objetivo

Verificar se a coleta SNMP consegue descobrir um computador Windows e se WMI por WinRM pode complementar atributos que o agente SNMP não fornece. Também foi conferida a apresentação dos campos no painel web.

## Resultado

- O computador respondeu à consulta SNMP v2c e foi mantido como equipamento descoberto pelo RADAR.
- O SNMP forneceu hostname, uptime, memória, volumes de armazenamento, endereço MAC associado à interface consultada e descrição do sistema.
- A interpretação do build SNMP identificou corretamente Windows 11 25H2, build 26200.
- O agente SNMP não forneceu modelo nem número de série pela ENTITY-MIB consultada.
- Com WinRM habilitado e credenciais configuradas localmente no ambiente do RADAR, WMI retornou modelo, número de série, edição/build do Windows, nome comercial do processador, memória e volumes.
- Após uma varredura iniciada pelo painel, modelo, serial e processador coletados por WMI apareceram no cadastro do equipamento.
- A edição manual foi implementada. As correções ficam armazenadas separadamente dos valores coletados; a preservação no painel após uma nova varredura ainda precisa de validação prática.

## Interpretação para o TCC

O teste indica que SNMP e WMI/WinRM são complementares neste cenário. A descoberta continua condicionada à resposta SNMP, enquanto WMI/WinRM enriquece computadores Windows já identificados. Não foi instalado agente próprio do RADAR. A manutenção manual permanece disponível quando um método de coleta não fornece o atributo.

Essa abordagem é compatível com a proposta de gestão do ciclo de vida dos ativos: os dados técnicos ajudam a identificar e avaliar equipamentos, enquanto condições patrimoniais, manutenção e destinação final continuam dependendo de registro administrativo. O teste não mediu consumo de energia, geração de resíduos ou impacto ambiental.

## Limites e próximos passos

- Esta validação foi feita em laboratório doméstico; ainda não é evidência do piloto na empresa.
- WinRM precisa estar habilitado no computador Windows. O firewall deve aceitar a origem do servidor RADAR, sem expor a porta de gerenciamento à internet.
- As credenciais WMI são diferentes das credenciais SNMP e devem permanecer em configuração local ignorada pelo Git.
- Durante a consulta, PyWinRM exibiu um aviso ao interpretar uma mensagem de erro do PowerShell, embora tenha retornado os dados esperados. Investigar se o aviso persiste em varreduras completas.
- Próximas validações: repetir varredura, conferir persistência dos valores manuais, testar outro Windows e validar ao menos um dispositivo de rede que não seja computador.
