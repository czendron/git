// Smoke do painel: window.claude.use('db') falso alimentado pelo batch.json real da CLI; sample, assets, downloads e
// MediaRecorder falsos para a aba Motion control. Uso: node panel_smoke.js batch.json index.html chrome [video.webm]
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const batch = JSON.parse(fs.readFileSync(process.argv[2]));
  if (process.argv[5]) {  // rodada da aba Motion: uma ficha do elenco esperando o Caio e o Genjutsu caro (aviso de teto)
    const el = batch.find(w => w.collection === 'elenco' && w.doc_id === 'gersinho--seu-tadeu');
    const fake = { state: 'aguardando', status: 'rascunho', sheetUrl: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/x8AAwMCAO+ip1sAAAAASUVORK5CYII=', sheetAt: 1000, usedBy: ['gersinho/x'], updatedAt: 2 };
    if (el) Object.assign(el.data, fake); else batch.push({ collection: 'elenco', doc_id: 'gersinho--seu-tadeu', data: { page: 'gersinho', castId: 'seu-tadeu', name: 'Seu Tadeu Carimbo', role: 'tio', look: 'bald man', ...fake } });
    const sa = batch.find(w => w.collection === 'saude');
    if (sa) sa.data.budget = { mcPerS: 30, maxCreditsIdea: 160, dayCapCredits: 240 };
  }
    const browser = await chromium.launch({ executablePath: process.argv[4] || undefined });
  const page = await browser.newPage();
  page.on('pageerror', e => console.log('PAGEERROR', e.message));
  const init = (batch) => {
    const cols = {}; window.__writes = [];
    for (const w of batch) { (cols[w.collection] ||= {})[w.doc_id] = w.data; }
    const fx = batch.find(w=>w.collection==="fila" && ["pronto","postado"].includes(w.data.state)) || batch.find(w=>w.collection==="fila");
    cols.placar = fx ? { "x": { ref: fx.data.ref, title:"t", views: 1200, views7: 7000, shares: 3, follows: 1, ret3: 40, createdAt: 1 } } : {};
    const snapOf = (c) => ({ docs: Object.entries(cols[c]||{}).map(([id,d]) => ({ id, data: () => d })) });
    const listeners = {};
    const coll = (c) => ({
      orderBy(){ return this; }, limit(){ return this; },
      onSnapshot(cb){ (listeners[c] ||= []).push(cb); cb(snapOf(c)); return () => {}; },
      doc(id){ return { set: async (d) => { window.__writes.push({c,id,d}); (cols[c] ||= {})[id] = d; (listeners[c]||[]).forEach(f => f(snapOf(c))); }, update: async (d) => window.__writes.push({c,id,d,u:1}), delete: async () => {} }; },
    });
    const db = { collection: coll, doc: (p) => ({ onSnapshot(cb){ const [c,id] = p.split('/'); cb({ exists: !!(cols[c]||{})[id], data: () => cols[c][id] }); return () => {}; } }) };
    // aba Motion control: Claude (com imagens), armazenamento e download falsos; MediaRecorder sem codificar nada
    window.__uploads = []; window.__saves = []; window.__samples = [];
    // conversa: sample(turns) devolve texto em PT-BR + bloco ```json (trocas, prompts, avisos, perguntas)
    window.__turns = [];
    const sample = async (input, opts = {}) => {
      window.__samples.push(typeof input === 'string' ? input.slice(0, 80) : 'TURNS:' + input.length);
      if (Array.isArray(input)) window.__turns.push(input.map(t => t.content));
      await new Promise(r => setTimeout(r, window.__sampleDelay || 50));
      const n = window.__turns.length;
      const reply = n === 1 ? 'Entendi: o dançarino de branco vira o Gersinho e o cara de boné vira o Seu Tadeu.' : 'Feito: troquei só o da esquerda.';
      const data = { swaps: [{ target: 'the dancer in the red shirt, center', replace_with: { kind: 'protagonist', description: 'Gersinho' } },
                             { target: 'the man in the cap, far left', replace_with: { kind: 'cast', cast_id: 'seu-tadeu', description: 'Seu Tadeu' } }],
                     scene_prompt: 'A busy São Paulo sidewalk at overcast midday. SCENE_MOCK turn ' + n,
                     frame_prompt: 'Edit image 1. Make exactly these replacements, one per person or object, and nothing else:\n1. Replace the dancer in the red shirt, center with GERSINHO. FRAME_MOCK turn ' + n,
                     warnings: ['Mais de uma pessoa: confira o boné.'], questions: n === 1 ? ['Deixo o fundo igual?'] : [] };
      const text = reply + '\n\n```json\n' + JSON.stringify(data) + '\n```';
      if (opts.onText) opts.onText({ text: reply, delta: reply });
      return { text, truncated: false, modelTierApplied: 'default' };
    };
    sample.limits = async () => ({ maxPromptBytes: 262144, images: { maxCount: 5, maxInputBytes: 20000000, mediaTypes: ['image/jpeg', 'image/png'] } });
    sample.json = async (input, opts = {}) => {
      window.__samples.push(String(input).slice(0, 80));
      if (opts.images) return { people: [{ id: 'p1', replace_subject: 'the dancer in the red shirt, center', position: 'center', full_body: true, hands_visible: false },
                                         { id: 'p2', replace_subject: 'the man in the cap, far left', position: 'left, far', full_body: true, hands_visible: true }],
                                flags: { multiple_people: true, hands_cut_off: true, camera_moving: false, too_close: false }, notes: 'frame bom' };
      if (/scene_prompt/.test(input)) return { scene_prompt: 'A busy São Paulo sidewalk at overcast midday. SCENE_MOCK', frame_prompt: 'Edit image 1. Replace the dancer in the red shirt, center with the man from image 2 and image 3. FRAME_MOCK', title: 'Trend teste' };
      return [];
    };
    const assets = { upload: async (blob, o = {}) => { const id = String(window.__uploads.length + 1).padStart(32, 'c'); window.__uploads.push({ type: o.type || blob.type, size: blob.size }); return { id, url: '/_blob/' + id, sizeBytes: blob.size, contentType: o.type || blob.type }; } };
    const downloads = { save: async (r) => { window.__saves.push({ filename: r.filename, size: r.data.size }); return { status: 'saved' }; } };
    window.MediaRecorder = class {
      constructor(stream, o = {}) { this.mimeType = o.mimeType; this.state = 'inactive'; }
      static isTypeSupported(t) { return /^video\/webm/.test(t); }
      start() { this.state = 'recording'; }
      stop() { this.state = 'inactive'; setTimeout(() => { this.ondataavailable && this.ondataavailable({ data: new Blob([new Uint8Array(4096)], { type: 'video/webm' }) }); this.onstop && this.onstop(); }, 0); }
    };
    const caps = { db, sample, assets, downloads };
    if (window.__noSample || location.hash === '#nosample') delete caps.sample;
    window.claude = { use: async (n) => caps[n] || null };
  };
  await page.addInitScript(init, batch);
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
  await page.click('[data-tab="caixa"]');
  console.log('CAIXA elenco:', (await page.$$('[data-st="elenco"][data-dec="approve"]')).length);
  if (await page.$('[data-st="elenco"][data-dec="reject"]')) {
    await page.click('[data-st="elenco"][data-dec="reject"]');
    console.log('ELENCO reject w/o reason:', await page.textContent('[data-st="elenco"][data-dec="reject"]'));
    await page.click('[data-st="elenco"][data-dec="approve"]');
    await page.waitForTimeout(100);
    console.log('ELENCO decision:', JSON.stringify(await page.evaluate(() => window.__writes.filter(w => w.c === 'decisoes' && w.d.stage === 'elenco').map(w => ({ ref: w.d.ref, verdict: w.d.verdict })))));
  }
  console.log('CAIXA elenco after:', (await page.$$('[data-st="elenco"][data-dec="approve"]')).length);
  await page.click('[data-tab="elenco"]');
  console.log('ELENCO tab:', (await page.$$('#elenco article')).length, '|', (await page.textContent('#elenco')).replace(/\s+/g, ' ').slice(0, 160));
  console.log('WRITES:', JSON.stringify(await page.evaluate(() => window.__writes.map(w => ({c:w.c, stage:w.d.stage, verdict:w.d.verdict, ref:w.d.ref, notes:w.d.notes})))));
  // ---------- aba Motion control ----------
  await page.click('[data-tab="motion"]');
  const ids = ['#mc-file', '#mc-url', '#mc-start', '#mc-end', '#mc-start-n', '#mc-end-n', '#mc-crop', '#mc-prep', '#mc-falso', '#mc-page',
               '#mc-who', '#mc-subject', '#mc-scene', '#mc-frame', '#mc-consent', '#mc-expr', '#mc-deadpan', '#mc-send', '#mc-dl', '#mc-list',
               '#mc-adv', '#b-motion', '#b-yt'];
  const missing = [];
  for (const id of ids) if (!(await page.$(id))) missing.push(id);
  console.log('MC missing:', JSON.stringify(missing));
  console.log('MC accept:', await page.getAttribute('#mc-file', 'accept'), '| adv open:', await page.$eval('#mc-adv', d => d.open));
  console.log('MC send disabled:', await page.$eval('#mc-send', b => b.disabled), '| caps hidden:', await page.$eval('#mc-caps', b => b.hidden));
  console.log('MC pages:', JSON.stringify(await page.$$eval('#mc-page option', os => os.map(o => o.value + (o.disabled ? '(x)' : '')))));
  const vid = process.argv[5];
  if (vid) {
    await page.setInputFiles('#mc-file', vid);
    await page.waitForSelector('#mc-stage:not([hidden])', { timeout: 20000 });
    console.log('MC cost load:', await page.textContent('#mc-cost'), '| cls:', await page.getAttribute('#mc-cost', 'class'));
    console.log('MC range:', await page.inputValue('#mc-start-n'), await page.inputValue('#mc-end-n'), '| crop shown:', await page.$eval('#mc-crop-wrap', e => !e.hidden));
    await page.fill('#mc-end-n', '20'); await page.dispatchEvent('#mc-end-n', 'change');
    console.log('MC clamp:', await page.inputValue('#mc-start-n'), await page.inputValue('#mc-end-n'));
    await page.fill('#mc-start-n', '0'); await page.dispatchEvent('#mc-start-n', 'change');
    await page.fill('#mc-end-n', '1'); await page.dispatchEvent('#mc-end-n', 'change');
    console.log('MC min3:', await page.inputValue('#mc-start-n'), await page.inputValue('#mc-end-n'));
    await page.click('#mc-prep');
    await page.waitForFunction(() => /Clipe pronto|Não consegui|não grava|CORS|limite/.test(document.querySelector('#mc-prep-msg').textContent), null, { timeout: 60000 });
    console.log('MC prep:', await page.textContent('#mc-prep-msg'));
    console.log('MC cuts:', (await page.textContent('#mc-cuts')).trim(), '| falso shown:', await page.$eval('#mc-falso-wrap', e => !e.hidden));
    await page.click('#mc-who');
    await page.waitForSelector('#mc-people [data-person]', { timeout: 10000 });
    console.log('MC people:', await page.$$eval('#mc-people [data-person]', bs => bs.map(b => b.getAttribute('aria-checked') + ':' + b.textContent).join(' | ')));
    console.log('MC flags:', (await page.textContent('#mc-flags')).replace(/\s+/g, ' '));
    await page.click('#mc-people [data-person="1"]');
    await page.click('#mc-people [data-person="0"]');
    console.log('MC chat shown:', await page.$eval('#mc-chat-wrap', e => !e.hidden), '| swaps:', (await page.$$('#mc-swaps .mc-swap')).length);
    await page.fill('#mc-instr', 'troca o dançarino de vermelho pelo Gersinho e o cara de boné pelo Seu Tadeu');
    await page.click('#mc-chat-send');
    await page.waitForFunction(() => /SCENE_MOCK turn 1/.test(document.querySelector('#mc-scene').value), null, { timeout: 10000 });
    console.log('MC chat 1:', (await page.textContent('#mc-chat')).replace(/\s+/g, ' ').slice(0, 200));
    console.log('MC notes:', (await page.textContent('#mc-agent-notes')).replace(/\s+/g, ' '));
    console.log('MC swaps after 1:', (await page.$$('#mc-swaps .mc-swap')).length, await page.$eval('#mc-swaps select[data-f="cast_id"]', s => s.value).catch(() => 'none'));
    const ctx = await page.evaluate(() => window.__turns[0]);
    console.log('MC ctx has:', ['C5', 'seu-tadeu', 'the man in the cap, far left', 'troca o dançarino', 'image 4'].map(k => ctx.join('\n').includes(k)).join(','));
    // edição manual vence: o Caio mexe no frame enquanto o agente responde
    await page.fill('#mc-scene', 'MANUAL scene edit');
    await page.evaluate(() => { window.__sampleDelay = 600; });
    await page.fill('#mc-chat-in', 'não, troca só o da esquerda');
    await page.click('#mc-chat-send');
    await page.waitForTimeout(150);
    await page.fill('#mc-frame', 'Edit image 1. MANUAL frame edit');
    await page.waitForFunction(() => /troquei só/.test(document.querySelector('#mc-chat').textContent), null, { timeout: 10000 });
    const last = await page.evaluate(() => window.__turns[1]);
    console.log('MC turn2 turns:', last.length, '| sent manual scene:', last[last.length - 1].includes('MANUAL scene edit'), '| history:', last.some(t => /troquei|Entendi/.test(t)));
    console.log('MC manual wins:', await page.inputValue('#mc-frame'), '|', await page.inputValue('#mc-scene'));
    await page.evaluate(() => { window.__sampleDelay = 50; });
    await page.click('#mc-write');
    await page.waitForFunction(() => /SCENE_MOCK turn 3/.test(document.querySelector('#mc-scene').value), null, { timeout: 10000 });
    await page.fill('#mc-consent', 'gravado pelo Caio, autorizado');
    console.log('MC send before deadpan:', await page.$eval('#mc-send', b => b.disabled));
    await page.check('#mc-deadpan');
    if (await page.$eval('#mc-falso-wrap', e => !e.hidden)) {
      console.log('MC send blocked by cut:', await page.$eval('#mc-send', b => b.disabled));
      await page.check('#mc-falso');
    }
    console.log('MC todo:', (await page.textContent('#mc-todo')).replace(/\s+/g, ' '));
    await page.click('#mc-send');
    await page.waitForFunction(() => /Pedido salvo|não foi salvo|Falha|Não salvou/.test(document.querySelector('#mc-send-msg').textContent), null, { timeout: 10000 });
    console.log('MC send:', await page.textContent('#mc-send-msg'));
    await page.click('#mc-dl');
    await page.waitForTimeout(100);
    const w = await page.evaluate(() => window.__writes.filter(x => x.c === 'motion').map(x => ({ id: x.id, ...x.d })));
    console.log('MOTION DOC:', JSON.stringify(w));
    console.log('UPLOADS:', JSON.stringify(await page.evaluate(() => window.__uploads)), 'SAVES:', JSON.stringify(await page.evaluate(() => window.__saves)));
    console.log('MC list:', (await page.textContent('#mc-list')).replace(/\s+/g, ' ').slice(0, 300));
  }
  console.log('MC cost:', await page.textContent('#mc-cost'));
  await page.setViewportSize({ width: 375, height: 800 });
  await page.click('[data-tab="elenco"]');
  console.log('ELENCO overflow at 375px:', await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth));
  await page.setViewportSize({ width: 1280, height: 900 });
  // sem sample: sem conversa; trocas à mão e prompts pelo modelo da página
  const p2 = await browser.newPage();
  p2.on('pageerror', e => console.log('PAGEERROR', e.message));
  await p2.addInitScript(() => { window.__noSample = true; });
  await p2.addInitScript(init, batch);
  await p2.goto('file://' + require('path').resolve(process.argv[3]) + '#motion');
  await p2.waitForTimeout(400);
  console.log('NOSAMPLE chat hidden:', await p2.$eval('#mc-chat-wrap', e => e.hidden), '| caps:', (await p2.textContent('#mc-caps')).slice(0, 120));
  await p2.fill('#mc-subject', 'the dancer, center');
  await p2.click('#mc-swap-add');
  await p2.fill('#mc-swaps .mc-swap:nth-child(2) [data-f="target"]', 'the green bottle');
  await p2.selectOption('#mc-swaps .mc-swap:nth-child(2) [data-f="kind"]', 'object');
  await p2.fill('#mc-swaps .mc-swap:nth-child(2) [data-f="description"]', 'a closed black umbrella');
  await p2.click('#mc-write');
  console.log('NOSAMPLE frame:', (await p2.inputValue('#mc-frame')).split('\n').slice(0, 3).join(' / '));
  await p2.close();
  await page.setViewportSize({ width: 375, height: 800 });
  await page.click('[data-tab="motion"]');
  console.log('MC overflow at 375px:', await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth));
  await browser.close();
})();
