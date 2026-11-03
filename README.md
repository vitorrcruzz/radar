# 📡 R.A.D.A.R.

<p align="center">
  <strong>Rastreamento Automático de Ativos de Rede</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white" alt="Servidor Python 3.11" />
  <img src="https://img.shields.io/badge/Flask-3.0-000000?logo=flask&logoColor=white" alt="Flask 3.0" />
  <img src="https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white" alt="SQLite 3" />
  <img src="https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white" alt="Docker Compose" />
  <img src="https://img.shields.io/badge/Coleta-Agente%20%2B%20SNMP-0891B2" alt="Coleta por agente e SNMP" />
  <img src="https://img.shields.io/badge/Status-Piloto%20em%20valida%C3%A7%C3%A3o-F59E0B" alt="Piloto em validação" />
</p>

<p align="center">
  Inventário de TI, identificação de equipamentos e acompanhamento da rede em um só painel.
</p>

<p align="center">
  <a href="#sobre">Sobre</a> ·
  <a href="#funcionalidades">Funcionalidades</a> ·
  <a href="#arquitetura">Arquitetura</a> ·
  <a href="#instalacao">Instalação</a> ·
  <a href="#agente">Agente Windows</a> ·
  <a href="#documentacao">Documentação</a> ·
  <a href="#autores">Autores</a>
</p>

---

<a id="sobre"></a>
## 🔎 Sobre o projeto

O **R.A.D.A.R.** é uma aplicação web para inventariar ativos de TI. Reúne informações coletadas por um agente próprio nos computadores e por consultas SNMP nos equipamentos de rede, permitindo consultar o inventário, acompanhar o status e complementar os cadastros manualmente.

Desenvolvido como **Trabalho de Conclusão de Curso**, o projeto evoluiu do [protótipo original com dispositivos simulados](https://github.com/vitorrcruzz/Inventario-de-TI-TCC-FATEC-Osasco-2026) para um piloto em equipamentos reais da **CH3 Construtora**. O Compose atual executa somente a aplicação, sem os simuladores do protótipo.

> **Situação em 03/11/2026:** piloto em validação, com computadores Windows e roteador consultado por SNMP. A cobertura depende dos agentes instalados, dos protocolos disponíveis e das redes configuradas. O sistema não representa um inventário integral automático de qualquer rede.

<a id="funcionalidades"></a>
## 🧩 Funcionalidades

| Recurso | O que oferece |
|---|---|
| **Dashboard** | Totais de equipamentos, status online/offline, distribuição por tipo e gráfico das últimas varreduras. |
| **Inventário de equipamentos** | Consulta de hostname, IP, MAC, número de série, modelo, processador, memória, armazenamento e sistema operacional, conforme disponibilidade da fonte. |
| **Agente próprio** | Coleta local e envio periódico do inventário à API, com token individual por equipamento. |
| **Coleta SNMP** | Consulta de equipamentos de rede que tenham SNMP habilitado e credenciais compatíveis. |
| **Identidade e mudança de IP** | Conciliação por MAC e número de série, registro de mudanças de IP e tratamento de conflitos. |
| **Redes e status** | Identificação das redes configuradas e expiração do status quando o agente deixa de enviar coletas. |
| **Edição manual** | Complementação de informações do equipamento, preservando os campos manuais nas atualizações automáticas. |
| **Windows** | Edição, estado de ativação e expiração quando informada pelo próprio sistema operacional. |
| **Softwares cadastrados** | Registro manual de programas como AutoCAD e Archicad, com informações de versão e licença. |
| **Usuários e permissões** | Login e gerenciamento de contas pelo administrador, com perfis de administrador e usuário comum. |
| **Histórico** | Pesquisa, ordenação e paginação no servidor, com 15 registros por página inicialmente. |
| **Retenção** | Limite configurável de resumos de varreduras concluídas; padrão de 500 registros. |
| **Exportação** | Rotas de CSV e Excel disponíveis, com pendências de adequação aos campos recentes e às correções manuais. |

A interface possui temas claro e escuro e ajustes de responsividade. A experiência em dispositivos móveis ainda precisa de validação em aparelhos reais.

<a id="arquitetura"></a>
## 🏗️ Tecnologias e arquitetura

| Camada | Tecnologias |
|---|---|
| Interface | HTML, CSS, JavaScript, Bootstrap, DataTables e Chart.js |
| Aplicação e API | Python e Flask |
| Persistência | SQLite e SQLAlchemy |
| Coleta local | Python, psutil e WMI via COM no Windows |
| Coleta de rede | PySNMP; descoberta ICMP opcional |
| Agendamento | APScheduler no servidor e tarefa agendada no Windows |
| Exportação | pandas e openpyxl |
| Implantação | Docker Compose em servidor Linux |

```text
Computadores Windows                 Equipamentos de rede
        │                                      ▲
        │ Agente: inventário local             │ Consultas SNMP
        ▼                                      │
  HTTPS + token individual ──────► Servidor R.A.D.A.R.
                                   Python + Flask
                                         │
                            ┌────────────┼────────────┐
                            ▼            ▼            ▼
                          SQLite    Agendador     Painel web
                                                   navegador
```

### Como a coleta funciona

**Nos computadores:** o agente consulta os dados localmente e os envia ao servidor. No Windows, utiliza WMI via COM, sem depender de WinRM remoto. A instalação cria a tarefa `RADAR Agent`, executada como SYSTEM. A senha administrativa utilizada para instalar o agente não fica armazenada por ele.

**Nos equipamentos de rede:** o servidor consulta SNMP. O coletor aceita perfis v1, v2c e v3, mas a rotina integrada ao painel utiliza a community v2c configurada. Nem todos os equipamentos disponibilizam os mesmos campos.

**No painel:** os dados recebidos são associados aos cadastros dos dispositivos. As regras de identidade verificam MAC e serial antes de tratar mudanças de IP; situações ambíguas podem exigir revisão. O status de agentes considera a última coleta e o tempo de tolerância configurado, não sendo uma indicação instantânea de desconexão.

Há um alvo de sub-rede para a varredura. As redes autorizadas a enviar inventários dos agentes são configuradas separadamente. A descoberta ICMP é opcional e vem desativada.

## 🗂️ Estrutura do projeto

```text
radar/
├── agent/                    # Cliente de registro e envio do inventário
├── backend/
│   ├── app.py                # Inicialização da aplicação e do agendador
│   ├── models.py             # Modelos do banco de dados
│   ├── device_identity.py    # Identidade dos ativos e conciliação de IPs
│   ├── history_retention.py  # Retenção dos resumos de varreduras
│   ├── migrations.py         # Migrações de estrutura do banco
│   ├── routes/               # API, autenticação, agentes e cadastros
│   ├── templates/            # Páginas HTML
│   └── static/               # Estilos e scripts da interface
├── collector/                # Coletores locais, SNMP e descoberta de rede
├── scripts/                  # Instalação, atualização e manutenção
├── tests/                    # Testes de regressão
├── docs/                     # Documentação técnica e material do TCC
├── database/                 # Banco e backups locais, fora do Git
├── exports/                  # Arquivos gerados na execução
├── .env.example              # Modelo de configuração
├── agent-requirements.txt    # Dependências do agente
├── requirements.txt          # Dependências do servidor
├── Dockerfile
└── docker-compose.yml
```

<a id="instalacao"></a>
## 🚀 Como executar o servidor

### 1. Preparar o projeto

Utilize um servidor com **Docker e Docker Compose**. O Python do servidor é instalado na imagem Docker.

```bash
git clone https://github.com/vitorrcruzz/radar.git
cd radar
cp .env.example .env
```

### 2. Configurar o ambiente

Edite o `.env` antes de iniciar. Configure a rede, a community SNMP, os segredos da aplicação e os certificados para HTTPS. O exemplo de configuração não substitui os valores da sua instalação.

| Variável | Finalidade |
|---|---|
| `SCAN_NETWORK` | Sub-rede consultada pela varredura. |
| `SCAN_COMMUNITY` | Community de leitura SNMP compatível com os equipamentos. |
| `SCAN_INTERVAL` | Intervalo entre varreduras, em segundos; padrão do Compose: 300. |
| `RADAR_AGENT_ALLOWED_NETWORKS` | Redes autorizadas para os agentes, em CIDR. |
| `RADAR_NETWORK_LABELS` | Rótulos das redes apresentados no painel. |
| `AGENT_OFFLINE_AFTER_SECONDS` | Tolerância sem coleta antes de marcar o agente offline; padrão: 900 segundos. |
| `HISTORICO_MAX_REGISTROS` | Resumos concluídos mantidos; padrão: 500. O valor `0` desativa a retenção. |
| `RADAR_AGENT_ENROLLMENT_TOKEN` | Segredo utilizado no registro inicial dos agentes. |
| `RADAR_SECRET_KEY` | Chave da aplicação para assinatura das sessões. |
| `RADAR_TLS_CERT_FILE` / `RADAR_TLS_KEY_FILE` | Caminhos do certificado e da chave TLS dentro do contêiner. |
| `RADAR_COOKIE_SECURE` | Uso de cookies de sessão restritos a HTTPS. |

Consulte o [.env.example](.env.example) e a [documentação operacional](docs/documentacao-atual-2026-10-27.md) para os formatos, caminhos de certificados e demais opções.

### 3. Iniciar e criar o primeiro administrador

```bash
docker compose up -d --build inventario-app

docker compose exec inventario-app python -m backend.create_user \
  --nome "Administrador" --email admin@exemplo.local --perfil admin
```

A senha será solicitada pelo terminal sem aparecer nos argumentos. Após o primeiro login, utilize o menu **Usuários** para cadastrar outras contas.

Com HTTPS configurado, acesse `https://IP_DO_SERVIDOR:5000`. No piloto, o servidor utiliza o endereço reservado `192.168.1.35`; adapte os exemplos à sua rede.

### Atualizar a aplicação

O código é copiado para a imagem Docker. Depois de atualizar os arquivos no servidor, execute:

```bash
docker compose up -d --build inventario-app
```

Atualize o navegador com **Ctrl+F5** após mudanças na interface. Fazer um commit registra o código no Git; não atualiza automaticamente outra instalação nem reconstrói a imagem.

<a id="agente"></a>
## 💻 Agente Windows

**Instale o Python manualmente antes de executar o instalador.** O script não utiliza winget nem baixa o interpretador.

Prepare o pacote com esta estrutura:

```text
C:\radar\
├── agent\
├── collector\
├── scripts\
├── agent-requirements.txt
└── radar-ca.crt              # CA pública, quando necessária
```

Não distribua o `.env`, o banco de dados nem a chave TLS privada do servidor com esse pacote. O token de registro é informado durante a instalação.

Execute no **PowerShell como administrador**, ajustando o endereço e o caminho real do Python:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\radar\scripts\install-agent-windows.ps1" -ServerUrl "https://192.168.1.35:5000" -CaBundle "C:\radar\radar-ca.crt" -PythonPath "C:\Program Files\Python314\python.exe"
```

### Atualizar um agente existente

Copie o pacote atualizado para a máquina e execute:

```powershell
& "C:\radar\scripts\update-agent-windows.ps1" -ProjectPath "C:\radar"
```

O atualizador preserva a identidade e o token do agente e copia o código. Ele **não atualiza automaticamente as dependências**. Mudanças apenas no servidor não exigem reinstalar os agentes, desde que o protocolo permaneça compatível.

| Item | Localização |
|---|---|
| Tarefa agendada | `RADAR Agent` |
| Instalação | `%ProgramFiles%\RADAR` |
| Estado e credencial individual | `%ProgramData%\RADAR\agent.json` |
| Log | `%ProgramData%\RADAR\agent.log` |

Há também coletor local Linux e instalador systemd; sua implantação precisa de validação específica.

## 🔐 Dados e segurança

O banco `database/inventario.db` permanece no host por meio de volume Docker. Contém contas, inventário, histórico e hashes dos tokens dos agentes. **Excluir o banco e iniciar uma base vazia impede reconhecer os agentes anteriormente registrados.**

Faça backups consistentes do SQLite e preserve as configurações necessárias à recuperação. O `.env`, os bancos, backups e certificados locais ficam fora do versionamento.

O acesso ao painel usa sessões e perfis de usuário. Os agentes utilizam tokens individuais e validações de rede. A expiração do status online não desativa nem remove o cadastro do equipamento.

<details>
<summary><strong>📋 Limites e pendências atuais</strong></summary>

- O servidor ainda utiliza o servidor embutido do Flask. A migração para um servidor de produção está planejada, mas não foi implementada.
- O piloto ainda exige avaliação de estabilidade, cobertura e desempenho; não há garantia de capacidade para qualquer quantidade de ativos.
- A coleta SNMP depende das informações expostas por cada equipamento. Campos ausentes podem precisar de preenchimento manual.
- A lista de programas instalados é cadastrada manualmente; o agente não realiza esse levantamento automaticamente.
- A ativação do Windows não comprova titularidade comercial da licença e não representa o calendário de suporte da Microsoft. A expiração só é preenchida quando informada pelo Windows.
- As exportações precisam incorporar as correções manuais e os campos recentes e passar por validação específica.
- A retenção automática abrange os resumos de varreduras concluídas. Coletas de agentes e varreduras sem finalização não são apagadas por essa política.
- A interface móvel e o agente Linux precisam de validação adicional.

</details>

## 🧪 Validação

Os testes cobrem registro de agentes, autenticação e conflitos de identidade/IP, migração do banco, paginação e retenção do histórico. Há também uma verificação JavaScript para reutilização dos gráficos nas atualizações do dashboard.

Em um ambiente Python com as dependências do projeto instaladas:

```bash
python -m unittest discover -s tests -q
```

Com Node.js disponível para a verificação JavaScript:

```bash
node tests/test_chart_refresh.js
```

Node.js é utilizado nesse teste, não para executar o servidor RADAR. Os testes automatizados complementam a avaliação no ambiente real, sem substituí-la.

<a id="documentacao"></a>
## 📚 Documentação e TCC

| Material | Conteúdo |
|---|---|
| [Documentação técnica e operacional](docs/documentacao-atual-2026-10-27.md) | Base consolidada de arquitetura, API, configuração, instalação e operação. |
| [Documento Word](docs/Documentacao_RADAR_2026-10-27.docx) | Material para complementar a documentação acadêmica. |
| [Arquitetura ilustrada](docs/figuras/arquitetura-radar-atual.png) | Diagrama da arquitetura documentada. |
| [Modelo de dados](docs/figuras/modelo-dados-radar.png) | Diagrama de referência das entidades. |
| [Identidade e mudança de IP](docs/identidade-e-mudanca-de-ip.md) | Atualização das regras de identificação e conciliação de endereços. |
| [Histórico e desempenho](docs/historico-paginado.md) | Paginação, retenção e otimização das atualizações dos gráficos. |

A documentação consolidada e o Word têm data de **27/10/2026**. Consulte também os adendos para as mudanças posteriores; os diagramas e documentos anteriores podem não representar todos os campos atuais.

## 🕘 Origem e evolução

O R.A.D.A.R. teve origem no projeto **Inventário de TI — FATEC Osasco 2026**, desenvolvido por **Sabrina de França Santos e Vitor Cruz** em um ambiente simulado com Docker e SNMP.

🔗 **[Acessar o repositório do projeto original](https://github.com/vitorrcruzz/Inventario-de-TI-TCC-FATEC-Osasco-2026)**

O protótipo explorava o fluxo de consulta SNMP, armazenamento dos dados e apresentação em um dashboard. A evolução para o R.A.D.A.R. trouxe a aplicação em equipamentos reais da CH3 Construtora, coleta por agentes nos computadores, autenticação, edição manual e tratamento de mudanças de IP.

Os projetos estão em **repositórios separados**. O repositório original é uma referência histórica da etapa simulada; as instruções para instalar e operar o R.A.D.A.R. estão neste repositório.

<details>
<summary><strong>Documentos das etapas anteriores</strong></summary>

- [Requisitos iniciais do MVP](docs/requisitos-mvp.md): planejamento original, incluindo recursos ainda não implementados e decisões alteradas posteriormente.
- [Validação de laboratório](docs/validacao-laboratorio.md): testes de SNMP e WinRM anteriores à implantação dos agentes.
- [Protótipo original](docs/prototipo-base.md): ambiente simulado utilizado no início do desenvolvimento.

O prazo acadêmico informado é **29/11/2026**. As conclusões do TCC devem refletir os casos efetivamente avaliados, sem atribuir cobertura total ou ganhos não medidos ao sistema.

</details>

<a id="autores"></a>
## 👩‍💻 Autores

| Nome | GitHub |
|---|---|
| Sabrina de França Santos | [@sabs0303](https://github.com/sabs0303) |
| Vitor Cruz | [@vitorrcruzz](https://github.com/vitorrcruzz) |

## 🏫 Instituição e orientação

**FATEC Osasco — Prefeito Hirant Sanazar**<br />
Curso Superior de Tecnologia em Redes de Computadores<br />
Disciplina: Projeto de Redes de Computadores<br />
Orientador: **Leandro Palha**<br />
Ano: **2026**

O R.A.D.A.R. integra o trabalho **“A Automação como Suporte à Gestão de Inventário de Equipamentos de TI”**. Sua origem acadêmica está vinculada à FATEC Osasco; a **CH3 Construtora** é o ambiente de aplicação do piloto com equipamentos reais.

---

<p align="center">
  <strong>R.A.D.A.R. — Rastreamento Automático de Ativos de Rede</strong><br />
  Desenvolvido por Sabrina de França Santos e Vitor Cruz<br />
  FATEC Osasco · 2026 · Piloto na CH3 Construtora<br />
  <a href="https://github.com/vitorrcruzz/radar">Código-fonte no GitHub</a>
</p>
