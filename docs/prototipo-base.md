# R.A.D.A.R. — Rastreamento Automático de Ativos de Rede

> **Estado do projeto:** migração do protótipo para um sistema multiplataforma em andamento. O código herdado ainda usa Docker para simulação e contém componentes que precisam ser substituídos antes do uso real. Não use o estado atual para varrer uma rede de produção.

Os requisitos do MVP acordados estão em [`docs/requisitos-mvp.md`](docs/requisitos-mvp.md). O piloto será executado na máquina conectada à rede monitorada e acessado pelo navegador na rede local. A aplicação principal deverá funcionar em Linux e Windows sem Docker; Docker ficará disponível como apoio opcional para simular dispositivos.

**Prazo acadêmico informado:** 29/11/2026.  
**Repositório:** RADAR — R.A.D.A.R.

---

## Estado herdado do protótipo

As seções abaixo descrevem o projeto base importado. Elas ainda não representam funcionalidades prontas para uso real. A documentação será atualizada conforme a migração avance.

---

## Referência do protótipo original

O texto a seguir foi mantido temporariamente como referência funcional e técnica do projeto-base.

---

### Protótipo Inventário de TI — FATEC Osasco 2026

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Flask-3.0-black?logo=flask&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-29.3-2496ED?logo=docker&logoColor=white" />
  <img src="https://img.shields.io/badge/SNMP-MIB--II-green" />
  <img src="https://img.shields.io/badge/SQLite-3-003B57?logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/Status-Em%20desenvolvimento-yellow" />
</p>

> **TCC — Redes de Computadores · FATEC Osasco · 2026**  
> Automação de inventário de equipamentos de TI via protocolo SNMP com dashboard web, alertas de licença e exportação de relatórios.

---

## 📋 Sobre o projeto

**A Automação como Suporte à Gestão de Inventário de Equipamentos de TI** é um sistema desenvolvido em Python que realiza varreduras automáticas em redes locais utilizando o protocolo **SNMP**, coleta informações dos equipamentos detectados, armazena em banco de dados e exibe tudo em um **dashboard web** interativo.

O ambiente de testes é 100% containerizado via **Docker**, simulando equipamentos reais como switches Cisco, roteadores MikroTik, computadores, impressoras, câmeras IP, nobreaks e access points — sem necessidade de infraestrutura física.

### ✨ Funcionalidades

- 🔍 **Varredura automática** via SNMP a cada intervalo configurável
- 🖱️ **Varredura manual** pelo dashboard com um clique
- 📊 **Dashboard web** com gráficos, tabelas filtráveis e detalhes por dispositivo
- 🔑 **Gestão de licenças** com alertas visuais por proximidade de vencimento
- 📁 **Exportação** de relatórios em CSV e Excel formatado
- 🕐 **Histórico** completo de todas as varreduras realizadas
- 🐳 **Ambiente simulado** com Docker para testes sem hardware físico

---

## 🖼️ Screenshots

### Dashboard principal

<img width="900" height="650" alt="prototipo dashboard" src="https://github.com/user-attachments/assets/ffb33a59-e747-4269-9e35-201a12b59481" />

### Tabela de dispositivos
- IP, Hostname, Tipo, Status, Modelo, Sistema Op., Processador, Memória, Armazenamento, **Licença**, Uptime
- Clique em qualquer linha para ver todos os detalhes em modal
- Filtros por tipo e status

### Alertas de licença
| Badge | Significado |
|---|---|
| 🟢 Verde (X dias) | Licença válida, mais de 90 dias |
| 🟡 Amarelo (X dias) | Atenção — menos de 90 dias |
| 🔴 Vermelho (X dias) | Crítico — menos de 30 dias |
| 🔴 Expirada | Licença vencida |

---

## 🏗️ Arquitetura

```
Dispositivos simulados (Docker/snmpsim)
        ↓  SNMP UDP 161
  Python: snmp_scanner.py
        ↓  dados coletados
  Python: SQLAlchemy → SQLite
        ↓  consulta ao banco
  Python: Flask → Dashboard Web
        ↓  HTTP :5000
  Navegador: Dashboard + Exportação
```

---

## 🗂️ Estrutura do projeto

```
inventario-ti/
├── docker-compose.yml          # Orquestra todos os containers
├── Dockerfile                  # Imagem da aplicação Python
├── requirements.txt            # Dependências Python
│
├── snmp-data/                  # Dados SNMP dos dispositivos simulados
│   ├── switch.snmprec          # Cisco Catalyst 2960
│   ├── router.snmprec          # MikroTik RouterBOARD
│   ├── pc1.snmprec             # Workstation Windows 10
│   ├── pc2.snmprec             # Workstation Ubuntu 22.04
│   ├── printer.snmprec         # HP LaserJet Pro M404dn
│   ├── ap.snmprec              # Ubiquiti UniFi AP-AC-Pro
│   ├── camera.snmprec          # Hikvision DS-2CD2143G2-I
│   └── nobreak.snmprec         # APC Smart-UPS 1500VA
│
├── collector/
│   └── snmp_scanner.py         # Módulo de varredura SNMP
│
├── backend/
│   ├── app.py                  # Inicialização Flask + APScheduler
│   ├── models.py               # Modelos SQLAlchemy
│   ├── database.py             # Instância do SQLAlchemy
│   ├── seed.py                 # Dados fixos (infraestrutura + offline)
│   ├── routes/
│   │   ├── dashboard.py        # Rota principal
│   │   ├── devices.py          # API REST de dispositivos
│   │   ├── scan.py             # Varredura manual e automática
│   │   └── export.py           # Exportação CSV e Excel
│   ├── templates/
│   │   └── index.html          # Dashboard web
│   └── static/
│       ├── css/style.css       # Estilos visuais
│       └── js/main.js          # Lógica JavaScript
│
├── database/                   # Banco SQLite (gerado automaticamente)
└── exports/                    # Arquivos exportados
```

---

## 🔧 Dispositivos simulados

| IP | Container | Hostname | Tipo |
|---|---|---|---|
| 172.20.0.2 | inventario-ti-app | SRV-INVENTARIO | Servidor |
| 172.20.0.10 | sim-switch-cisco | SW-LAB-01 | Switch |
| 172.20.0.11 | sim-roteador-mikrotik | RTR-FATEC-01 | Roteador |
| 172.20.0.12 | sim-pc-windows-1 | PC-LAB-01 | Computador |
| 172.20.0.13 | sim-pc-windows-2 | PC-LAB-02 | Servidor |
| 172.20.0.14 | sim-impressora-hp | IMP-LAB-01 | Impressora |
| 172.20.0.15 | sim-ap-wifi | AP-LAB-01 | Access Point |
| 172.20.0.16 | sim-camera-ip | CAM-LAB-01 | Câmera IP |
| 172.20.0.17 | sim-nobreak-apc | UPS-LAB-01 | Nobreak |
| 172.20.0.20 | — (offline) | NB-LAB-01 | Notebook |
| 172.20.0.21 | — (offline) | NB-LAB-02 | Notebook |
| 172.20.0.22 | — (offline) | PC-LAB-03 | Computador |
| 172.20.0.23 | — (offline) | IMP-LAB-02 | Impressora |
| 172.20.0.24 | — (offline) | FW-LAB-01 | Firewall |

---

## 🚀 Como executar

### Pré-requisitos

- [Docker Engine](https://docs.docker.com/engine/install/) 20.x ou superior
- [Docker Compose](https://docs.docker.com/compose/install/) v2.x ou superior

### Passo a passo

```bash
# 1. Clone o repositório
git clone https://github.com/vitorrcruzz/Inventario-de-TI-TCC-FATEC-Osasco-2026.git
cd inventario-ti

# 2. Suba todos os containers
docker compose up --build

# 3. Acesse o dashboard
http://localhost:5000

# 4. Clique em "Escanear Agora" para a primeira varredura
```

### Parar o projeto
```bash
docker compose down
```

### Ver logs em tempo real
```bash
docker compose logs -f inventario-app
```

### Resetar o banco de dados
```bash
rm database/inventario.db
docker compose down
docker compose up --build
```

---

## 🌐 API REST

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Dashboard web |
| GET | `/api/dispositivos` | Lista todos os dispositivos |
| GET | `/api/dispositivos?tipo=Switch` | Filtra por tipo |
| GET | `/api/dispositivos?status=online` | Filtra por status |
| GET | `/api/dispositivos/<id>` | Detalhes de um dispositivo |
| GET | `/api/stats` | Estatísticas gerais |
| GET | `/api/historico` | Últimas 20 varreduras |
| POST | `/api/scan` | Dispara varredura manual |
| GET | `/api/export/csv` | Download CSV |
| GET | `/api/export/excel` | Download Excel formatado |

---

## ⚙️ Variáveis de ambiente

Configuráveis no `docker-compose.yml`:

| Variável | Padrão | Descrição |
|---|---|---|
| `SCAN_NETWORK` | `172.20.0.0/24` | Sub-rede a ser escaneada |
| `SCAN_COMMUNITY` | `public` | Community string SNMP |
| `SCAN_INTERVAL` | `300` | Intervalo de varredura em segundos |
| `TZ` | `America/Sao_Paulo` | Fuso horário |

---

## 🏷️ OIDs SNMP coletados

| OID | Nome | Informação |
|---|---|---|
| 1.3.6.1.2.1.1.1.0 | sysDescr | Descrição do sistema |
| 1.3.6.1.2.1.1.3.0 | sysUpTime | Tempo de atividade |
| 1.3.6.1.2.1.1.4.0 | sysContact | Contato do responsável |
| 1.3.6.1.2.1.1.5.0 | sysName | Hostname |
| 1.3.6.1.2.1.1.6.0 | sysLocation | Localização física |
| 1.3.6.1.2.1.2.1.0 | ifNumber | Número de interfaces |
| 1.3.6.1.2.1.4.1.0 | ipForwarding | É roteador? |
| 1.3.6.1.99.1.1.0 | (custom) | Modelo do equipamento |
| 1.3.6.1.99.1.2.0 | (custom) | Sistema operacional |
| 1.3.6.1.99.1.3.0 | (custom) | Armazenamento |
| 1.3.6.1.99.1.4.0 | (custom) | Memória RAM |
| 1.3.6.1.99.1.5.0 | (custom) | Processador |

---

## 📦 Tecnologias utilizadas

| Camada | Tecnologia |
|---|---|
| Linguagem | Python 3.11 |
| Web | Flask 3.0 + Jinja2 |
| Banco de dados | SQLite via SQLAlchemy |
| Coleta SNMP | easysnmp |
| Descoberta de rede | python-nmap |
| Agendador | APScheduler |
| Exportação | pandas + openpyxl |
| Simulação SNMP | snmpsim (Docker) |
| Frontend | Bootstrap 5 + Chart.js + DataTables |
| Containerização | Docker + Docker Compose |
| Sistema operacional | Ubuntu 22.04 LTS |

---

## 👩‍💻 Autores

| Nome | GitHub |
|---|---|
| Sabrina de França Santos | [@sabs0303](https://github.com/sabs0303) |
| Vitor Cruz | [@vitorrcruzz](https://github.com/vitorrcruzz) |

---

## 🏫 Instituição

**FATEC Osasco — Prefeito Hirant Sanazar**  
Curso Superior de Tecnologia em Redes de Computadores  
Disciplina: Projeto de Redes de Computadores  
Professores orientadores: [Leandro Palha]  
Ano: 2026

---

## 🔀 Controle de versão

Este projeto utiliza **Git** para controle de versão e **GitHub** como repositório remoto, seguindo boas práticas de desenvolvimento de software.

### Fluxo de trabalho

```bash
# Clonar o repositório
git clone https://github.com/vitorrcruzz/Inventario-de-TI-TCC-FATEC-Osasco-2026.git

# Verificar status das alterações
git status

# Adicionar arquivos modificados
git add .

# Registrar as alterações com descrição
git commit -m "descricao da alteracao"

# Enviar para o GitHub
git push
```

### Boas práticas adotadas

- Commits frequentes com mensagens descritivas em português
- `.gitignore` configurado para não versionar banco de dados, ambiente virtual e arquivos temporários
- Histórico de alterações rastreável por funcionalidade

---

## 📄 Licença

Este projeto foi desenvolvido para fins acadêmicos como Trabalho de Conclusão de Curso (TCC).

---

<p align="center">
  Feito com ☕ e muito SNMP por Sabrina e Vitor — FATEC Osasco 2026
</p>
