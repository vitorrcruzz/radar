const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync('backend/static/js/main.js', 'utf8').split('// ── Init ')[0];
let created = 0, updated = 0, revision = 0;
const context = {
  window: {innerWidth: 1280},
  document: { getElementById: id => ({id, textContent: ''}) },
  Chart: class {
    constructor(canvas, config) { created++; this.data = config.data; this.options = config.options; }
    update(mode) { assert.equal(mode,'none'); updated++; }
    destroy() { throw new Error('O polling não deve destruir gráficos'); }
  },
  fetch: async url => ({ok:true, json:async () => url === '/api/stats'
    ? {total:18,online:18,offline:0,por_tipo:[{tipo:'Computador',quantidade:18+revision}]}
    : [{iniciado_em:'29/10/2026 10:00:00',total_online:18+revision,total_offline:0}]}),
};
vm.createContext(context);
vm.runInContext(source,context);
(async () => {
  for (let i=0;i<50;i++) {
    await vm.runInContext('carregarStats()',context);
    await vm.runInContext('carregarGraficoHistorico()',context);
  }
  assert.equal(created,2);
  assert.equal(updated,0);
  revision=1;
  await vm.runInContext('carregarStats()',context);
  await vm.runInContext('carregarGraficoHistorico()',context);
  assert.equal(created,2);
  assert.equal(updated,2);
  console.log('OK: 50 atualizações reutilizam os dois gráficos; alterações são aplicadas sem recriação.');
})().catch(error=>{console.error(error);process.exitCode=1;});
