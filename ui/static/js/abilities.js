'use strict';
/* abilities.js — Step 5 ability score generation and assignment */

// ── Class suggestion mapping (highest priority stat → highest score) ──────────
const CLASS_SUGGESTIONS = {
  barbarian: {str:15, con:14, dex:13, wis:12, cha:10, int:8},
  bard:      {cha:15, dex:14, con:13, wis:12, int:10, str:8},
  cleric:    {wis:15, con:14, str:13, cha:12, int:10, dex:8},
  druid:     {wis:15, con:14, int:13, dex:12, cha:10, str:8},
  fighter:   {str:15, con:14, dex:13, wis:12, int:10, cha:8},
  monk:      {dex:15, wis:14, con:13, str:12, int:10, cha:8},
  paladin:   {str:15, cha:14, con:13, wis:12, int:10, dex:8},
  ranger:    {dex:15, wis:14, con:13, str:12, int:10, cha:8},
  rogue:     {dex:15, int:14, con:13, cha:12, wis:10, str:8},
  sorcerer:  {cha:15, con:14, dex:13, wis:12, int:10, str:8},
  warlock:   {cha:15, con:14, dex:13, wis:12, int:10, str:8},
  wizard:    {int:15, con:14, dex:13, wis:12, cha:10, str:8},
};
const DEFAULT_SUGGESTION = {str:15, dex:14, con:13, int:12, wis:10, cha:8};

// ── Ability metadata ──────────────────────────────────────────────────────────
const ABILITIES = ['str', 'dex', 'con', 'int', 'wis', 'cha'];
const ABILITY_FULL = {
  str:'strength', dex:'dexterity', con:'constitution',
  int:'intelligence', wis:'wisdom', cha:'charisma',
};
const ABILITY_NAMES = {
  str:'Strength', dex:'Dexterity', con:'Constitution',
  int:'Intelligence', wis:'Wisdom', cha:'Charisma',
};

// ── Mutable state ─────────────────────────────────────────────────────────────
let _method  = null;   // 'standard_array' | 'point_buy' | 'random_roll' | null
let _pool    = [];     // SA/RR: full pool including any duplicates
let _assign  = {};     // SA/RR: {ability_key: raw_int}
let _pb      = {};     // PB:    {ability_key: score_int}
let _rolled  = [];     // RR:    scores fetched from server
let _flex    = {};     // {ability_key: 0|bonus_amount} for flexible racial bonus slots
let _asi     = [];     // [{type:'', ab1:'', ab2:''}, …] one entry per earned ASI slot

// ── Bootstrap ─────────────────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  _initCards();
  _restoreState();
  document.getElementById('ability-form')
    .addEventListener('submit', _onSubmit);

  // Scroll to and focus error summary if present
  const errBox = document.getElementById('error-summary');
  if (errBox) {
    errBox.scrollIntoView({behavior: 'smooth', block: 'start'});
    errBox.focus();
  }
});

// ── Card setup ────────────────────────────────────────────────────────────────
function _initCards() {
  const cards = Array.from(document.querySelectorAll('[role="radio"]'));
  cards.forEach((card, i) => {
    card.addEventListener('click', () => selectMethod(card.dataset.method));
    card.addEventListener('keydown', e => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        selectMethod(card.dataset.method);
      } else if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
        e.preventDefault();
        cards[(i + 1) % cards.length].focus();
      } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
        e.preventDefault();
        cards[(i - 1 + cards.length) % cards.length].focus();
      }
    });
  });
}

// ── Restore server-provided saved state on page load ──────────────────────────
function _restoreState() {
  const savedMethod = (typeof SAVED_METHOD !== 'undefined') ? SAVED_METHOD : null;
  if (!savedMethod) return;

  _method = savedMethod;

  // Restore flexible bonus assignments
  if (typeof SAVED_FLEX !== 'undefined' && SAVED_FLEX) {
    ABILITIES.forEach(ab => { _flex[ab] = SAVED_FLEX[ab] || 0; });
  }

  // Restore ASI slot assignments
  if (typeof SAVED_ASI !== 'undefined' && Array.isArray(SAVED_ASI)) {
    _asi = SAVED_ASI.map(s => ({
      type: s.type || '',
      ab1:  s.ab1  || '',
      ab2:  s.ab2  || '',
    }));
  }

  const saved = (typeof SAVED_SCORES !== 'undefined') ? SAVED_SCORES : {};
  const hasSaved = ABILITIES.some(ab => saved[ab] !== undefined && saved[ab] !== 0);

  if (_method === 'point_buy') {
    const min = _pbMin();
    ABILITIES.forEach(ab => { _pb[ab] = hasSaved ? (saved[ab] || min) : min; });

  } else if (_method === 'random_roll') {
    _rolled = (typeof ROLLED_SCORES !== 'undefined') ? [...ROLLED_SCORES] : [];
    _pool   = [..._rolled];
    if (hasSaved) ABILITIES.forEach(ab => { if (saved[ab]) _assign[ab] = saved[ab]; });

  } else {
    // standard_array
    _pool = _standardPool();
    if (hasSaved) {
      ABILITIES.forEach(ab => { if (saved[ab]) _assign[ab] = saved[ab]; });
    } else {
      _applySuggestion();
    }
  }

  _updateCardState();
  _renderPhase2(false); // false = don't shift focus on restore
}

// ── Method selection (called by card click / keyboard) ────────────────────────
function selectMethod(newMethod) {
  const switching = (newMethod !== _method);
  _method = newMethod;

  if (switching) {
    _assign = {}; _flex = {}; _pb = {}; _pool = [];
    if (_method === 'standard_array') {
      _pool = _standardPool();
      _applySuggestion();
    } else if (_method === 'random_roll') {
      // Keep any previously rolled scores so the user doesn't lose them
      // if they briefly switch away and back
      _rolled = (typeof ROLLED_SCORES !== 'undefined') ? [...ROLLED_SCORES] : [];
      _pool   = [..._rolled];
    } else if (_method === 'point_buy') {
      const min = _pbMin();
      ABILITIES.forEach(ab => { _pb[ab] = min; });
    }
  }

  document.getElementById('ability-method-input').value = _method;
  _updateCardState();

  const phase2 = document.getElementById('phase2');
  const wasHidden = phase2.classList.contains('hidden');
  phase2.classList.remove('hidden');
  _renderPhase2(wasHidden); // shift focus when first revealed
}

function _applySuggestion() {
  const cls = (typeof CHAR_CLASS !== 'undefined' ? CHAR_CLASS : 'fighter').toLowerCase();
  _assign = Object.assign({}, CLASS_SUGGESTIONS[cls] || DEFAULT_SUGGESTION);
}

function _updateCardState() {
  const cards = document.querySelectorAll('[role="radio"]');
  let hasSelected = false;
  cards.forEach(card => {
    const sel = (card.dataset.method === _method);
    card.setAttribute('aria-checked', sel ? 'true' : 'false');
    card.setAttribute('tabindex', sel ? '0' : '-1');
    card.classList.toggle('method-selected', sel);
    if (sel) hasSelected = true;
  });
  if (!hasSelected && cards.length) cards[0].setAttribute('tabindex', '0');
}

// ── Phase 2 rendering ─────────────────────────────────────────────────────────
function _renderPhase2(focusHeading) {
  _renderPool();
  _renderValueCells();
  _renderBonusCells();
  _renderAsiSection();  // render ASI UI before updating rows so _asi is in DOM
  _updateAllRows();
  if (focusHeading) {
    const h = document.getElementById('phase2-heading');
    if (h) h.focus();
  }
}

// ── Score pool ────────────────────────────────────────────────────────────────
function _renderPool() {
  const sec = document.getElementById('score-pool-section');
  if (!sec) return;

  if (_method === 'standard_array') {
    sec.innerHTML =
      '<p class="score-pool-label">Standard Array — assign each score exactly once:</p>' +
      _chipsHtml(_pool);

  } else if (_method === 'random_roll') {
    if (_pool.length) {
      sec.innerHTML =
        '<div class="pool-header">' +
          '<p class="score-pool-label">Your rolled scores — assign each to an ability:</p>' +
          '<button type="button" class="btn btn-outline btn-sm" onclick="rerollScores()">Reroll All</button>' +
        '</div>' +
        _chipsHtml(_pool);
    } else {
      sec.innerHTML =
        '<p class="roll-desc">Click the button to generate six ability scores. You can reroll before assigning.</p>' +
        '<button type="button" class="btn btn-accent" id="roll-btn" onclick="rollScores()">Roll My Scores</button>';
    }

  } else if (_method === 'point_buy') {
    const budget = _pbBudget();
    const spent  = _pbSpent();
    const rem    = budget - spent;
    const over   = rem < 0;
    sec.innerHTML =
      '<p class="pb-budget-label" aria-live="polite" aria-atomic="true">' +
        'Points remaining: ' +
        '<strong class="' + (over ? 'over-budget' : '') + '">' + rem + '</strong>' +
        ' / ' + budget +
        (over ? ' <span class="over-budget">— Over budget!</span>' : '') +
      '</p>';
  }
}

function _chipsHtml(pool) {
  const usedCounts = {};
  Object.values(_assign).forEach(v => { usedCounts[v] = (usedCounts[v] || 0) + 1; });
  const poolCounts = {};
  pool.forEach(v => { poolCounts[v] = (poolCounts[v] || 0) + 1; });

  const chips = [...pool].sort((a, b) => b - a).map(v => {
    const fullyUsed = (usedCounts[v] || 0) >= poolCounts[v];
    return '<span class="pool-chip' + (fullyUsed ? ' chip-used' : '') + '"' +
           ' data-value="' + v + '"' +
           ' aria-hidden="true"' +
           (fullyUsed ? ' aria-disabled="true"' : '') + '>' + v + '</span>';
  }).join('');

  return '<p class="score-pool" id="score-pool-display" aria-hidden="true">' + chips + '</p>';
}

// ── Value cells ───────────────────────────────────────────────────────────────
function _renderValueCells() {
  ABILITIES.forEach(ab => _renderValueCell(ab));
}

function _renderValueCell(ab) {
  const cell = document.getElementById('val-cell-' + ab);
  if (!cell) return;

  if (_method === 'standard_array' || _method === 'random_roll') {
    cell.innerHTML = _dropdownHtml(ab);
  } else if (_method === 'point_buy') {
    cell.innerHTML = _stepperHtml(ab);
  }
}

function _dropdownHtml(ab) {
  if (_method === 'random_roll' && !_pool.length) {
    return '<span class="val-pending">Roll first</span>';
  }

  const myVal  = _assign[ab] || null;
  const avail  = _availableFor(ab);
  const unique = [...new Set(_pool)].sort((a, b) => b - a);

  let opts = '<option value="">— assign —</option>';
  unique.forEach(v => {
    const ok = avail.includes(v) || v === myVal;
    opts += '<option value="' + v + '"' +
            (v === myVal ? ' selected' : '') +
            (!ok ? ' disabled' : '') + '>' + v + '</option>';
  });

  return '<select class="score-select" name="score_' + ab + '" id="sel-' + ab + '"' +
         ' onchange="onValueChange(\'' + ab + '\', this.value)"' +
         ' aria-label="' + ABILITY_NAMES[ab] + ' score">' +
         opts + '</select>';
}

function _stepperHtml(ab) {
  const min   = _pbMin();
  const max   = _pbMax();
  const costs = _pbCosts();
  const score = _pb[ab] || min;
  const spent = _pbSpent();
  const budget = _pbBudget();

  const currCost = costs[score]     || 0;
  const nextCost = costs[score + 1] || 0;
  const canDec   = score > min;
  const canInc   = score < max && (spent - currCost + nextCost) <= budget;

  return '<input type="hidden" name="score_' + ab + '" id="hidden-score-' + ab + '" value="' + score + '">' +
         '<div class="pb-stepper" role="group" aria-label="' + ABILITY_NAMES[ab] + ' score">' +
           '<button type="button" class="pb-btn"' +
           ' onclick="pbChange(\'' + ab + '\',-1)"' +
           ' aria-label="Decrease ' + ABILITY_NAMES[ab] + '"' +
           (canDec ? '' : ' disabled') + '>−</button>' +
           '<span class="pb-score" aria-live="polite" aria-atomic="true">' + score + '</span>' +
           '<button type="button" class="pb-btn"' +
           ' onclick="pbChange(\'' + ab + '\',1)"' +
           ' aria-label="Increase ' + ABILITY_NAMES[ab] + '"' +
           (canInc ? '' : ' disabled') + '>+</button>' +
         '</div>';
}

function _availableFor(ab) {
  const poolCounts = {};
  _pool.forEach(v => { poolCounts[v] = (poolCounts[v] || 0) + 1; });
  const usedCounts = {};
  ABILITIES.forEach(a => {
    if (a !== ab && _assign[a]) usedCounts[_assign[a]] = (usedCounts[_assign[a]] || 0) + 1;
  });
  const result = [];
  Object.entries(poolCounts).forEach(([v, total]) => {
    if (total - (usedCounts[v] || 0) > 0) result.push(Number(v));
  });
  return result;
}

// ── Value change ──────────────────────────────────────────────────────────────
function onValueChange(ab, valStr) {
  if (!valStr) {
    delete _assign[ab];
  } else {
    _assign[ab] = parseInt(valStr, 10);
  }
  ABILITIES.forEach(other => { if (other !== ab) _renderValueCell(other); });
  _updateChips();
  _updateRow(ab);
}

// ── Point Buy ─────────────────────────────────────────────────────────────────
function pbChange(ab, delta) {
  const min    = _pbMin();
  const max    = _pbMax();
  const costs  = _pbCosts();
  const budget = _pbBudget();
  const cur    = _pb[ab] || min;
  const nxt    = cur + delta;

  if (nxt < min || nxt > max) return;

  const others = ABILITIES.filter(a => a !== ab)
    .reduce((sum, a) => sum + (costs[_pb[a]] || 0), 0);
  if (others + (costs[nxt] || 0) > budget) return;

  _pb[ab] = nxt;
  _renderPool();
  _renderValueCells();
  _updateAllRows();
}

// ── Bonus cells ───────────────────────────────────────────────────────────────
function _renderBonusCells() {
  ABILITIES.forEach(ab => _renderBonusCell(ab));
}

function _renderBonusCell(ab) {
  const cell = document.getElementById('bonus-cell-' + ab);
  if (!cell) return;

  const racial     = (typeof RACIAL_BONUSES !== 'undefined') ? RACIAL_BONUSES : {};
  const flexTotal  = racial.flexible || 0;
  const flexAmount = racial.flexible_amount || 1;
  const fixedExcl  = racial.fixed_bonus_abilities || [];
  const fixed      = racial[ABILITY_FULL[ab]] || 0;

  // Fixed bonus (e.g. half-elf CHA +2): show value and stop
  if (fixed !== 0) {
    cell.innerHTML = '<span class="bonus-fixed">' + (fixed > 0 ? '+' + fixed : String(fixed)) + '</span>';
    return;
  }

  // Flexible bonus dropdown — skip abilities excluded by fixed bonus (e.g. half-elf CHA)
  if (flexTotal > 0 && !fixedExcl.includes(ab)) {
    const flexUsed = ABILITIES.filter(a => !fixedExcl.includes(a) && (_flex[a] || 0) > 0).length;
    const myFlex   = _flex[ab] || 0;
    if (myFlex > 0 || flexUsed < flexTotal) {
      cell.innerHTML =
        '<select class="flex-select"' +
        ' onchange="onFlexChange(\'' + ab + '\', this.value)"' +
        ' aria-label="' + ABILITY_NAMES[ab] + ' flexible bonus">' +
        '<option value="0"' + (myFlex === 0 ? ' selected' : '') + '>—</option>' +
        '<option value="' + flexAmount + '"' + (myFlex === flexAmount ? ' selected' : '') + '>+' + flexAmount + '</option>' +
        '</select>';
      const hf = document.getElementById('hidden-flex-' + ab);
      if (hf) hf.value = myFlex;
      return;
    }
  }

  cell.innerHTML = '<span class="bonus-fixed">—</span>';
}

function onFlexChange(ab, valStr) {
  _flex[ab] = parseInt(valStr, 10) || 0;
  const hf = document.getElementById('hidden-flex-' + ab);
  if (hf) hf.value = _flex[ab];
  _renderBonusCells();
  ABILITIES.forEach(a => _updateRow(a));
}

// ── Row score / modifier ──────────────────────────────────────────────────────
function _updateRow(ab) {
  const scoreCell = document.getElementById('score-cell-' + ab);
  const modCell   = document.getElementById('mod-cell-' + ab);
  if (!scoreCell || !modCell) return;

  const raw    = (_method === 'point_buy') ? (_pb[ab] || null) : (_assign[ab] || null);
  const racial = (typeof RACIAL_BONUSES !== 'undefined') ? RACIAL_BONUSES : {};
  const bonus  = (racial[ABILITY_FULL[ab]] || 0) + (_flex[ab] || 0) + _getAsiBonus(ab);

  if (raw === null) {
    scoreCell.textContent = '—';
    modCell.textContent   = '—';
    modCell.className     = 'mod-cell';
  } else {
    const score = raw + bonus;
    const mod   = Math.floor((score - 10) / 2);
    scoreCell.textContent = String(score);
    modCell.textContent   = mod >= 0 ? '+' + mod : String(mod);
    modCell.className     = 'mod-cell' + (mod > 0 ? ' mod-pos' : mod < 0 ? ' mod-neg' : '');
  }
}

function _updateAllRows() {
  ABILITIES.forEach(ab => _updateRow(ab));
}

function _updateChips() {
  const usedCounts = {};
  Object.values(_assign).forEach(v => { usedCounts[v] = (usedCounts[v] || 0) + 1; });
  const poolCounts = {};
  _pool.forEach(v => { poolCounts[v] = (poolCounts[v] || 0) + 1; });

  document.querySelectorAll('#score-pool-display .pool-chip').forEach(chip => {
    const v    = parseInt(chip.dataset.value, 10);
    const full = (usedCounts[v] || 0) >= (poolCounts[v] || 1);
    chip.classList.toggle('chip-used', full);
    chip.setAttribute('aria-disabled', full ? 'true' : 'false');
  });
}

// ── Random Roll API calls ─────────────────────────────────────────────────────
function rollScores() {
  const btn = document.getElementById('roll-btn');
  if (btn) { btn.disabled = true; btn.textContent = 'Rolling…'; }

  fetch('/roll_scores', {
    method: 'POST',
    headers: {'X-Requested-With': 'XMLHttpRequest'},
  })
    .then(r => r.json())
    .then(data => {
      _rolled = data.scores;
      _pool   = [..._rolled];
      _assign = {};
      _renderPool();
      _renderValueCells();
      _renderBonusCells();
      _updateAllRows();
    })
    .catch(() => {
      if (btn) { btn.disabled = false; btn.textContent = 'Roll My Scores'; }
    });
}

function rerollScores() {
  fetch('/roll_scores', {
    method: 'POST',
    headers: {'X-Requested-With': 'XMLHttpRequest'},
  })
    .then(r => r.json())
    .then(data => {
      _rolled = data.scores;
      _pool   = [..._rolled];
      _assign = {};
      _renderPool();
      _renderValueCells();
      _renderBonusCells();
      _updateAllRows();
    });
}

// ── Form submit handler ───────────────────────────────────────────────────────
function _onSubmit() {
  // For SA/RR the <select name="score_ab"> elements are live in the DOM.
  // For PB the <input type="hidden" name="score_ab"> values were set by pbChange.
  // Just ensure the method field is current.
  document.getElementById('ability-method-input').value = _method || '';
}

// ── Point Buy helpers ─────────────────────────────────────────────────────────
function _pbMin()    { return (typeof PB_MIN    !== 'undefined') ? PB_MIN    : 8;  }
function _pbMax()    { return (typeof PB_MAX    !== 'undefined') ? PB_MAX    : 15; }
function _pbBudget() { return (typeof PB_BUDGET !== 'undefined') ? PB_BUDGET : 27; }
function _pbCosts()  { return (typeof PB_COSTS  !== 'undefined') ? PB_COSTS  : {}; }
function _pbSpent()  {
  const c = _pbCosts();
  return ABILITIES.reduce((sum, ab) => sum + (c[_pb[ab]] || 0), 0);
}

function _standardPool() {
  return (typeof STANDARD_ARRAY !== 'undefined') ? [...STANDARD_ARRAY] : [15,14,13,12,10,8];
}

// ── ASI (Ability Score Improvement) ──────────────────────────────────────────

function _getAsiBonus(ab) {
  let bonus = 0;
  _asi.forEach(slot => {
    if (!slot || !slot.type) return;
    if (slot.type === 'double' && slot.ab1 === ab) {
      bonus += 2;
    } else if (slot.type === 'split') {
      if (slot.ab1 === ab) bonus += 1;
      if (slot.ab2 === ab) bonus += 1;
    }
  });
  return bonus;
}

function onAsiTypeChange(i, type) {
  if (!_asi[i]) _asi[i] = {type: '', ab1: '', ab2: ''};
  _asi[i].type = type;
  _asi[i].ab1  = '';
  _asi[i].ab2  = '';

  const th  = document.getElementById('asi-' + i + '-type-h');
  const a1h = document.getElementById('asi-' + i + '-ab1-h');
  const a2h = document.getElementById('asi-' + i + '-ab2-h');
  if (th)  th.value  = type;
  if (a1h) a1h.value = '';
  if (a2h) a2h.value = '';

  const dPanel = document.getElementById('asi-' + i + '-dpanel');
  const sPanel = document.getElementById('asi-' + i + '-spanel');
  if (dPanel) dPanel.classList.toggle('hidden', type !== 'double');
  if (sPanel) sPanel.classList.toggle('hidden', type !== 'split');

  // Reset visible selects so previous choice doesn't linger
  ['asi-' + i + '-ab1-d', 'asi-' + i + '-ab1-s', 'asi-' + i + '-ab2-s'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.value = '';
  });

  _updateAllRows();
}

function onAsiChange(i) {
  if (!_asi[i]) _asi[i] = {type: '', ab1: '', ab2: ''};
  const type = _asi[i].type;
  let ab1 = '', ab2 = '';

  if (type === 'double') {
    const sel = document.getElementById('asi-' + i + '-ab1-d');
    ab1 = sel ? sel.value : '';
  } else if (type === 'split') {
    const s1 = document.getElementById('asi-' + i + '-ab1-s');
    const s2 = document.getElementById('asi-' + i + '-ab2-s');
    ab1 = s1 ? s1.value : '';
    ab2 = s2 ? s2.value : '';
  }

  _asi[i].ab1 = ab1;
  _asi[i].ab2 = ab2;

  const a1h = document.getElementById('asi-' + i + '-ab1-h');
  const a2h = document.getElementById('asi-' + i + '-ab2-h');
  if (a1h) a1h.value = ab1;
  if (a2h) a2h.value = ab2;

  _updateAllRows();
}

function _renderAsiSection() {
  const sec    = document.getElementById('asi-section');
  if (!sec) return;
  const earned = (typeof ASI_SLOTS_EARNED !== 'undefined') ? ASI_SLOTS_EARNED : 0;
  if (earned === 0) { sec.innerHTML = ''; return; }

  // Pad _asi array to match earned slots
  while (_asi.length < earned) _asi.push({type: '', ab1: '', ab2: ''});

  let html = '<h2 class="step-section-heading">Ability Score Improvements</h2>';
  html += '<p class="asi-subtitle">Your class grants ' + earned +
          ' improvement slot' + (earned > 1 ? 's' : '') +
          '. Each slot adds +2 to one ability or +1 to two abilities.' +
          ' Slots are optional — your facilitator may advise skipping.</p>';

  for (let i = 0; i < earned; i++) {
    html += _asiSlotHtml(i, _asi[i] || {type: '', ab1: '', ab2: ''});
  }
  sec.innerHTML = html;
}

function _asiSlotHtml(i, slot) {
  const labels = {
    str: 'Strength', dex: 'Dexterity', con: 'Constitution',
    int: 'Intelligence', wis: 'Wisdom', cha: 'Charisma',
  };

  function abilityOpts(selected) {
    let o = '<option value="">— choose —</option>';
    ABILITIES.forEach(ab => {
      o += '<option value="' + ab + '"' + (selected === ab ? ' selected' : '') + '>' + labels[ab] + '</option>';
    });
    return o;
  }

  const isDouble = slot.type === 'double';
  const isSplit  = slot.type === 'split';

  let h = '<div class="asi-slot">';
  h += '<h3 class="asi-label">Improvement ' + (i + 1) + '</h3>';

  // Radio buttons for type selection (name only used for browser grouping; hidden field submits)
  h += '<div class="asi-type-choice">';
  [['', 'Skip (optional)'], ['double', '+2 to one ability'], ['split', '+1 to two abilities']].forEach(([val, lbl]) => {
    const chk = (slot.type === val || (!slot.type && val === '')) ? ' checked' : '';
    h += '<label class="asi-radio-label"><input type="radio" name="asi_ui_' + i + '" value="' + val + '"' + chk +
         ' onchange="onAsiTypeChange(' + i + ', \'' + val + '\')"> ' + lbl + '</label>';
  });
  h += '</div>';

  // Hidden fields for form submission
  h += '<input type="hidden" name="asi_' + i + '_type" id="asi-' + i + '-type-h" value="' + (slot.type || '') + '">';
  h += '<input type="hidden" name="asi_' + i + '_ab1"  id="asi-' + i + '-ab1-h"  value="' + (slot.ab1 || '') + '">';
  h += '<input type="hidden" name="asi_' + i + '_ab2"  id="asi-' + i + '-ab2-h"  value="' + (slot.ab2 || '') + '">';

  // +2 to one ability
  h += '<div id="asi-' + i + '-dpanel" class="asi-double-panel' + (!isDouble ? ' hidden' : '') + '">';
  h += '<label class="asi-field-label">Which ability? ';
  h += '<select id="asi-' + i + '-ab1-d" onchange="onAsiChange(' + i + ')">' + abilityOpts(slot.ab1) + '</select>';
  h += '</label></div>';

  // +1 to two abilities
  h += '<div id="asi-' + i + '-spanel" class="asi-split-panel' + (!isSplit ? ' hidden' : '') + '">';
  h += '<label class="asi-field-label">First ability: ';
  h += '<select id="asi-' + i + '-ab1-s" onchange="onAsiChange(' + i + ')">' + abilityOpts(slot.ab1) + '</select>';
  h += '</label>';
  h += '<label class="asi-field-label">Second ability: ';
  h += '<select id="asi-' + i + '-ab2-s" onchange="onAsiChange(' + i + ')">' + abilityOpts(slot.ab2) + '</select>';
  h += '</label></div>';

  h += '</div>';
  return h;
}
