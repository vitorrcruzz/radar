# R.A.D.A.R. — Rastreamento Automático de Ativos de Rede

Sistema em desenvolvimento para inventariar ativos de TI usando SNMP nos equipamentos de rede e um agente próprio nos computadores Windows/Linux. O projeto está sendo migrado de um protótipo simulado para uma aplicação Python multiplataforma, acessada pelo navegador na rede local.

> **Estado atual:** painel protegido por login e perfis, API autenticada, coleta local multiplataforma e scripts iniciais para execução automática do agente. A instalação precisa ser validada em cada sistema operacional e HTTPS ainda precisa ser implantado. Não usar em produção ainda.

## Objetivo do MVP

- Executar a aplicação principal em Linux e Windows sem exigir Docker.
- Consultar SNMP v1, v2c e v3 nas sub-redes explicitamente autorizadas pelo administrador.
- Instalar um agente nos computadores para coletar localmente os dados de hardware e sistema e enviá-los ao RADAR por conexão de saída autenticada.
- Permitir corrigir dados manualmente e preservar essas correções em varreduras futuras.
- Inventariar os tipos de equipamentos cobertos pelo projeto base e mostrar “não informado” quando um equipamento não expuser determinado dado.
- Oferecer painel web com autenticação, perfis, histórico de varreduras, relatórios e gestão de licenças.
- Manter Docker como recurso opcional para simular dispositivos durante o desenvolvimento.

O escopo e os critérios de aceite estão detalhados em [`docs/requisitos-mvp.md`](docs/requisitos-mvp.md). A documentação original do protótipo foi preservada em [`docs/prototipo-base.md`](docs/prototipo-base.md).

## Situação da migração

- [x] Importado o código do projeto base para este repositório local.
- [x] Registrados os requisitos iniciais do MVP.
- [x] Implementar protótipo de agente multiplataforma para coleta local em Windows e Linux.
- [ ] Validar instaladores e execução automática do agente em Windows e Linux.
- [x] Implementar API autenticada para receber dados dos agentes (HTTPS ainda precisa ser implantado e validado).
- [x] Criar o primeiro fluxo de registro autenticado e coleta pontual do agente (ainda sem instalador/serviço).
- [ ] Configurar descoberta segura em múltiplas sub-redes e perfis de credenciais SNMP.
- [x] Implementar autenticação e perfis básicos de acesso (admin e usuário).
- [ ] Completar histórico, retenção, gestão de licenças e relatórios para uso real.
- [ ] Documentar e validar instalação em Linux e Windows.
- [ ] Validar com a empresa piloto, mediante autorização.

## Execução nativa

O servidor pode ser iniciado sem Docker. Na raiz do repositório, crie e ative um ambiente virtual e instale as dependências:

```bash
python -m venv .venv
```

Linux:

```bash
source .venv/bin/activate
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Depois, nos dois sistemas:

```bash
python -m pip install -r requirements.txt
```

Copie `.env.example` para `.env`, defina um `RADAR_SECRET_KEY` aleatório, ajuste `SCAN_NETWORK` e `SCAN_COMMUNITY` às credenciais SNMP autorizadas e crie a primeira conta administradora:

```bash
python backend/app.py
```

Em outro terminal, com o mesmo ambiente virtual ativo, crie a conta (a senha será digitada sem aparecer e não ficará nos argumentos do processo):

```bash
python -m backend.create_user --nome "Administrador" --email admin@exemplo.local --perfil admin
```

Abra `http://localhost:5000` e entre com essa conta. Para acesso pela rede, use o IP do servidor no lugar de `localhost`. Crie contas adicionais pelo mesmo comando, usando `--perfil usuario` para acesso de consulta e exportação. Administradores podem iniciar varreduras e editar dados manuais. O HTTPS pode ser ativado com os caminhos de certificado descritos abaixo; sem HTTPS, mantenha o uso restrito ao laboratório.

## Simulação com Docker

Docker Compose continua disponível para simular dispositivos SNMP. Copie `.env.example` para `.env`, deixe `SCAN_NETWORK` apontando para `172.20.0.0/24` e inicie com `docker compose up -d --build`. Acesse `http://localhost:5000` e use **Escanear Agora**.

### Agente de coleta e instalação como serviço

O agente coleta localmente dados do computador e registra um token individual no servidor. No Windows, consulta o WMI local pela API COM do sistema via `pywin32`; isso não habilita nem usa WinRM remoto. Para testar em laboratório, instale as dependências Python no computador-alvo (`pip install -r agent-requirements.txt`), configure `RADAR_AGENT_ENROLLMENT_TOKEN` no `.env` do servidor e inicie o servidor. Dentro da cópia do projeto no computador a registrar, execute:

```bash
python -m agent.client --register --server-url http://IP-DO-SERVIDOR:5000 --allow-insecure-http
```

O programa solicitará o token de registro sem exibi-lo. Gere um segredo com `python -c "import secrets; print(secrets.token_urlsafe(32))"`, salve-o apenas em `RADAR_AGENT_ENROLLMENT_TOKEN` no `.env` do servidor e recrie o container com `docker compose up -d --force-recreate inventario-app`. Depois que os agentes autorizados forem registrados, remova esse segredo do `.env` e recrie o container; os tokens individuais continuam funcionando.

Para uma coleta pontual manual, use:

```bash
python -m agent.client --once --allow-insecure-http
```

Os scripts abaixo instalam o agente para iniciar junto com o sistema e repetir a coleta a cada 15 minutos. Execute-os somente após registrar a rede e o certificado autorizados com os responsáveis pela infraestrutura.

No Windows, abra PowerShell como administrador na raiz do projeto. O agente roda como a conta interna `SYSTEM` pela Tarefa Agendada; não cria usuário local nem armazena a senha do administrador. Para o laboratório doméstico sem HTTPS:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-agent-windows.ps1 -ServerUrl "http://IP-DO-SERVIDOR:5000" -AllowInsecureHttp
```

Para HTTPS com CA interna confiável, omita `-AllowInsecureHttp` e informe `-CaBundle "C:\caminho\empresa-ca.pem"`. O script pedirá o token inicial de registro sem exibi-lo, instalará as dependências em um ambiente virtual separado e criará a tarefa `RADAR Agent`. O arquivo de estado e o log ficam em `%ProgramData%\RADAR`; acesso limitado a `SYSTEM` e Administradores. Para verificar a tarefa, use `Get-ScheduledTask -TaskName 'RADAR Agent'`; o log pode ser lido com `Get-Content "$env:ProgramData\RADAR\agent.log" -Wait`.

No Linux com systemd, execute como root (por exemplo, com `sudo`). O serviço roda sob a conta interna `root` para ler os identificadores de hardware locais; não cria outro usuário nem guarda senha. Para HTTPS:

```bash
sudo ./scripts/install-agent-linux.sh --server-url https://radar.empresa.local --ca-bundle /caminho/empresa-ca.pem
```

Em laboratório doméstico sem HTTPS, acrescente `--allow-insecure-http`. O token inicial será solicitado sem aparecer no terminal. O serviço `radar-agent.service` inicia no boot, reinicia após falhas e registra eventos no journal: `journalctl -u radar-agent.service -f`. O arquivo de estado, que contém o token individual, fica em `/var/lib/radar-agent/agent.json` com acesso restrito a root.

No modo manual, o estado do agente fica em `~/.radar/agent.json` (ou no caminho informado por `--state-file`/`RADAR_AGENT_STATE`) e contém o token individual desse computador. Proteja esse arquivo; não o envie ao GitHub nem o compartilhe. Os instaladores pedem elevação local porque configuram uma tarefa ou serviço e protegem o arquivo de estado. O uso de HTTP é permitido **somente para laboratório isolado**. Não instale agentes na rede empresarial até a equipe aprovar o procedimento e o servidor HTTPS com certificado confiável estar disponível.

O arquivo `.env` é ignorado pelo Git. A configuração atual aceita uma sub-rede e uma community v1/v2c; suporte a várias sub-redes e perfis SNMP v3 ainda será implementado. A varredura consulta SNMP e tenta ping na faixa autorizada. Hosts que respondem somente ao ping aparecem como **Host sem coleta** até o agente ser instalado; ICMP bloqueado pode esconder hosts, então peça também à equipe de rede uma lista DHCP quando disponível. Para SNMP, o servidor precisa de rota até a rede e os equipamentos/firewalls devem permitir UDP 161. Para habilitar TLS direto no servidor, forneça certificado e chave PEM em `certs/` (não versionada) e preencha `RADAR_TLS_CERT_FILE=/app/certs/server.crt` e `RADAR_TLS_KEY_FILE=/app/certs/server.key` no `.env`; os computadores clientes precisam confiar na CA que emitiu o certificado. Para TLS em proxy reverso, configure `RADAR_COOKIE_SECURE=true` para o navegador enviar o cookie de sessão somente por HTTPS. Se a rede da empresa se sobrepuser à rede Docker `172.20.0.0/24`, será necessário ajustar a rede do Compose antes de iniciar.

Para voltar ao cenário simulado padrão, remova ou renomeie `.env`; o Compose usará `172.20.0.0/24` e `public`.

## Segurança

Configure somente redes autorizadas. Credenciais SNMP não são as senhas de administrador do Windows ou Linux. Não armazene segredos em arquivos versionados, issues ou relatórios. SNMP v1/v2c não protegem a community com criptografia; prefira SNMPv3 com autenticação e privacidade quando houver suporte.

O coletor WMI/WinRM existe apenas como validação complementar de laboratório e ainda usa credenciais configuradas no ambiente; não é o mecanismo planejado para implantação em escala. O painel exige uma conta local, guarda senhas como hash e separa permissões de administrador e usuário. A API do agente autentica cada instalação com token individual. O token inicial de registro deve ser removido do ambiente do servidor após a etapa de cadastro dos agentes. Mantenha a aplicação somente no laboratório até que HTTPS e os scripts de instalação do agente sejam validados no ambiente-alvo. O acesso ao banco SQLite e ao arquivo de estado de cada agente também deve ser restrito às contas do sistema operacional que executam esses componentes.

## Documentação

- [Requisitos do MVP](docs/requisitos-mvp.md)
- [Registro de validação em laboratório](docs/validacao-laboratorio.md)
- [README do protótipo original](docs/prototipo-base.md)

## Prazo acadêmico

O prazo informado para o projeto é **29/11/2026**. A documentação acadêmica será atualizada conforme os resultados de pesquisa e do piloto, seguindo as normas ABNT aplicáveis.
