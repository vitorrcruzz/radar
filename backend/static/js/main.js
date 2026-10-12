let tabelaDispositivos = null;
let tabelaHistorico    = null;
let graficoPie         = null;
let graficoLinha       = null;

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

  if (graficoPie) graficoPie.destroy();
  graficoPie = new Chart(document.getElementById('grafico-tipos'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: values, backgroundColor: cores, borderWidth: 2 }]
    },
    options: {
      plugins: { legend: { position: 'right', labels: { font: { size: 12 } } } },
      cutout: '60%',
    }
  });
}

async function carregarGraficoHistorico() {
  const r = await fetch('/api/historico');
  const lista = await r.json();
  const recentes = lista.slice(0, 10).reverse();

  const labels  = recentes.map(h => h.iniciado_em.slice(11, 16));
  const online  = recentes.map(h => h.total_online);
  const offline = recentes.map(h => h.total_offline);

  if (graficoLinha) graficoLinha.destroy();
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

function abrirModal(d) {
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
          <table class="table table-sm table-borderless mb-0">
            <tr><td style="width:45%;${tm}">Software</td>
                <td style="${tc}"><strong>${d.licenca_software}</strong></td></tr>
            <tr><td style="${tm}">Expira em</td>
                <td style="${tc}"><strong>${d.licenca_expira}</strong></td></tr>
            <tr><td style="${tm}">Status</td>
                <td>${badgeLicenca(d)}</td></tr>
          </table>
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
                <td style="${tm}"><small>${d.ultima_vez}</small></td></tr>
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
  ['descricao', 'Descrição'], ['localizacao', 'Localização'], ['contato', 'Contato']
];

function editarCamposManuais() {
  const d = window._dispositivoAtual;
  const container = document.getElementById('manual-campos');
  window._dadosOriginaisManual = {};
  container.innerHTML = camposEditaveis.map(([campo, rotulo]) => `
    <div class="col-md-6">
      <label class="form-label" for="manual-${campo}">${rotulo}</label>
      ${campo === 'descricao'
        ? `<textarea class="form-control" id="manual-${campo}" rows="2"></textarea>`
        : `<input class="form-control" id="manual-${campo}" type="text">`}
    </div>`).join('');
  camposEditaveis.forEach(([campo]) => {
    const valor = d[campo] === '—' ? '' : (d[campo] ?? '');
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

// ── Tabela de dispositivos ─────────────────────────────
function badgeLicenca(d) {
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
  const tipo   = document.getElementById('filtro-tipo').value;
  const status = document.getElementById('filtro-status').value;
  let url = '/api/dispositivos?';
  if (tipo)   url += `tipo=${encodeURIComponent(tipo)}&`;
  if (status) url += `status=${status}`;

  const r = await fetch(url);
  const lista = await r.json();

  if (tabelaDispositivos) {
    tabelaDispositivos.destroy();
    tabelaDispositivos = null;
    document.querySelector('#tabela-dispositivos tbody').innerHTML = '';
  }

  const tbody = document.querySelector('#tabela-dispositivos tbody');
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
        <td><small class="text-muted">${d.ultima_vez}</small></td>
      </tr>`;
  });

  tabelaDispositivos = new DataTable('#tabela-dispositivos', {
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/pt-BR.json' },
    pageLength: 15,
    order: [[3, 'desc']],
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
async function carregarHistorico() {
  const r = await fetch('/api/historico');
  const lista = await r.json();

  if (tabelaHistorico) {
    tabelaHistorico.destroy();
    tabelaHistorico = null;
    document.querySelector('#tabela-historico tbody').innerHTML = '';
  }

  const tbody = document.querySelector('#tabela-historico tbody');
  lista.forEach(h => {
    const origem = h.disparado_por === 'manual'
      ? '<span class="badge bg-info text-dark">Manual</span>'
      : '<span class="badge bg-secondary">Automático</span>';
    tbody.innerHTML += `
      <tr>
        <td>${h.id}</td>
        <td>${h.iniciado_em}</td>
        <td>${h.finalizado_em}</td>
        <td class="text-center">${h.total_escaneado}</td>
        <td class="text-center text-success fw-bold">${h.total_online}</td>
        <td class="text-center text-danger">${h.total_offline}</td>
        <td>${origem}</td>
      </tr>`;
  });

  tabelaHistorico = new DataTable('#tabela-historico', {
    language: { url: 'https://cdn.datatables.net/plug-ins/1.13.7/i18n/pt-BR.json' },
    pageLength: 15,
    order: [[0, 'desc']],
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

  setInterval(async () => {
    await carregarStats();
    await carregarGraficoHistorico();
  }, 30000);
})();
