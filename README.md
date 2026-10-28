# R.A.D.A.R. — Rastreamento Automático de Ativos de Rede

Aplicação de inventário de TI em Python com painel web, banco SQLite, coleta por agente próprio em computadores Windows/Linux e consultas SNMP complementares. O ambiente piloto atual é a **CH3 Construtora**.

**Situação em 27/10/2026:** piloto com coleta de computadores reais, autenticação e perfis, cadastro de usuários pelo administrador, edição manual de equipamentos e registro manual de softwares. O projeto ainda possui pendências de exportação, implantação definitiva e avaliação de cobertura e desempenho. A interface para celular recebeu ajustes que precisam ser conferidos em aparelhos reais.

## Documentação atual

A referência consolidada para o funcionamento e os limites atuais é:

- [Documentação técnica e operacional completa](docs/documentacao-atual-2026-10-27.md)
- [Documento Word para complementar o TCC](docs/Documentacao_RADAR_2026-10-27.docx)
- [Arquitetura atual](docs/figuras/arquitetura-radar-atual.png)
- [Modelo de dados](docs/figuras/modelo-dados-radar.png)

O documento completo descreve arquitetura, fontes de coleta, dados de licença, API, configuração, instalação, atualização de agentes, backup, recuperação, segurança, diagnóstico e pendências. Inclui textos sugeridos para o TCC e referências técnicas primárias.

## Funcionamento

O agente Windows consulta WMI localmente por COM e envia o inventário por HTTPS à API. Ele não depende de habilitação de WinRM remoto na estação nem armazena a senha administrativa usada na instalação. Uma tarefa agendada executa o agente como SYSTEM. No Linux, há coletor local e instalador systemd, cuja implantação precisa de validação específica.

O servidor também pode consultar equipamentos com SNMP. O coletor Python aceita perfis v1, v2c e v3, mas a rotina integrada ao painel usa a community v2c configurada. Há uma sub-rede de varredura; a lista de redes autorizadas dos agentes é independente desse alvo. A descoberta ICMP é opcional e vem desligada.

O administrador pode complementar dados e cadastrar softwares como AutoCAD e Archicad. O agente não coleta automaticamente a lista de programas. O estado de ativação do Windows não comprova titularidade comercial e não corresponde ao calendário de suporte Microsoft. A data de expiração só é coletada quando informada pelo Windows.

## Início rápido do servidor

O Compose atual inicia somente a aplicação, sem simuladores. Prepare `.env` a partir do exemplo e configure redes, segredos e HTTPS antes de instalar agentes:

```bash
cp .env.example .env
docker compose up -d --build inventario-app
```

Crie o primeiro administrador; a senha será solicitada sem aparecer nos argumentos:

```bash
docker compose exec inventario-app python -m backend.create_user \
  --nome "Administrador" --email admin@exemplo.local --perfil admin
```

Depois do primeiro login, o menu **Usuários** permite cadastrar outras contas com perfil administrador ou usuário comum. O IP reservado do servidor no piloto é `192.168.1.35`, e a rede inicial é `192.168.1.0/24`. Esses endereços devem ser adaptados em outras instalações.

O código é copiado para a imagem. Depois de atualizar os arquivos no host Linux, reconstrua e recrie o serviço para incorporar mudanças:

```bash
docker compose up -d --build --force-recreate inventario-app
```

A execução nativa por Python também existe. Os procedimentos completos, os caminhos de certificados e as diferenças entre commit, atualização de arquivos e reconstrução estão na documentação consolidada.

## Agentes Windows

Instale Python manualmente antes do agente. O instalador não utiliza winget nem baixa o interpretador. O pacote precisa de `agent/`, `collector/`, `scripts/`, `agent-requirements.txt` e da CA pública quando necessária; não inclua `.env`, banco, tokens ou chave TLS privada do servidor.

Execute em PowerShell como administrador, adaptando o caminho real do Python:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\radar\scripts\install-agent-windows.ps1" -ServerUrl "https://192.168.1.35:5000" -CaBundle "C:\radar\radar-ca.crt" -PythonPath "C:\Program Files\Python314\python.exe"
```

Para atualizar uma instalação existente preservando identidade e token:

```powershell
& "C:\radar\scripts\update-agent-windows.ps1" -ProjectPath "C:\radar"
```

A tarefa é `RADAR Agent`. O estado e o log ficam em `%ProgramData%\RADAR`. O atualizador copia código; ele não atualiza dependências automaticamente.

## Persistência e limitações

O banco `database/inventario.db` é persistido no host. Ele contém contas, inventário e hashes das credenciais dos agentes. Apagá-lo e criar uma base vazia impede o reconhecimento dos agentes já registrados. Faça backup consistente e preserve também as configurações necessárias à recuperação.

A pasta `database/`, o `.env`, os certificados locais e outros dados de execução são ignorados pelo Git. Código do agente e scripts de instalação são arquivos versionados e devem ser revisados ao preparar cada commit.

A revisão atual identificou que `backend/routes/export.py` referencia `Dispositivo` sem importá-lo. As exportações também precisam aplicar as correções manuais e incluir os campos recentes. Essas rotas não devem ser consideradas homologadas antes da correção e validação. A documentação registra outras limitações, como ausência de retenção, conciliação completa de IPs e uso do servidor embutido Flask.

## Registros históricos

- [Requisitos iniciais do MVP](docs/requisitos-mvp.md): planejamento; inclui recursos ainda não implementados e decisões posteriormente alteradas.
- [Validação de laboratório em 07/10/2026](docs/validacao-laboratorio.md): prova SNMP e WinRM anterior à implantação dos agentes.
- [Protótipo original](docs/prototipo-base.md): referência histórica de simulação; não descreve o funcionamento atual.

O prazo acadêmico informado para o projeto é **29/11/2026**. Dados do piloto e conclusões acadêmicas devem refletir os casos efetivamente avaliados, sem atribuir cobertura total, ganhos ambientais ou capacidade de produção sem evidências.
