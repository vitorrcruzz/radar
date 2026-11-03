let tabelaDispositivos = null;
let tabelaHistorico    = null;
let graficoPie         = null;
let graficoLinha       = null;
let requisicaoDispositivos = 0;

// Variáveis de tema para uso global
let _t  = false;  // tema escuro ativo?
let _tc = '';     // cor texto principal
let _tm = '';     // cor texto muted
let _ti = '';     // estilo info-card
// ── Tema ───────────────────────────────────────────────
function aplicarTema(tema) {
  document.documentElement.setAttribute('data-theme', tema);
  localStorage.setItem('tema', tema);

  // Atualiza botões ativos
  document.getElementById('btn-claro').classList.toggle('ativo', tema === 'light');
  document.getElementById('btn-nordic').classList.toggle('ativo', tema === 'nordic');

  if (tema === 'nordic') {
    atualizarGraficosNordic();
  } else {
    atualizarGraficosClaro();
  }
  setTimeout(() => {
    corrigirEstilosDataTables();
    aplicarTemaSelect();
  }, 150);
}
function corrigirEstilosDataTables() {
  const tema = document.documentElement.getAttribute('data-theme');
  const escuro = tema === 'nordic';

  const corBg       = escuro ? '#243044' : '#ffffff';
  const corTexto    = escuro ? '#e2e8f0' : '#212529';
  const corBorda    = escuro ? '#2d3748' : '#ced4da';
  const corLabel    = escuro ? '#8892a4' : '#6c757d';
  const corHoverBg  = escuro ? '#2d3a50' : '#e9ecef';
  const corHoverTxt = escuro ? '#4fc3f7' : '#212529';
  const corAtivoBg  = escuro ? '#4fc3f7' : '#2E75B6';
  const corAtivoTxt = '#ffffff';

// Selects do DataTables (Exibir)
  document.querySelectorAll('.dataTables_length select').forEach(el => {
    el.className = 'form-select form-select-sm';
    el.style.width = 'auto';
    el.style.display = 'inline-block';
    el.style.cursor = 'pointer';
  });
  // Inputs de busca
  document.querySelectorAll('.dataTables_filter input').forEach(el => {
    el.style.backgroundColor = corBg;
    el.style.color = corTexto;
    el.style.border = `1px solid ${corBorda}`;
    el.style.borderRadius = '.4rem';
    el.style.padding = '.2rem .5rem';
  });

  // Labels e info
  document.querySelectorAll(
    '.dataTables_length label, .dataTables_filter label, .dataTables_info'
  ).forEach(el => {
    el.style.color = corLabel;
  });

  // Botões de paginação
  document.querySelectorAll('.paginate_button').forEach(el => {
    const isCurrent  = el.classList.contains('current');
    const isDisabled = el.classList.contains('disabled');

    el.style.backgroundColor = isCurrent ? corAtivoBg : corBg;
    el.style.color            = isCurrent ? corAtivoTxt : corTexto;
    el.style.border           = `1px solid ${isCurrent ? corAtivoBg : corBorda}`;
    el.style.borderRadius     = '.4rem';
    el.style.margin           = '0 2px';
    el.style.opacity          = isDisabled ? '.4' : '1';
    el.style.cursor           = isDisabled ? 'not-allowed' : 'pointer';
  });

  // Selects de filtro (Todos os tipos / Todos status)
  // Remove a seta extra injetada via JS — deixa só a do Bootstrap
  document.querySelectorAll('#filtro-tipo, #filtro-status').forEach(el => {
    el.style.backgroundColor = corBg;
    el.style.color = corTexto;
    el.style.borderColor = corBorda;
    el.style.cursor = 'pointer';
    // Remove qualquer backgroundImage injetado anteriormente
    el.style.backgroundImage = '';
  });
}

function aplicarTemaSelect() {
  const tema = document.documentElement.getAttribute('data-theme');
  const escuro = tema === 'nordic';

  document.querySelectorAll('.dataTables_length select').forEach(el => {
    if (escuro) {
      el.style.setProperty('-webkit-appearance', 'none', 'important');
      el.style.setProperty('-moz-appearance', 'none', 'important');
      el.style.setProperty('appearance', 'none', 'important');
      el.style.setProperty('background-color', '#243044', 'important');
      el.style.setProperty('color', '#e2e8f0', 'important');
      el.style.setProperty('border-color', '#2d3748', 'important');
      el.style.setProperty('background-image',
        "url(\"data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' width='10' height='10' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%238892a4' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='m2 5 6 6 6-6'/%3e%3c/svg%3e\")",
        'important');
      el.style.setProperty('background-repeat', 'no-repeat', 'important');
      el.style.setProperty('background-position', 'right .6rem center', 'important');
      el.style.setProperty('padding-right', '2rem', 'important');
      el.style.setProperty('padding', '.15rem 1.5rem .15rem .4rem', 'important');
      el.style.setProperty('font-size', '.875rem', 'important');
      el.style.setProperty('width', '70px', 'important');
      el.style.setProperty('height', '31px', 'important');
    } else {
      el.style.removeProperty('-webkit-appearance');
      el.style.removeProperty('-moz-appearance');
      el.style.removeProperty('appearance');
      el.style.removeProperty('background-color');
      el.style.removeProperty('color');
      el.style.removeProperty('border-color');
      el.style.removeProperty('background-image');
      el.style.removeProperty('background-repeat');
      el.style.removeProperty('background-position');
      el.style.removeProperty('padding-right');
      el.style.removeProperty('padding');
      el.style.removeProperty('font-size');
      el.style.removeProperty('width');
      el.style.removeProperty('height');
    }
  });
}
function atualizarGraficosNordic() {
  if (graficoLinha) {
    // Mantém barras, só muda cores para o nordic
    graficoLinha.config.type = 'bar';
    graficoLinha.data.datasets[0].backgroundColor = '#4fc3f799';
    graficoLinha.data.datasets[0].fill = false;
    graficoLinha.data.datasets[1].backgroundColor = '#f4736899';
    graficoLinha.data.datasets[1].fill = false;
    graficoLinha.options.scales.x.ticks = { color: '#8892a4' };
    graficoLinha.options.scales.y.ticks = { color: '#8892a4' };
    graficoLinha.options.scales.x.grid  = { color: '#2d3748' };
    graficoLinha.options.scales.y.grid  = { color: '#2d3748' };
    graficoLinha.options.plugins.legend.labels = { color: '#e2e8f0', font: { size: 12 } };
    graficoLinha.update();
  }
  if (graficoPie) {
    graficoPie.options.plugins.legend.labels = { color: '#e2e8f0', font: { size: 12 } };
    graficoPie.update();
  }
}
function atualizarGraficosClaro() {
  if (graficoLinha) {
    graficoLinha.data.datasets[0].backgroundColor = '#28a74599';
    graficoLinha.data.datasets[1].backgroundColor = '#dc354599';
    graficoLinha.config.type = 'bar';
    graficoLinha.data.datasets[0].fill = false;
    graficoLinha.data.datasets[1].fill = false;
    graficoLinha.options.scales.x.ticks = { color: '#666' };
    graficoLinha.options.scales.y.ticks = { color: '#666' };
    graficoLinha.options.scales.x.grid  = { color: 'rgba(0,0,0,.05)' };
    graficoLinha.options.scales.y.grid  = { color: 'rgba(0,0,0,.05)' };
    graficoLinha.options.plugins.legend.labels = { color: '#333', font: { size: 12 } };
    graficoLinha.update();
  }
  if (graficoPie) {
    graficoPie.options.plugins.legend.labels = { color: '#333', font: { size: 12 } };
    graficoPie.update();
  }
}
// ── Navegação ──────────────────────────────────────────
function mostrarSecao(nome) {
  ['dashboard','dispositivos','historico'].forEach(s => {
    document.getElementById('secao-'+s).style.display = 'none';
  });
  document.getElementById('secao-'+nome).style.display = '';
  document.getElementById('page-title').textContent =
    nome.charAt(0).toUpperCase() + nome.slice(1);
  document.querySelectorAll('#sidebar .nav-link').forEach(el => {
    el.classList.toggle('active',
      el.textContent.trim().toLowerCase().startsWith(nome));
  });
  if (nome === 'dispositivos') carregarDispositivos();
  if (nome === 'historico')    carregarHistorico();
}

// ── Toast ──────────────────────────────────────────────
function mostrarToast(msg, cor = 'bg-success') {
  const t = document.getElementById('toast');
  t.className = `toast align-items-center text-white border-0 ${cor}`;
  document.getElementById('toast-msg').textContent = msg;
  new bootstrap.Toast(t, { delay: 3500 }).show();
}

// ── Estatísticas e gráficos ────────────────────────────
async function carregarStats() {
  const r = await fetch('/api/stats');
  if (!r.ok) return;
  const d = await r.json();

  document.getElementById('stat-total').textContent   = d.total;
  document.getElementById('stat-online').textContent  = d.online;
  document.getElementById('stat-offline').textContent = d.offline;
  document.getElementById('badge-total').textContent  = d.total;

  if (d.ultima_varredura) {
    document.getElementById('stat-varreduras').textContent =
      d.ultima_varredura.id || 0;
    document.getElementById('ultima-varredura-sidebar').textContent =
      d.ultima_varredura.iniciado_em || '—';
  }

  const labels = d.por_tipo.map(t => t.tipo || 'Desconhecido');
  const values = d.por_tipo.map(t => t.quantidade);
  const cores  = ['#2E75B6','#28a745','#fd7e14','#6f42c1','#dc3545','#17a2b8','#ffc107','#20c997'];

  if (graficoPie) {
    if (JSON.stringify(graficoPie.data.labels) !== JSON.stringify(labels) ||
        JSON.stringify(graficoPie.data.datasets[0].data) !== JSON.stringify(values)) {
      graficoPie.data.labels = labels;
      graficoPie.data.datasets[0].data = values;
      graficoPie.update('none');
    }
    return;
  }
  graficoPie = new Chart(document.getElementById('grafico-tipos'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: cores, borderWidth: 2 }]
    },
    options: {
      plugins: { legend: { position: 'right', labels: { font: { size: 12 } } } },
      responsive: true,
      maintainAspectRatio: false,
      cutout: '60%',
    }
  });
}

async function carregarGraficoHistorico() {
  const r = await fetch('/api/historico/recentes');
  if (!r.ok) return;
  const lista = await r.json();
  const recentes = lista.reverse();

  const labels  = recentes.map(h => h.iniciado_em.slice(11, 16));
  const online  = recentes.map(h => h.total_online);
  const offline = recentes.map(h => h.total_offline);

  if (graficoLinha) {
    if (JSON.stringify(graficoLinha.data.labels) !== JSON.stringify(labels) ||
        JSON.stringify(graficoLinha.data.datasets[0].data) !== JSON.stringify(online) ||
        JSON.stringify(graficoLinha.data.datasets[1].data) !== JSON.stringify(offline)) {
      graficoLinha.data.labels = labels;
      graficoLinha.data.datasets[0].data = online;
      graficoLinha.data.datasets[1].data = offline;
      graficoLinha.update('none');
    }
    return;
  }
  graficoLinha = new Chart(document.getElementById('grafico-historico'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: 'Online',  data: online,  backgroundColor: '#28a74599' },
        { label: 'Offline', data: offline, backgroundColor: '#dc354599' },
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { position: 'top' } },
      scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
    }
  });
}

// ── Modal de detalhes ──────────────────────────────────
function escaparHtml(valor) {
  return String(valor ?? '—').replace(/[&<>"']/g, caractere => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[caractere]);
}

async function abrirModal(d) {
  const respostaDetalhe = await fetch(`/api/dispositivos/${d.id}`);
  if (respostaDetalhe.ok) d = await respostaDetalhe.json();
  window._dispositivoAtual = d;
  const statusBadge = d.status === 'online'
    ? '<span class="badge badge-online px-2 py-1">● Online</span>'
    : '<span class="badge badge-offline px-2 py-1">○ Offline</span>';

  document.getElementById('modal-titulo').textContent =
    `${d.hostname} — ${d.ip}`;

  const t  = document.documentElement.getAttribute('data-theme') === 'nordic';
  const tc = t ? 'color:#e2e8f0' : '';
  const tm = t ? 'color:#8892a4' : '';
  const ti = t ? 'background:#1a2235;border-color:#2d3748' : '';
  
  // Atualiza globais também
  _t = t; _tc = tc; _tm = tm; _ti = ti;

  document.getElementById('modal-corpo').innerHTML = `
    <div id="detalhes-view">
    <div class="row g-3">
      <div class="col-12">
        <div class="d-flex align-items-center gap-2 mb-2">
          <span class="badge bg-light text-dark border fs-6" style="${t?'background:#2d3748!important;color:#e2e8f0!important;border-color:#4a5568!important':''}">${escaparHtml(d.tipo)}</span>
          ${statusBadge}
        </div>
      </div>

      <div class="col-md-6">
        <div class="info-card" style="${ti}">
          <div class="info-label"><i class="bi bi-cpu me-1"></i>Hardware</div>
          <table class="table table-sm table-borderless mb-0">
            <tr><td style="width:45%;${tm}">Modelo</td>
                <td style="${tc}"><strong>${escaparHtml(d.modelo)}</strong></td></tr>
            <tr><td style="${tm}">Processador</td>
                <td style="${tc}"><strong>${escaparHtml(d.processador)}</strong></td></tr>
            <tr><td style="${tm}">Memória</td>
                <td style="${tc}"><strong>${escaparHtml(d.memoria)}</strong></td></tr>
            <tr><td style="${tm}">Armazenamento</td>
                <td style="${tc}"><strong>${escaparHtml(d.armazenamento)}</strong></td></tr>
          </table>
        </div>
      </div>

      <div class="col-md-6">
        <div class="info-card" style="${ti}">
          <div class="info-label"><i class="bi bi-hdd-network me-1"></i>Rede</div>
          <table class="table table-sm table-borderless mb-0">
            <tr><td style="width:45%;${tm}">IP</td>
                <td><code style="${t?'color:#4fc3f7;background:rgba(79,195,247,.1);padding:.1rem .3rem;border-radius:.3rem':''}">${escaparHtml(d.ip)}</code></td></tr>
            <tr><td style="${tm}">Rede</td>
                <td style="${tc}"><span class="badge bg-info text-dark">${escaparHtml(d.rede)}</span></td></tr>
            <tr><td style="${tm}">Hostname</td>
                <td style="${tc}"><strong>${escaparHtml(d.hostname)}</strong></td></tr>
            <tr><td style="${tm}">Interfaces</td>
                <td style="${tc}"><strong>${d.interfaces ?? '—'}</strong></td></tr>
            <tr><td style="${tm}">Uptime</td>
                <td style="${tc}"><strong>${escaparHtml(d.uptime)}</strong></td></tr>
                <tr><td style="width:45%;${tm}">MAC Address</td>
                <td style="${tc}"><code style="${t?'color:#4fc3f7;background:rgba(79,195,247,.1);padding:.1rem .3rem;border-radius:.3rem':''}">${escaparHtml(d.mac_address)}</code></td></tr>
            <tr><td style="${tm}">Serial Number</td>
                <td style="${tc}"><strong>${escaparHtml(d.serial_number)}</strong></td></tr>
          </table>
        </div>
      </div>

      <div class="col-md-6">
        <div class="info-card" style="${ti}">
          <div class="info-label"><i class="bi bi-display me-1"></i>Sistema</div>
          <table class="table table-sm table-borderless mb-0">
            <tr><td style="width:45%;${tm}">Sistema Op.</td>
                <td style="${tc}"><strong>${escaparHtml(d.sistema_op)}</strong></td></tr>
            <tr><td style="${tm}">Descrição</td>
                <td style="${tm}"><small>${escaparHtml(d.descricao)}</small></td></tr>
          </table>
        </div>
      </div>

      <div class="col-md-6">
        <div class="info-card" style="${ti}">
          <div class="info-label"><i class="bi bi-key me-1"></i>Licença</div>
          <p class="small text-muted mb-2">Ativação e edição reportadas pelo Windows. Isso não comprova a titularidade comercial da licença.</p>
          <table class="table table-sm table-borderless mb-0">
            <tr><td style="width:45%;${tm}">Edição do Windows</td>
                <td style="${tc}"><strong>${escaparHtml(d.edicao_windows)}</strong></td></tr>
            <tr><td style="${tm}">Ativação do Windows</td>
                <td style="${tc}"><strong>${escaparHtml(d.status_ativacao_windows)}</strong></td></tr>
            <tr><td style="${tm}">Expiração informada pelo Windows</td>
                <td style="${tc}"><strong>${escaparHtml(d.licenca_windows_expira)}</strong></td></tr>
            <tr><td style="${tm}">Licença cadastrada</td>
                <td style="${tc}"><strong>${escaparHtml(d.licenca_software)}</strong></td></tr>
            <tr><td style="${tm}">Validade cadastrada</td>
                <td style="${tc}"><strong>${d.licenca_expira}</strong></td></tr>
            <tr><td style="${tm}">Status</td>
                <td>${badgeLicenca(d)}</td></tr>
          </table>
        </div>
      </div>

      <div class="col-12">
        <div class="info-card" style="${ti}">
          <div class="d-flex justify-content-between align-items-center mb-2">
            <div class="info-label mb-0"><i class="bi bi-box-seam me-1"></i>Softwares instalados</div>
            ${window.RADAR_PODE_EDITAR ? `<button class="btn btn-outline-primary btn-sm" onclick="mostrarFormularioSoftware()"><i class="bi bi-plus-lg me-1"></i>Cadastrar software</button>` : ''}
          </div>
          <div id="lista-softwares">${htmlSoftwares(d.softwares_instalados || [])}</div>
          <div id="formulario-software" class="mt-3" style="display:none"></div>
        </div>
      </div>

      <div class="col-12">
        <div class="info-card" style="${ti}">
          <div class="info-label"><i class="bi bi-geo-alt me-1"></i>Localização e contato</div>
          <table class="table table-sm table-borderless mb-0">
            <tr><td style="width:20%;${tm}">Local</td>
                <td style="${tc}"><strong>${escaparHtml(d.localizacao)}</strong></td></tr>
            <tr><td style="${tm}">Contato</td>
                <td style="${tm}"><small>${escaparHtml(d.contato)}</small></td></tr>
            <tr><td style="${tm}">Última varredura</td>
                <td style="${tm}"><small>${escaparHtml(d.ultima_vez || '—')}</small></td></tr>
          </table>
        </div>
      </div>
    </div>
    ${window.RADAR_PODE_EDITAR ? `<div class="text-end mt-3">
      <button class="btn btn-outline-primary btn-sm" onclick="editarCamposManuais()">
        <i class="bi bi-pencil-square me-1"></i>Editar cadastro manualmente
      </button>
    </div>` : ''}
    </div>
    <div id="manual-view" style="display:none">
      <p class="text-muted small">Os valores preenchidos aqui têm prioridade sobre a coleta automática. Apague um valor para voltar a usar o dado coletado.</p>
      <div id="manual-campos" class="row g-3"></div>
      <div class="d-flex justify-content-end gap-2 mt-3">
        <button class="btn btn-secondary btn-sm" onclick="cancelarEdicaoManual()">Cancelar</button>
        <button class="btn btn-primary btn-sm" onclick="salvarEdicaoManual()">Salvar dados</button>
      </div>
    </div>
  `;
  bootstrap.Modal.getOrCreateInstance(document.getElementById('modalDetalhes')).show();
}

const camposEditaveis = [
  ['hostname', 'Hostname'], ['tipo', 'Tipo'], ['modelo', 'Modelo'],
  ['sistema_op', 'Sistema operacional'], ['processador', 'Processador'],
  ['memoria', 'Memória'], ['armazenamento', 'Armazenamento'],
  ['mac_address', 'MAC Address'], ['serial_number', 'Número de série'],
  ['rede', 'Rede / andar'], ['interfaces', 'Interfaces', 'number'], ['uptime', 'Tempo ligado'],
  ['descricao', 'Descrição'], ['localizacao', 'Localização'], ['contato', 'Contato'],
  ['licenca_software', 'Software / licença cadastrada'],
  ['licenca_expira', 'Validade da licença', 'date'],
  ['edicao_windows', 'Edição do Windows'],
  ['status_ativacao_windows', 'Ativação do Windows'],
  ['licenca_windows_expira', 'Expiração informada pelo Windows', 'date']
];

function editarCamposManuais() {
  const d = window._dispositivoAtual;
  const container = document.getElementById('manual-campos');
  window._dadosOriginaisManual = {};
  container.innerHTML = camposEditaveis.map(([campo, rotulo, tipo = 'text']) => `
    <div class="col-md-6">
      <label class="form-label" for="manual-${campo}">${rotulo}</label>
      ${campo === 'descricao'
        ? `<textarea class="form-control" id="manual-${campo}" rows="2"></textarea>`
        : `<input class="form-control" id="manual-${campo}" type="${tipo}">`}
    </div>`).join('');
  camposEditaveis.forEach(([campo]) => {
    const valorAtual = campo === 'licenca_expira' ? d.licenca_expira_iso
      : campo === 'licenca_windows_expira' ? d.licenca_windows_expira_iso
      : d[campo];
    const valor = valorAtual === '—' ? '' : (valorAtual ?? '');
    window._dadosOriginaisManual[campo] = String(valor);
    document.getElementById(`manual-${campo}`).value = valor;
  });
  document.getElementById('detalhes-view').style.display = 'none';
  document.getElementById('manual-view').style.display = 'block';
}

function cancelarEdicaoManual() {
  document.getElementById('manual-view').style.display = 'none';
  document.getElementById('detalhes-view').style.display = 'block';
}

async function salvarEdicaoManual() {
  const d = window._dispositivoAtual;
  const payload = {};
  camposEditaveis.forEach(([campo]) => {
    const valor = document.getElementById(`manual-${campo}`).value.trim();
    if (valor !== window._dadosOriginaisManual[campo]) payload[campo] = valor;
  });
  if (!Object.keys(payload).length) {
    cancelarEdicaoManual();
    mostrarToast('Nenhuma alteração foi feita.', 'bg-info');
    return;
  }
  const resposta = await fetch(`/api/dispositivos/${d.id}/manual`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const resultado = await resposta.json();
  if (!resposta.ok) {
    mostrarToast(resultado.erro || 'Não foi possível salvar os dados.', 'bg-danger');
    return;
  }
  window._dispositivoAtual = resultado;
  carregarDispositivos();
  abrirModal(resultado);
  mostrarToast('Cadastro atualizado. Os campos manuais serão preservados nas próximas varreduras.');
}

function htmlSoftwares(lista) {
  if (!lista.length) return '<p class="text-muted small mb-0">Nenhum software cadastrado manualmente.</p>';
  return `<div class="table-responsive"><table class="table table-sm table-hover mb-0">
    <thead><tr><th>Software</th><th>Fabricante</th><th>Versão</th><th>Licença</th><th>Expira em</th>${window.RADAR_PODE_EDITAR ? '<th>Ações</th>' : ''}</tr></thead>
    <tbody>${lista.map(s => `<tr>
      <td><strong>${escaparHtml(s.nome)}</strong>${s.observacao ? `<div class="small text-muted">${escaparHtml(s.observacao)}</div>` : ''}</td>
      <td>${escaparHtml(s.fabricante || '—')}</td><td>${escaparHtml(s.versao || '—')}</td>
      <td>${escaparHtml(s.tipo_licenca || '—')}</td>
      <td>${s.expira_em ? escaparHtml(s.expira_em.split('-').reverse().join('/')) : '—'}</td>
      ${window.RADAR_PODE_EDITAR ? `<td class="text-nowrap"><button class="btn btn-sm btn-outline-secondary me-1" title="Editar" onclick="mostrarFormularioSoftware(${s.id})"><i class="bi bi-pencil"></i></button><button class="btn btn-sm btn-outline-danger" title="Excluir" onclick="excluirSoftware(${s.id})"><i class="bi bi-trash"></i></button></td>` : ''}
    </tr>`).join('')}</tbody></table></div>`;
}

function mostrarFormularioSoftware(softwareId = null) {
  const atual = window._dispositivoAtual;
  const software = (atual.softwares_instalados || []).find(item => item.id === softwareId) || {};
  const wrap = document.getElementById('formulario-software');
  wrap.innerHTML = `<h6>${softwareId ? 'Editar software' : 'Cadastrar software'}</h6>
    <div class="row g-2">
      <div class="col-md-4"><label class="form-label" for="sw-nome">Nome *</label><input id="sw-nome" class="form-control" maxlength="150" required></div>
      <div class="col-md-4"><label class="form-label" for="sw-fabricante">Fabricante</label><input id="sw-fabricante" class="form-control" maxlength="120"></div>
      <div class="col-md-4"><label class="form-label" for="sw-versao">Versão</label><input id="sw-versao" class="form-control" maxlength="80"></div>
      <div class="col-md-4"><label class="form-label" for="sw-licenca">Tipo de licença</label><input id="sw-licenca" class="form-control" maxlength="80" placeholder="Ex.: assinatura, perpétua"></div>
      <div class="col-md-4"><label class="form-label" for="sw-expira">Validade</label><input id="sw-expira" type="date" class="form-control"></div>
      <div class="col-md-12"><label class="form-label" for="sw-observacao">Observações</label><textarea id="sw-observacao" class="form-control" rows="2" maxlength="1000"></textarea></div>
    </div>
    <div class="d-flex justify-content-end gap-2 mt-3"><button class="btn btn-secondary btn-sm" onclick="cancelarFormularioSoftware()">Cancelar</button><button class="btn btn-primary btn-sm" onclick="salvarSoftware(${softwareId || 'null'})">Salvar software</button></div>`;
  document.getElementById('sw-nome').value = software.nome || '';
  document.getElementById('sw-fabricante').value = software.fabricante || '';
  document.getElementById('sw-versao').value = software.versao || '';
  document.getElementById('sw-licenca').value = software.tipo_licenca || '';
  document.getElementById('sw-expira').value = software.expira_em || '';
  document.getElementById('sw-observacao').value = software.observacao || '';
  wrap.style.display = 'block';
}

function cancelarFormularioSoftware() {
  const wrap = document.getElementById('formulario-software');
  wrap.style.display = 'none';
  wrap.innerHTML = '';
}

async function salvarSoftware(softwareId = null) {
  const atual = window._dispositivoAtual;
  const payload = {
    nome: document.getElementById('sw-nome').value.trim(),
    fabricante: document.getElementById('sw-fabricante').value.trim(),
    versao: document.getElementById('sw-versao').value.trim(),
    tipo_licenca: document.getElementById('sw-licenca').value.trim(),
    expira_em: document.getElementById('sw-expira').value,
    observacao: document.getElementById('sw-observacao').value.trim()
  };
  if (!payload.nome) { mostrarToast('Informe o nome do software.', 'bg-danger'); return; }
  const endpoint = `/api/dispositivos/${atual.id}/softwares${softwareId ? `/${softwareId}` : ''}`;
  const resposta = await fetch(endpoint, {
    method: softwareId ? 'PUT' : 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  const resultado = await resposta.json();
  if (!resposta.ok) { mostrarToast(resultado.erro || 'Não foi possível salvar o software.', 'bg-danger'); return; }
  atual.softwares_instalados = resultado.softwares_instalados || [];
  abrirModal(atual);
  mostrarToast('Software salvo no cadastro do equipamento.');
}

async function excluirSoftware(softwareId) {
  if (!confirm('Remover este software do inventário do equipamento?')) return;
  const atual = window._dispositivoAtual;
  const resposta = await fetch(`/api/dispositivos/${atual.id}/softwares/${softwareId}`, { method: 'DELETE' });
  const resultado = await resposta.json();
  if (!resposta.ok) { mostrarToast(resultado.erro || 'Não foi possível remover o software.', 'bg-danger'); return; }
  atual.softwares_instalados = resultado.softwares_instalados || [];
  abrirModal(atual);
  mostrarToast('Software removido do cadastro.');
}

// ── Tabela de dispositivos ─────────────────────────────
function badgeLicenca(d) {
  const ativacaoWindows = d.status_ativacao_windows;
  if (ativacaoWindows && ativacaoWindows !== 'Não coletado') {
    if (ativacaoWindows === 'Ativo') {
      return '<span class="badge bg-success">Ativa no Windows</span>';
    }
    const cor = ativacaoWindows === 'Não licenciado' || ativacaoWindows === 'Notificação de ativação'
      ? 'bg-danger' : 'bg-warning text-dark';
    return `<span class="badge ${cor}">${escaparHtml(ativacaoWindows)}</span>`;
  }
  if (d.licenca_expira === '—' || d.licenca_expira === null) {
    return '<span class="badge bg-secondary">Sem licença</span>';
  }
  const sl = d.status_licenca;
  if (sl === 'expirada') {
    return `<span class="badge bg-danger">Expirada</span>`;
  }
  if (sl === 'critica') {
    return `<span class="badge bg-danger">${d.dias_para_expirar}d restantes</span>`;
  }
  if (sl === 'atencao') {
    return `<span class="badge bg-warning text-dark">${d.dias_para_expirar}d restantes</span>`;
  }
  return `<span class="badge bg-success">${d.dias_para_expirar}d restantes</span>`;
}


async function carregarDispositivos() {
  const requisicao = ++requisicaoDispositivos;
  const tipo   = document.getElementById('filtro-tipo').value;
  const status = document.getElementById('filtro-status').value;
  let url = '/api/dispositivos?';
  if (tipo)   url += `tipo=${encodeURIComponent(tipo)}&`;
  if (status) url += `status=${status}`;

  const r = await fetch(url);
  if (!r.ok) return;
  const lista = await r.json();
  if (requisicao !== requisicaoDispositivos) return;
  const tbody = document.createElement('tbody');
  window._dispositivos = {};
  lista.forEach((d, idx) => {
    const badge = d.status === 'online'
      ? '<span class="badge badge-online px-2 py-1">● Online</span>'
      : '<span class="badge badge-offline px-2 py-1">○ Offline</span>';

    // Armazena o objeto numa variável global indexada
    window._dispositivos = window._dispositivos || {};
    window._dispositivos[idx] = d;

    tbody.innerHTML += `
      <tr style="cursor:pointer" onclick="abrirModal(window._dispositivos[${idx}])">
        <td><code>${escaparHtml(d.ip)}</code></td>
        <td><span class="badge bg-info text-dark">${escaparHtml(d.rede)}</span></td>
        <td><strong>${escaparHtml(d.hostname)}</strong></td>
        <td><span class="badge bg-light text-dark border">${escaparHtml(d.tipo)}</span></td>
        <td>${badge}</td>
        <td><small>${escaparHtml(d.modelo)}</small></td>
        <td><small>${escaparHtml(d.sistema_op)}</small></td>
        <td><small>${escaparHtml(d.processador)}</small></td>
        <td><small>${escaparHtml(d.mac_address)}</small></td>
        <td><small>${escaparHtml(d.serial_number)}</small></td>
        <td><small>${escaparHtml(d.memoria)}</small></td>
        <td><small>${escaparHtml(d.armazenamento)}</small></td>
        <td>${badgeLicenca(d)}</td>
        <td>${d.uptime}</td>
        <td class="ultima-varredura"><span>${escaparHtml(d.ultima_vez || '—')}</span></td>
      </tr>`;
  });

  if (tabelaDispositivos) {
    tabelaDispositivos.clear().rows.add(Array.from(tbody.children)).draw(false);
    const info = tabelaDispositivos.page.info();
    if (info.pages && info.page >= info.pages) tabelaDispositivos.page(info.pages - 1).draw(false);
    return;
  }
  document.querySelector('#tabela-dispositivos tbody').replaceChildren(...Array.from(tbody.children));

  tabelaDispositivos = new DataTable('#tabela-dispositivos', {
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/pt-BR.json' },
    pageLength: 15,
    order: [[4, 'desc']],
    scrollX: true,
    initComplete: function() {
      corrigirEstilosDataTables();
      setTimeout(aplicarTemaSelect, 50);
    },
    drawCallback: function() {
      corrigirEstilosDataTables();
      setTimeout(aplicarTemaSelect, 50);
    }
  });
}
function filtrarTabela() { carregarDispositivos(); }

// ── Tabela histórico ───────────────────────────────────
function carregarHistorico() {
  if (tabelaHistorico) {
    tabelaHistorico.ajax.reload(null, false);
    return;
  }
  const texto = valor => escaparHtml(valor ?? '—');
  tabelaHistorico = new DataTable('#tabela-historico', {
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/pt-BR.json' },
    processing: true,
    serverSide: true,
    deferRender: true,
    searchDelay: 350,
    pageLength: 15,
    lengthMenu: [10, 15, 25, 50],
    order: [[0, 'desc']],
    ajax: { url: '/api/historico', type: 'GET' },
    columns: [
      { data: 'id', render: texto },
      { data: 'iniciado_em', render: texto },
      { data: 'finalizado_em', render: texto },
      { data: 'total_escaneado', className: 'text-center', render: texto },
      { data: 'total_online', className: 'text-center text-success fw-bold', render: texto },
      { data: 'total_offline', className: 'text-center text-danger', render: texto },
      { data: 'disparado_por', render: (origem, tipo) => {
        if (tipo !== 'display') return origem;
        return origem === 'manual'
          ? '<span class="badge bg-info text-dark">Manual</span>'
          : '<span class="badge bg-secondary">Automático</span>';
      } }
    ],
    initComplete: function() {
      corrigirEstilosDataTables();
      setTimeout(aplicarTemaSelect, 50);
    },
    drawCallback: function() {
      corrigirEstilosDataTables();
      setTimeout(aplicarTemaSelect, 50);
    }
  });
}

// ── Varredura manual ───────────────────────────────────
async function dispararVarredura() {
  const btn     = document.getElementById('btn-scan');
  const spinner = document.getElementById('scan-spinner');
  btn.classList.add('scanning');
  spinner.classList.add('visible');

  try {
    const r = await fetch('/api/scan', { method: 'POST' });
    const d = await r.json();
    mostrarToast(
      `Varredura concluída: ${d.online} online, ${d.offline} offline`,
      'bg-success'
    );
    await carregarStats();
    await carregarGraficoHistorico();
  } catch (e) {
    mostrarToast('Erro ao realizar varredura.', 'bg-danger');
  } finally {
    btn.classList.remove('scanning');
    spinner.classList.remove('visible');
  }
}

// ── Init ───────────────────────────────────────────────
(async () => {
  // Aplica tema salvo
  const temaSalvo = localStorage.getItem('tema') || 'light';
  aplicarTema(temaSalvo);

  await carregarStats();
  await carregarGraficoHistorico();

  let atualizacaoEmAndamento = false;
  setInterval(async () => {
    if (document.hidden || atualizacaoEmAndamento) return;
    atualizacaoEmAndamento = true;
    try {
      await carregarStats();
      if (document.getElementById('secao-dashboard').style.display !== 'none') {
        await carregarGraficoHistorico();
      }
      if (document.getElementById('secao-dispositivos').style.display !== 'none' &&
          !document.querySelector('.modal.show')) {
        await carregarDispositivos();
      }
    } catch (erro) {
      console.warn('Atualização periódica indisponível; será tentada novamente.', erro);
    } finally {
      atualizacaoEmAndamento = false;
    }
  }, 30000);
})();
