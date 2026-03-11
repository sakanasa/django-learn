// ── WS Damage Simulator — Frontend Logic ──────────────────────────────────

const API_BASE = window._WS_SIM_API_BASE || '';

// ---------------------------------------------------------------------------
// Block definitions
// ---------------------------------------------------------------------------
const BLOCK_DEFS = {
  swing:                { label: 'swing',                field: 'value', inputType: 'number', default: 3,     desc: '普通攻擊（靈魂值）' },
  burn:                 { label: 'burn',                 field: 'value', inputType: 'number', default: 2,     desc: '燒傷' },
  icytail:              { label: 'icytail',              field: 'value', inputType: 'number', default: 6,     desc: '看底 X 張（集體）' },
  ping_icytail:         { label: 'ping_icytail',         field: 'value', inputType: 'number', default: 4,     desc: '看底 X 張（獨立）',
                          mainLabel: '底張', extraField: { field: 'dmg', inputType: 'number', default: 1, label: '傷/CX' } },
  reveal_top_lv0_burn:  { label: 'reveal_top_lv0_burn',  field: 'value', inputType: 'number', default: 1,     desc: '揭示頂牌，若0等/Event則燒X傷' },
  direct_soul_check:    { label: 'direct_soul_check',    field: 'value', inputType: 'number', default: 3,     desc: '揭示頂X張，每有Soul直接+1傷（不取消）' },
  shuffleback:          { label: 'shuffleback',          field: 'value', inputType: 'number', default: 2,     desc: '加 DMG 重洗' },
  moca:                 { label: 'moca',                 field: 'value', inputType: 'number', default: 2,     desc: '移除頂 CX' },
  insert_top:           { label: 'insert_top',           field: 'card',  inputType: 'select', default: 'DMG', desc: '插牌到頂', options: ['DMG', 'CX'] },
  if_canceled:          { label: 'if_canceled',          field: null,    inputType: null,     default: null,  desc: '取消後執行' },
  reset_canceled:       { label: 'reset_canceled',       field: null,    inputType: null,     default: null,  desc: '重置取消旗標' },
};

const DAMAGE_LABELS = ["3-6","3-5","3-4","3-3","3-2","3-1","3-0",
                        "2-6","2-5","2-4","2-3","2-2","2-1","2-0"];

// Fan angles per card count
const FAN_ANGLES = {
  1: [0],
  2: [-15, 15],
  3: [-15, 0, 15],
  4: [-20, -7, 7, 20],
  5: [-25, -12, 0, 12, 25],
};

// ---------------------------------------------------------------------------
// State
// ---------------------------------------------------------------------------
let state = {
  sequence: [],
  oppConfigs: [
    { size: 30, cx: 8 },
    { size: 25, cx: 8 },
    { size: 20, cx: 8 },
    { size: 30, cx: 6 },
    { size: 25, cx: 6 },
    { size: 20, cx: 6 },
  ],
  presets: [],
  savedCombos: [],          // loaded from API
  activeCombo: { id: null, name: '', images: [null,null,null,null,null] },
  lastResults: null,
  insertTarget: null,       // path[] or null — click-to-target for if_canceled
};

let dragSrcIndex = null;    // for reordering top-level blocks
let paletteDragType = null; // for dragging from palette into if-steps

// ---------------------------------------------------------------------------
// Path helpers
// ---------------------------------------------------------------------------
function getStepsAt(path) {
  // path = [] => top-level sequence
  // path = [i] => state.sequence[i].steps
  // path = [i, j] => state.sequence[i].steps[j].steps
  let steps = state.sequence;
  for (let k = 0; k < path.length; k++) {
    steps = steps[path[k]].steps;
  }
  return steps;
}

function getStepAt(path) {
  const steps = getStepsAt(path.slice(0, -1));
  return steps[path[path.length - 1]];
}

function removeStepAt(path) {
  const steps = getStepsAt(path.slice(0, -1));
  steps.splice(path[path.length - 1], 1);
}

function insertStepAt(parentPath, step) {
  getStepsAt(parentPath).push(step);
}

function duplicateBlockAtPath(path) {
  const clone = JSON.parse(JSON.stringify(getStepAt(path)));
  const parentPath = path.slice(0, -1);
  const insertIdx = path[path.length - 1] + 1;
  getStepsAt(parentPath).splice(insertIdx, 0, clone);
  renderSequence();
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------
function $(id) { return document.getElementById(id); }

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function pctColor(pct) {
  const r = pct < 50 ? 220 : Math.round(220 - (pct - 50) * 2.2);
  const g = pct < 50 ? Math.round(pct * 2.8) : 140;
  const b = 60;
  return `rgb(${r},${g},${b})`;
}

function makeStep(type) {
  const def = BLOCK_DEFS[type];
  const step = { type };
  if (def.field === 'value') step.value = def.default;
  if (def.field === 'card')  step.card = def.default;
  if (def.extraField)        step[def.extraField.field] = def.extraField.default;
  if (type === 'if_canceled') step.steps = [];
  return step;
}

function genId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

// ---------------------------------------------------------------------------
// Image compression
// ---------------------------------------------------------------------------
function compressImage(file, size = 200) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = e => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        const scale = Math.max(size / img.width, size / img.height);
        const sw = size / scale;
        const sh = size / scale;
        const sx = (img.width - sw) / 2;
        const sy = (img.height - sh) / 2;
        ctx.drawImage(img, sx, sy, sw, sh, 0, 0, size, size);
        resolve(canvas.toDataURL('image/jpeg', 0.8));
      };
      img.onerror = reject;
      img.src = e.target.result;
    };
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

// ---------------------------------------------------------------------------
// API — Combos
// ---------------------------------------------------------------------------
async function fetchCombos() {
  try {
    const res = await fetch(API_BASE + '/api/combos');
    const data = await res.json();
    state.savedCombos = data.combos;
    renderComboDropdown();
  } catch (e) {
    console.error('Failed to fetch combos', e);
  }
}

async function apiSaveCombo() {
  const name = $('active-combo-name').value.trim();
  if (!name) {
    $('active-combo-name').focus();
    return;
  }
  if (state.sequence.length === 0) {
    alert('請先加入效果積木再儲存');
    return;
  }
  if (!state.activeCombo.id) {
    state.activeCombo.id = genId();
  }
  const body = {
    id: state.activeCombo.id,
    name,
    sequence: JSON.parse(JSON.stringify(state.sequence)),
    images: state.activeCombo.images,
  };
  try {
    await fetch(API_BASE + '/api/combos', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    state.activeCombo.name = name;
    await fetchCombos();
  } catch (e) {
    alert('存檔失敗: ' + e.message);
  }
}

async function apiDeleteCombo(id) {
  try {
    await fetch(API_BASE + `/api/combos/${id}`, { method: 'DELETE' });
    await fetchCombos();
  } catch (e) {
    console.error('Delete failed', e);
  }
}

function renderComboDropdown() {
  const sel = $('combo-select');
  const cur = sel.value;
  sel.innerHTML = '<option value="">— 已存檔殺招 —</option>';
  state.savedCombos.forEach(c => {
    const opt = document.createElement('option');
    opt.value = c.id;
    opt.textContent = c.name;
    sel.appendChild(opt);
  });
  if (cur) sel.value = cur;
}

function loadComboById(id) {
  const combo = state.savedCombos.find(c => c.id === id);
  if (!combo) return;
  state.sequence = JSON.parse(JSON.stringify(combo.sequence));
  state.activeCombo = {
    id: combo.id,
    name: combo.name,
    images: combo.images || [null,null,null,null,null],
  };
  $('active-combo-name').value = combo.name;
  syncImageSlots();
  renderSequence();
}

function newCombo() {
  state.sequence = [];
  state.activeCombo = { id: null, name: '', images: [null,null,null,null,null] };
  $('active-combo-name').value = '';
  syncImageSlots();
  renderSequence();
  $('run-status').textContent = '';
}

// ---------------------------------------------------------------------------
// Image slots
// ---------------------------------------------------------------------------
function syncImageSlots() {
  for (let i = 0; i < 5; i++) {
    const slot = $(`img-slot-${i}`);
    const img = state.activeCombo.images[i];
    if (img) {
      slot.style.backgroundImage = `url(${img})`;
      slot.classList.add('has-image');
      slot.querySelector('.slot-plus').style.display = 'none';
    } else {
      slot.style.backgroundImage = '';
      slot.classList.remove('has-image');
      slot.querySelector('.slot-plus').style.display = '';
    }
  }
}

function setupImageSlots() {
  for (let i = 0; i < 5; i++) {
    const slot = $(`img-slot-${i}`);
    const input = $(`img-input-${i}`);
    slot.addEventListener('click', () => input.click());
    input.addEventListener('change', async () => {
      const file = input.files[0];
      if (!file) return;
      try {
        const b64 = await compressImage(file);
        state.activeCombo.images[i] = b64;
        syncImageSlots();
      } catch (e) {
        console.error('Image compress error', e);
      }
      input.value = '';
    });
  }
}

// ---------------------------------------------------------------------------
// Insert target (click-to-target for if_canceled sub-steps)
// ---------------------------------------------------------------------------
function setInsertTarget(path) {
  state.insertTarget = path;
  renderSequence();
}

function clearInsertTarget() {
  state.insertTarget = null;
  renderSequence();
}

// ---------------------------------------------------------------------------
// Add / Remove blocks via path
// ---------------------------------------------------------------------------
function addBlock(type, targetPath = null) {
  const step = makeStep(type);
  if (targetPath === null) {
    state.sequence.push(step);
  } else {
    insertStepAt(targetPath, step);
  }
  state.insertTarget = null;
  renderSequence();
}

function removeBlockAtPath(path) {
  removeStepAt(path);
  state.insertTarget = null;
  renderSequence();
}

function updateStepValue(path, field, value) {
  const step = getStepAt(path);
  if (field === 'value') step.value = parseInt(value) || 1;
  if (field === 'card')  step.card = value;
  if (field === 'dmg')   step.dmg = parseInt(value) || 1;
}

// ---------------------------------------------------------------------------
// Render sequence
// ---------------------------------------------------------------------------
function renderSequence() {
  const area = $('sequence-area');
  area.innerHTML = '';
  if (state.sequence.length === 0) {
    area.innerHTML = '<div class="sequence-empty">點擊左側積木加入序列</div>';
    return;
  }
  state.sequence.forEach((step, idx) => {
    area.appendChild(buildBlockEl(step, [idx]));
  });
}

function buildNumCtrl(value, min, max, cls) {
  return `<div class="num-ctrl">
    <button class="btn-dec ${cls}-dec">-</button>
    <input type="number" min="${min}" max="${max}" value="${value}" class="block-input ${cls}-input" />
    <button class="btn-inc ${cls}-inc">+</button>
  </div>`;
}

function wireNumCtrl(el, cls, min, max, path, field) {
  const input = el.querySelector(`.${cls}-input`);
  input.addEventListener('change', e => updateStepValue(path, field, e.target.value));
  el.querySelector(`.${cls}-dec`).addEventListener('click', e => {
    e.stopPropagation();
    const v = Math.max(min, parseInt(input.value) - 1);
    input.value = v;
    updateStepValue(path, field, v);
  });
  el.querySelector(`.${cls}-inc`).addEventListener('click', e => {
    e.stopPropagation();
    const v = Math.min(max, parseInt(input.value) + 1);
    input.value = v;
    updateStepValue(path, field, v);
  });
}

function buildBlockEl(step, path) {
  const el = document.createElement('div');
  el.className = `seq-block seq-block-${step.type}`;
  el.dataset.path = JSON.stringify(path);

  const pathJson = JSON.stringify(path);

  if (step.type === 'if_canceled') {
    const isTarget = state.insertTarget &&
      JSON.stringify(state.insertTarget) === JSON.stringify(path);

    el.innerHTML = `
      <div class="if-body">
        <div class="if-header">
          <span class="block-label">🔀 if_canceled</span>
          <button class="btn-dup btn-dup-path" data-path='${pathJson}' title="複製">⧉</button>
          <button class="btn-remove btn-rm-path" data-path='${pathJson}'>✕</button>
        </div>
        <div class="if-steps" data-if-path='${pathJson}'>
          ${step.steps.length === 0 ? '<div class="if-empty">取消時執行（空）</div>' : ''}
        </div>
        <button class="btn-secondary btn-sm add-if-block" data-if-path='${pathJson}' style="margin-top:4px;width:100%">+ 選取目標</button>
      </div>`;

    if (isTarget) el.classList.add('insert-target-active');

    const ifArea = el.querySelector('.if-steps');
    step.steps.forEach((sub, si) => {
      ifArea.appendChild(buildBlockEl(sub, [...path, si]));
    });

    ifArea.addEventListener('dragover', e => {
      if (!paletteDragType) return;
      e.preventDefault();
      ifArea.classList.add('drag-over-if');
    });
    ifArea.addEventListener('dragleave', () => ifArea.classList.remove('drag-over-if'));
    ifArea.addEventListener('drop', e => {
      e.preventDefault();
      ifArea.classList.remove('drag-over-if');
      if (!paletteDragType) return;
      addBlock(paletteDragType, path);
      paletteDragType = null;
    });

    el.querySelector('.add-if-block').addEventListener('click', e => {
      e.stopPropagation();
      const p = JSON.parse(e.target.dataset.ifPath);
      if (state.insertTarget && JSON.stringify(state.insertTarget) === JSON.stringify(p)) {
        clearInsertTarget();
      } else {
        setInsertTarget(p);
      }
    });

    el.querySelector('.btn-dup-path').addEventListener('click', e => {
      e.stopPropagation();
      duplicateBlockAtPath(JSON.parse(e.target.dataset.path));
    });

    el.querySelector('.btn-rm-path').addEventListener('click', e => {
      e.stopPropagation();
      removeBlockAtPath(JSON.parse(e.target.dataset.path));
    });

    if (path.length === 1) setupBlockDragReorder(el, path[0]);
    return el;
  }

  if (step.type === 'reset_canceled') {
    el.innerHTML = `
      <span class="block-label">🔁 reset_canceled</span>
      <button class="btn-dup btn-dup-path" data-path='${pathJson}' title="複製">⧉</button>
      <button class="btn-remove btn-rm-path" data-path='${pathJson}'>✕</button>`;
    el.querySelector('.btn-dup-path').addEventListener('click', e => {
      e.stopPropagation();
      duplicateBlockAtPath(JSON.parse(e.target.dataset.path));
    });
    el.querySelector('.btn-rm-path').addEventListener('click', e => {
      e.stopPropagation();
      removeBlockAtPath(JSON.parse(e.target.dataset.path));
    });
    if (path.length === 1) setupBlockDragReorder(el, path[0]);
    return el;
  }

  const def = BLOCK_DEFS[step.type];
  let inputHtml = '';
  if (def.inputType === 'number') {
    const mainLbl = def.extraField
      ? `<span class="extra-label">${def.mainLabel ?? '張數'}</span>` : '';
    inputHtml = mainLbl + buildNumCtrl(step.value ?? def.default, 1, 20, 'main');
  } else if (def.inputType === 'select') {
    const opts = (def.options || []).map(o =>
      `<option${(step.card ?? def.default) === o ? ' selected' : ''}>${o}</option>`
    ).join('');
    inputHtml = `<select class="block-input main-input">${opts}</select>`;
  }

  let extraHtml = '';
  if (def.extraField) {
    const ef = def.extraField;
    extraHtml = `<span class="extra-label">${ef.label}</span>
      ${buildNumCtrl(step[ef.field] ?? ef.default, 1, 20, 'extra')}`;
  }

  el.innerHTML = `
    <span class="block-label">${step.type}</span>
    ${inputHtml}
    ${extraHtml}
    <button class="btn-dup btn-dup-path" data-path='${pathJson}' title="複製">⧉</button>
    <button class="btn-remove btn-rm-path" data-path='${pathJson}'>✕</button>`;

  if (def.inputType === 'number') {
    wireNumCtrl(el, 'main', 1, 20, path, 'value');
  } else if (def.inputType === 'select') {
    el.querySelector('.main-input').addEventListener('change', e => {
      updateStepValue(path, def.field, e.target.value);
    });
  }

  if (def.extraField) {
    wireNumCtrl(el, 'extra', 1, 20, path, def.extraField.field);
  }

  el.querySelector('.btn-dup-path').addEventListener('click', e => {
    e.stopPropagation();
    duplicateBlockAtPath(JSON.parse(e.target.dataset.path));
  });

  el.querySelector('.btn-rm-path').addEventListener('click', e => {
    e.stopPropagation();
    removeBlockAtPath(JSON.parse(e.target.dataset.path));
  });

  if (path.length === 1) setupBlockDragReorder(el, path[0]);
  return el;
}

// ---------------------------------------------------------------------------
// Drag-and-drop — reorder top-level blocks
// ---------------------------------------------------------------------------
function setupBlockDragReorder(el, idx) {
  el.setAttribute('draggable', 'true');
  el.addEventListener('dragstart', e => {
    // Only reorder if not dragging from palette
    if (paletteDragType) return;
    dragSrcIndex = idx;
    el.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/plain', 'reorder');
  });
  el.addEventListener('dragend', () => {
    el.classList.remove('dragging');
    document.querySelectorAll('.drag-target').forEach(d => d.classList.remove('drag-target'));
    dragSrcIndex = null;
  });
  el.addEventListener('dragover', e => {
    if (paletteDragType) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    el.classList.add('drag-target');
  });
  el.addEventListener('dragleave', () => el.classList.remove('drag-target'));
  el.addEventListener('drop', e => {
    e.preventDefault();
    el.classList.remove('drag-target');
    if (dragSrcIndex === null || dragSrcIndex === idx) return;
    const moved = state.sequence.splice(dragSrcIndex, 1)[0];
    const insertAt = dragSrcIndex < idx ? idx - 1 : idx;
    state.sequence.splice(insertAt, 0, moved);
    dragSrcIndex = null;
    renderSequence();
  });
}

function setupAreaDrop() {
  const area = $('sequence-area');
  area.addEventListener('dragover', e => {
    e.preventDefault();
    area.classList.add('drag-over');
  });
  area.addEventListener('dragleave', () => area.classList.remove('drag-over'));
  area.addEventListener('drop', e => {
    e.preventDefault();
    area.classList.remove('drag-over');
    if (paletteDragType) {
      addBlock(paletteDragType, null);
      paletteDragType = null;
    }
  });
}

// ---------------------------------------------------------------------------
// Palette buttons
// ---------------------------------------------------------------------------
function setupPalette() {
  document.querySelectorAll('.block-btn').forEach(btn => {
    // Click: add to insertTarget or top-level
    btn.addEventListener('click', () => {
      const type = btn.dataset.type;
      addBlock(type, state.insertTarget);
    });

    // Drag from palette
    btn.addEventListener('dragstart', e => {
      paletteDragType = btn.dataset.type;
      e.dataTransfer.effectAllowed = 'copy';
      e.dataTransfer.setData('text/plain', btn.dataset.type);
    });
    btn.addEventListener('dragend', () => {
      paletteDragType = null;
    });
  });

  // Clear insertTarget on Escape or clicking blank area
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && state.insertTarget) clearInsertTarget();
  });
  document.addEventListener('click', e => {
    if (state.insertTarget && !e.target.closest('.seq-block') && !e.target.closest('.block-btn')) {
      clearInsertTarget();
    }
  });
}

// ---------------------------------------------------------------------------
// Opponent config tags
// ---------------------------------------------------------------------------
function renderOppConfigs() {
  const list = $('opp-config-list');
  list.innerHTML = '';
  state.oppConfigs.forEach((cfg, i) => {
    const tag = document.createElement('div');
    tag.className = 'config-tag';
    tag.innerHTML = `<span>${cfg.cx}CX/${cfg.size}</span><button data-i="${i}">✕</button>`;
    tag.querySelector('button').addEventListener('click', e => {
      state.oppConfigs.splice(parseInt(e.target.dataset.i), 1);
      renderOppConfigs();
    });
    list.appendChild(tag);
  });
}

function setupDeckConfig() {
  const sizeSlider = $('opp-size');
  const cxSlider = $('opp-cx');
  $('opp-size-val').textContent = sizeSlider.value;
  $('opp-cx-val').textContent = cxSlider.value;
  sizeSlider.addEventListener('input', () => $('opp-size-val').textContent = sizeSlider.value);
  cxSlider.addEventListener('input',  () => $('opp-cx-val').textContent = cxSlider.value);
  $('btn-add-config').addEventListener('click', () => {
    state.oppConfigs.push({ size: parseInt(sizeSlider.value), cx: parseInt(cxSlider.value) });
    renderOppConfigs();
  });
  renderOppConfigs();
}

// ---------------------------------------------------------------------------
// Results Modal
// ---------------------------------------------------------------------------
function openResultsModal() {
  if (!state.lastResults) return;
  const body = $('results-modal-body');
  body.innerHTML = buildResultsHtml(state.lastResults);
  $('results-modal').classList.add('open');
}

function closeResultsModal() {
  $('results-modal').classList.remove('open');
}

// ---------------------------------------------------------------------------
// Export PNG — Canvas 2D API
// ---------------------------------------------------------------------------
// Smooth HSL gradient: dark (0%) → red → orange → yellow → green (100%)
function heatColor(pct) {
  if (pct === 0) return '#0d1117';
  // hue 0→120 (red→green), saturated & reasonably bright
  const hue = Math.round((pct / 100) * 120);
  const sat = 90;
  const lit = pct < 15 ? 28 : pct < 40 ? 38 : pct < 70 ? 44 : 40;
  return `hsl(${hue},${sat}%,${lit}%)`;
}

async function exportPNG() {
  if (!state.lastResults) { alert('請先執行模擬'); return; }

  const name = $('active-combo-name').value.trim() || '殺招模擬結果';
  const images = state.activeCombo.images.filter(Boolean);
  const data = state.lastResults;

  // Load card images
  const imgEls = (await Promise.all(images.map(src => new Promise(res => {
    const img = new Image();
    img.onload = () => res(img);
    img.onerror = () => res(null);
    img.src = src;
  })))).filter(Boolean);

  // ── Layout constants (at 1920px wide) ──────────────────────────────────
  const W   = 1920;
  const PAD = 64;
  const INNER_W = W - PAD * 2;

  const TITLE_H        = 100;
  const FAN_H          = imgEls.length > 0 ? 320 : 0;
  const TABLE_HEADER_H = 80;
  const ROW_H          = 48;
  const TABLE_H        = TABLE_HEADER_H + ROW_H * data.results.length + 12;
  const SECTION_GAP    = 48;
  const CHART_TITLE_H  = 56;
  const CHART_ROW_H    = 48;
  const CHART_H        = CHART_TITLE_H + CHART_ROW_H * data.results.length + 12;

  const contentH = PAD + TITLE_H + FAN_H + TABLE_H + SECTION_GAP + CHART_H + PAD;
  // Ensure at least 16:9
  const TOTAL_H  = Math.max(contentH, Math.round(W * 9 / 16));

  const canvas = document.createElement('canvas');
  canvas.width  = W;
  canvas.height = TOTAL_H;
  const ctx = canvas.getContext('2d');

  // ── Background ──────────────────────────────────────────────────────────
  const bgGrad = ctx.createLinearGradient(0, 0, W, TOTAL_H);
  bgGrad.addColorStop(0, '#12151f');
  bgGrad.addColorStop(1, '#1e2338');
  ctx.fillStyle = bgGrad;
  ctx.beginPath();
  ctx.roundRect(0, 0, W, TOTAL_H, 0);
  ctx.fill();

  let y = PAD;

  // ── Title ───────────────────────────────────────────────────────────────
  const titleGrad = ctx.createLinearGradient(PAD, 0, PAD + 900, 0);
  titleGrad.addColorStop(0, '#b07ef8');
  titleGrad.addColorStop(1, '#5dc8f0');
  ctx.fillStyle = titleGrad;
  ctx.font = 'bold 52px "Segoe UI", system-ui, sans-serif';
  ctx.textBaseline = 'top';
  ctx.textAlign = 'left';
  ctx.fillText(name, PAD, y + 10);
  y += TITLE_H;

  // ── Card fan (contain, no crop) ─────────────────────────────────────────
  if (imgEls.length > 0) {
    const angles     = FAN_ANGLES[imgEls.length] || [0];
    const MAX_CARD_W = 160;
    const MAX_CARD_H = 260;
    const cardSpacing = 150;   // wide gap between cards
    const totalWidth  = (imgEls.length - 1) * cardSpacing + MAX_CARD_W;
    const startX  = W / 2 - totalWidth / 2;
    const centerY = y + FAN_H / 2 + 10;
    const midI    = Math.floor(imgEls.length / 2);

    imgEls.forEach((img, i) => {
      const rad = (angles[i] || 0) * Math.PI / 180;
      const cx  = startX + i * cardSpacing + MAX_CARD_W / 2;
      const ty  = i === midI ? -14 : 0;

      // Contain-fit: scale to fit MAX_CARD_W × MAX_CARD_H, keep aspect ratio
      const scale = Math.min(MAX_CARD_W / img.naturalWidth, MAX_CARD_H / img.naturalHeight);
      const dw = img.naturalWidth  * scale;
      const dh = img.naturalHeight * scale;
      const dx = -dw / 2;
      const dy = -dh / 2;

      ctx.save();
      ctx.translate(cx, centerY + ty);
      ctx.rotate(rad);
      ctx.shadowColor   = 'rgba(0,0,0,0.7)';
      ctx.shadowBlur    = 32;
      ctx.shadowOffsetY = 12;
      ctx.beginPath();
      ctx.roundRect(dx, dy, dw, dh, 12);
      ctx.clip();
      ctx.drawImage(img, dx, dy, dw, dh);
      ctx.restore();
    });

    y += FAN_H;
  }

  // ── Heat table ──────────────────────────────────────────────────────────
  const NUM_COLS = DAMAGE_LABELS.length;
  const LABEL_W  = 120;
  const COL_W    = Math.floor((INNER_W - LABEL_W) / NUM_COLS);

  // Table background
  ctx.fillStyle = 'rgba(30,35,56,0.85)';
  ctx.beginPath();
  ctx.roundRect(PAD, y, INNER_W, TABLE_H, 10);
  ctx.fill();

  // Header row 1 — damage labels (e.g. "3-6")
  ctx.fillStyle = '#9aa3c0';
  ctx.font = '600 18px "Segoe UI", system-ui, sans-serif';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'center';
  DAMAGE_LABELS.forEach((lbl, i) => {
    ctx.fillText(lbl, PAD + LABEL_W + i * COL_W + COL_W / 2, y + 22);
  });

  // Header row 2 — ≥N thresholds
  ctx.fillStyle = '#6b74a0';
  ctx.font = '600 15px "Segoe UI", system-ui, sans-serif';
  data.damage_range.forEach((d, i) => {
    ctx.fillText(`≥${d}`, PAD + LABEL_W + i * COL_W + COL_W / 2, y + 58);
  });

  // Divider
  ctx.strokeStyle = '#2e3350';
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.moveTo(PAD, y + TABLE_HEADER_H);
  ctx.lineTo(PAD + INNER_W, y + TABLE_HEADER_H);
  ctx.stroke();

  // Data rows
  data.results.forEach((row, ri) => {
    const rowY = y + TABLE_HEADER_H + ri * ROW_H;

    ctx.fillStyle = '#9aa3c0';
    ctx.font = '600 17px "Segoe UI", system-ui, sans-serif';
    ctx.textBaseline = 'middle';
    ctx.textAlign = 'left';
    ctx.fillText(row.label, PAD + 10, rowY + ROW_H / 2);

    row.rates.forEach((pct, ci) => {
      const cellX = PAD + LABEL_W + ci * COL_W;

      // Cell background: smooth gradient fill
      ctx.fillStyle = heatColor(pct);
      ctx.beginPath();
      ctx.roundRect(cellX + 2, rowY + 3, COL_W - 4, ROW_H - 6, 5);
      ctx.fill();

      // Cell value
      ctx.fillStyle = pct === 0 ? '#4a5070' : '#ffffff';
      ctx.font = `600 ${pct >= 100 ? 14 : 16}px "Segoe UI", system-ui, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText(String(pct), cellX + COL_W / 2, rowY + ROW_H / 2);
    });

    if (ri < data.results.length - 1) {
      ctx.strokeStyle = 'rgba(46,51,80,0.4)';
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(PAD, rowY + ROW_H);
      ctx.lineTo(PAD + INNER_W, rowY + ROW_H);
      ctx.stroke();
    }
  });

  y += TABLE_H + SECTION_GAP;

  // ── Bar chart ───────────────────────────────────────────────────────────
  const chartDmgIdx = 7;
  const chartDmg = data.damage_range[chartDmgIdx] ?? 8;

  ctx.fillStyle = '#9aa3c0';
  ctx.font = '700 22px "Segoe UI", system-ui, sans-serif';
  ctx.textBaseline = 'middle';
  ctx.textAlign = 'left';
  ctx.fillText(`致命率  ≥${chartDmg} 傷害`, PAD, y + CHART_TITLE_H / 2);
  y += CHART_TITLE_H;

  const CHART_LABEL_W = 120;
  const CHART_RATIO_W = 80;
  const CHART_BAR_W   = INNER_W - CHART_LABEL_W - CHART_RATIO_W;
  const BAR_H         = 30;

  data.results.forEach((row, ri) => {
    const pct  = row.rates[chartDmgIdx] ?? 0;
    const rowY = y + ri * CHART_ROW_H;
    const barY = rowY + (CHART_ROW_H - BAR_H) / 2;

    ctx.fillStyle = '#6b74a0';
    ctx.font = '600 17px "Segoe UI", system-ui, sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(row.label, PAD + CHART_LABEL_W - 8, rowY + CHART_ROW_H / 2);

    // Bar background
    ctx.fillStyle = 'rgba(30,35,56,0.85)';
    ctx.beginPath();
    ctx.roundRect(PAD + CHART_LABEL_W, barY, CHART_BAR_W, BAR_H, 5);
    ctx.fill();

    if (pct > 0) {
      const fillW = Math.max(4, (pct / 100) * CHART_BAR_W);

      // Bar fill — gradient from left edge to fill end
      const barGrad = ctx.createLinearGradient(PAD + CHART_LABEL_W, 0, PAD + CHART_LABEL_W + fillW, 0);
      barGrad.addColorStop(0, heatColor(Math.min(pct, 5)));
      barGrad.addColorStop(1, heatColor(pct));
      ctx.fillStyle = barGrad;
      ctx.beginPath();
      ctx.roundRect(PAD + CHART_LABEL_W, barY, fillW, BAR_H, 5);
      ctx.fill();

      if (pct >= 8) {
        ctx.fillStyle = '#ffffff';
        ctx.font = '700 15px "Segoe UI", system-ui, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        ctx.fillText(pct + '%', PAD + CHART_LABEL_W + fillW - 6, barY + BAR_H / 2);
      }
    }

    const m = row.label.match(/(\d+)\s*CX\s*\/\s*(\d+)/);
    const ratioStr = m ? (parseInt(m[2]) / parseInt(m[1])).toFixed(2) + '×' : '';
    ctx.fillStyle = '#6b74a0';
    ctx.font = '600 15px "Segoe UI", system-ui, sans-serif';
    ctx.textAlign = 'right';
    ctx.textBaseline = 'middle';
    ctx.fillText(ratioStr, PAD + CHART_LABEL_W + CHART_BAR_W + CHART_RATIO_W, rowY + CHART_ROW_H / 2);
  });

  canvas.toBlob(blob => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ws_sim_${Date.now()}.png`;
    a.click();
    URL.revokeObjectURL(url);
  }, 'image/png');
}

function exportCSV(data) {
  const headers = ['牌庫設定', ...DAMAGE_LABELS.map((l,i) => `${l}(≥${i+1})`)];
  const rows = data.results.map(r => [r.label, ...r.rates]);
  const csv = [headers, ...rows].map(r => r.join(',')).join('\n');
  const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `ws_sim_${Date.now()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Build results HTML
// ---------------------------------------------------------------------------
function buildResultsHtml(data, forExport = false) {
  const dmgRange = data.damage_range;
  let html = '';

  if (!forExport && state.activeCombo.name) {
    const validImgs = state.activeCombo.images.filter(Boolean);
    const imgsHtml = validImgs.map(img => `<img class="active-combo-thumb" src="${img}" alt="" />`).join('');
    html += `<div class="active-combo-header">
      ${imgsHtml ? `<div class="active-combo-images">${imgsHtml}</div>` : ''}
      <div class="active-combo-name">${escapeHtml(state.activeCombo.name)}</div>
    </div>`;
  }

  html += `<div class="results-meta">${data.iterations.toLocaleString()} 次迭代・${data.elapsed_sec}s</div>`;

  // Table — double header row: level-life notation + threshold
  html += `<div style="overflow-x:auto"><table class="results-table"><thead>
    <tr>
      <th class="col-label" rowspan="2">牌庫設定</th>`;
  DAMAGE_LABELS.forEach(l => {
    html += `<th class="dmg-col">${l}</th>`;
  });
  html += `</tr><tr>`;
  dmgRange.forEach(d => {
    html += `<th class="dmg-col">≥${d}</th>`;
  });
  html += `</tr></thead><tbody>`;

  data.results.forEach(row => {
    html += `<tr><td class="col-label">${row.label}</td>`;
    row.rates.forEach(pct => {
      const bg = pctColor(pct);
      const textColor = pct > 60 ? '#fff' : '#eee';
      html += `<td><div class="cell-rate" style="background:${bg};color:${textColor}">
        <div class="cell-bar" style="width:${pct}%"></div>
        <span class="cell-val">${pct}</span>
      </div></td>`;
    });
    html += `</tr>`;
  });
  html += `</tbody></table></div>`;

  // Bar chart at ≥8 damage (index 7)
  const chartIdx = 7;
  const chartDmg = dmgRange[chartIdx] ?? 8;
  html += `<div class="chart-area">
    <h3>致命率 (≥${chartDmg} 傷害)</h3>
    <div class="chart-rows">`;
  data.results.forEach(row => {
    const pct = row.rates[chartIdx] ?? 0;
    // Compression ratio
    const m = row.label.match(/(\d+)\s*CX\s*\/\s*(\d+)/);
    const ratioStr = m ? (parseInt(m[2]) / parseInt(m[1])).toFixed(2) + '×' : '';
    html += `<div class="chart-row">
      <div class="chart-row-label">${row.label}</div>
      <div class="chart-bar-wrap">
        <div class="chart-bar" style="width:${pct}%;background:${pctColor(pct)}">
          ${pct >= 10 ? pct + '%' : ''}
        </div>
      </div>
      <div class="chart-ratio">${ratioStr}</div>
    </div>`;
  });
  html += `</div></div>`;

  return html;
}

// ---------------------------------------------------------------------------
// Render results
// ---------------------------------------------------------------------------
function renderResults(data) {
  $('results-area').innerHTML = buildResultsHtml(data);
}

// ---------------------------------------------------------------------------
// Simulation
// ---------------------------------------------------------------------------
async function runSimulation() {
  const btn = $('btn-run');
  const status = $('run-status');

  if (state.sequence.length === 0) {
    status.textContent = '請先加入效果積木';
    status.className = 'run-status error';
    return;
  }

  btn.disabled = true;
  status.textContent = '計算中…';
  status.className = 'run-status loading';

  const payload = {
    sequence: state.sequence,
    iterations: parseInt($('iterations').value),
    opp_deck_configs: state.oppConfigs.map(c => ({
      first_deck_size: c.size,
      first_climaxes: c.cx,
    })),
    opp_second_deck: {
      size: parseInt($('opp2-size').value),
      climaxes: parseInt($('opp2-cx').value),
    },
    own_deck: {
      total_cards: parseInt($('own-total').value),
      soul_triggers: parseInt($('own-soul').value),
      two_soul_triggers: parseInt($('own-2soul').value),
    },
  };

  try {
    const res = await fetch(API_BASE + '/api/simulate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: res.statusText }));
      throw new Error(err.detail || res.statusText);
    }

    const data = await res.json();
    state.lastResults = data;
    renderResults(data);
    $('results-toolbar').style.display = 'flex';
    status.textContent = `完成 — ${data.iterations.toLocaleString()} 次迭代，耗時 ${data.elapsed_sec}s`;
    status.className = 'run-status done';
  } catch (e) {
    status.textContent = `錯誤：${e.message}`;
    status.className = 'run-status error';
    console.error(e);
  } finally {
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------
document.addEventListener('DOMContentLoaded', async () => {
  setupPalette();
  setupAreaDrop();
  setupDeckConfig();
  setupImageSlots();
  await fetchCombos();

  // Results toolbar hidden until first simulation
  $('results-toolbar').style.display = 'none';

  // Combo controls
  $('btn-load-combo').addEventListener('click', () => {
    const id = $('combo-select').value;
    if (id) loadComboById(id);
  });
  $('btn-save-combo').addEventListener('click', apiSaveCombo);
  $('btn-new-combo').addEventListener('click', newCombo);
  $('btn-clear').addEventListener('click', () => {
    state.sequence = [];
    state.insertTarget = null;
    renderSequence();
    $('run-status').textContent = '';
  });

  // Run simulation
  $('btn-run').addEventListener('click', runSimulation);

  // Results modal
  $('btn-expand-results').addEventListener('click', openResultsModal);
  $('results-modal-close').addEventListener('click', closeResultsModal);
  $('results-modal').addEventListener('click', e => {
    if (e.target === $('results-modal')) closeResultsModal();
  });

  // Export buttons
  $('btn-export-png').addEventListener('click', exportPNG);
  $('btn-export-csv').addEventListener('click', () => {
    if (state.lastResults) exportCSV(state.lastResults);
  });
  $('results-modal-export-png').addEventListener('click', exportPNG);
  $('results-modal-export-csv').addEventListener('click', () => {
    if (state.lastResults) exportCSV(state.lastResults);
  });
});
