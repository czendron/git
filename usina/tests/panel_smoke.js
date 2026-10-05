// Smoke do painel: window.claude.use('db') falso alimentado pelo batch.json real da CLI. Uso: node panel_smoke.js batch.json index.html chrome
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const batch = JSON.parse(fs.readFileSync(process.argv[2]));
    const browser = await chromium.launch({ executablePath: process.argv[4] || undefined });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('PAGEERROR', e.message));
  await page.addInitScript((batch) => {
    const cols = {}; window.__writes = [];
    for (const w of batch) { (cols[w.collection] ||= {})[w.doc_id] = w.data; }
    cols.placar = { "x": { ref: (batch.find(w=>w.collection==="fila" && ["pronto","postado"].includes(w.data.state)) || batch.find(w=>w.collection==="fila")).data.ref, title:"t", views: 1200, views7: 7000, shares: 3, follows: 1, ret3: 40, createdAt: 1 } };
    const snapOf = (c) => ({ docs: Object.entries(cols[c]||{}).map(([id,d]) => ({ id, data: () => d })) });
    const listeners = {};
    const coll = (c) => ({
      orderBy(){ return this; }, limit(){ return this; },
      onSnapshot(cb){ (listeners[c] ||= []).push(cb); cb(snapOf(c)); return () => {}; },
      doc(id){ return { set: async (d) => { window.__writes.push({c,id,d}); (cols[c] ||= {})[id] = d; (listeners[c]||[]).forEach(f => f(snapOf(c))); }, update: async (d) => window.__writes.push({c,id,d,u:1}), delete: async () => {} }; },
    });
    const db = { collection: coll, doc: (p) => ({ onSnapshot(cb){ const [c,id] = p.split('/'); cb({ exists: !!(cols[c]||{})[id], data: () => cols[c][id] }); return () => {}; } }) };
    window.claude = { use: async (n) => n === 'db' ? db : null };
  }, batch);
  await page.goto('file://' + require('path').resolve(process.argv[3]));
  await page.waitForTimeout(500);
  await page.click('[data-tab="saude"]');
  const txt = await page.textContent('#saude');
  console.log('SAUDE:', txt.replace(/\s+/g,' ').slice(0, 900));
  await page.selectOption('#pl-item', { index: 0 }).catch(()=>{});
  await page.dispatchEvent('#pl-item', 'change');
  console.log('PREFILL views7=', await page.inputValue('#pl-views7'));
  await page.fill('#ks-why', 'viagem');
  await page.click('#b-pause');
  await page.waitForTimeout(100);
  console.log('KS msg:', await page.textContent('#ks-msg'));
  await page.click('[data-tab="fila"]');
  const vetos = await page.$$('[data-veto]');
  console.log('veto buttons:', vetos.length);
  if (vetos.length) { await vetos[0].click(); await page.waitForTimeout(100); }
  console.log('veto after:', (await page.$$('[data-veto]')).length);
  // rodada 4: pronto = Baixar MP4 + Postei; Caixa sem card de vídeo enquanto o gag da trend está em produção
  console.log('DOWNLOADS:', JSON.stringify(await page.$$eval('#fila [data-dl]', as => as.map(a => a.dataset.dl))));
  const posts = await page.$$('[data-post]');
  console.log('post buttons:', posts.length);
  if (posts.length) { await page.fill('[data-link]', 'https://instagram.com/reel/abc'); await posts[0].click(); await page.waitForTimeout(100); }
  console.log('post after:', (await page.$$('[data-post]')).length);
  console.log('CAIXA cards:', await page.textContent('#n-caixa'));
  console.log('WRITES:', JSON.stringify(await page.evaluate(() => window.__writes.map(w => ({c:w.c, stage:w.d.stage, verdict:w.d.verdict, ref:w.d.ref, notes:w.d.notes})))));
  await browser.close();
})();
