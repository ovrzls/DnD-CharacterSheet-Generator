/* wizard.js — OtG character creator interactivity */

/* ── Description display (species / class / background) ─────
   Called via onchange="showDescription(this, 'target-id')"
   The select element must have data-descriptions='{"name":{...}}'  */
function showDescription(select, targetId) {
  const box = document.getElementById(targetId);
  if (!box) return;

  const key   = select.value;
  let   data  = {};
  try { data = JSON.parse(select.dataset.descriptions || "{}"); } catch (_) {}

  const item = data[key];
  if (!item) {
    box.innerHTML = '<p class="desc-placeholder">Select an option above to see a description.</p>';
    return;
  }

  let html = '';
  if (item.desc) html += `<p>${escHtml(item.desc)}</p>`;

  // Species extras
  if (item.size || item.speed) {
    html += `<p class="desc-meta">Size: ${escHtml(String(item.size || '—'))} · Speed: ${item.speed || 30} ft</p>`;
  }

  // Class extras
  if (item.hit_die) {
    html += `<p class="desc-meta">Hit Die: d${item.hit_die}`;
    if (item.is_caster && item.spell_ability) {
      html += ` · Spellcasting: ${escHtml(item.spell_ability)}`;
    }
    html += '</p>';
  }

  // Background extras
  if (item.feature) {
    html += `<p class="desc-meta"><strong>Special Ability:</strong> ${escHtml(item.feature)}`;
    if (item.feature_desc) html += ` — ${escHtml(item.feature_desc)}`;
    html += '</p>';
  }

  box.innerHTML = html || '<p class="desc-placeholder">No description available.</p>';
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/* ── Ability score modifier display ─────────────────────────
   Called via onchange="updateMod('str', this.value)"
   Also updates racial total and modifier if RACIAL_BONUSES defined. */
function updateMod(ability, scoreStr) {
  const modEl   = document.getElementById('mod_'   + ability);
  const totalEl = document.getElementById('total_' + ability);
  if (!modEl) return;

  const base = parseInt(scoreStr, 10);
  if (isNaN(base)) {
    modEl.textContent   = '—';
    if (totalEl) totalEl.textContent = '—';
    return;
  }

  const racial = (window.RACIAL_BONUSES && window.RACIAL_BONUSES[ability]) || 0;
  const total  = base + racial;

  if (totalEl) totalEl.textContent = String(total);

  const modVal = Math.floor((total - 10) / 2);
  modEl.textContent = modVal >= 0 ? '+' + modVal : String(modVal);
}

/* ── Track duplicate selections in Standard Array / Random Roll
   window.SCORE_POOL holds the full pool including duplicates
   (e.g. [17,17,14,13,12,10]).  trackUsed() counts how many
   times each value is *available* vs *selected* and disables
   options only when every slot for that value is taken.       */
function trackUsed() {
  const selects = Array.from(document.querySelectorAll('.score-select'));
  if (!selects.length) return;

  // Build availability counts from window.SCORE_POOL.
  // window.SCORE_POOL is set by the inline <script> in step4_abilities.html
  // and mutated by rollScores(); using window. ensures cross-file visibility.
  const poolCount = {};
  const pool = window.SCORE_POOL;
  if (pool && pool.length) {
    pool.forEach(v => {
      const k = String(v);
      poolCount[k] = (poolCount[k] || 0) + 1;
    });
  }

  // Count how many selects currently have each value chosen
  const selCount = {};
  selects.forEach(s => {
    if (s.value) selCount[s.value] = (selCount[s.value] || 0) + 1;
  });

  selects.forEach(sel => {
    const myVal = sel.value;

    Array.from(sel.options).forEach(opt => {
      if (!opt.value) return;
      const v     = opt.value;
      const avail = poolCount[v] || 0;
      const used  = selCount[v]  || 0;
      // Slots remaining for this option, adding back 1 if this select already holds it
      const slotsLeft = avail - used + (v === myVal ? 1 : 0);
      opt.disabled = slotsLeft <= 0;
    });

    const isOver = myVal && (selCount[myVal] || 0) > (poolCount[myVal] || 0);
    sel.style.borderColor = isOver ? '#c00' : '';
    sel.setAttribute('aria-invalid', isOver ? 'true' : 'false');
  });

  // Dim chips whose available slots are fully used
  document.querySelectorAll('#score-pool-display .pool-chip').forEach(chip => {
    const v     = String(chip.dataset.value);
    const avail = poolCount[v] || 0;
    const used  = selCount[v]  || 0;
    chip.classList.toggle('chip-used', avail > 0 && used >= avail);
  });
}

/* ── AJAX score roller (Standard Array Re-roll / Random Roll) ──
   Fetches fresh scores from the server, updates the pool display
   and all dropdowns live — no page reload required.             */
function rollScores() {
  const initBtn   = document.getElementById('initial-roll-btn');
  const rerollBtn = document.getElementById('reroll-btn');
  [initBtn, rerollBtn].forEach(b => {
    if (b) { b.disabled = true; b.textContent = 'Rolling…'; }
  });

  fetch('/api/roll-scores')
    .then(r => r.json())
    .then(data => {
      const scores = data.scores;   // sorted descending ints from server

      // Update window.SCORE_POOL (full pool with duplicates) for trackUsed()
      window.SCORE_POOL = scores;

      // Refresh pool-chip display (shows duplicates so user sees "17 17 14 …")
      const poolEl = document.getElementById('score-pool-display');
      if (poolEl) {
        poolEl.innerHTML = [...scores]
          .sort((a, b) => b - a)
          .map(s => `<span class="pool-chip" data-value="${s}">${s}</span>`)
          .join('');
      }

      // Persist rolled scores so method switching can restore them
      window.ROLLED_SCORES = scores;

      // Rebuild every dropdown with UNIQUE option values (dedup for clean display).
      // trackUsed() uses window.SCORE_POOL counts, not option counts, so
      // duplicate slots are still correctly honoured.
      const uniqueScores = [...new Set(scores)].sort((a, b) => b - a);
      document.querySelectorAll('.score-select').forEach(sel => {
        const ab = sel.id.replace('score_', '');
        let html = '<option value="">—</option>';
        uniqueScores.forEach(s => {
          html += `<option value="${s}">${s}</option>`;
        });
        sel.innerHTML = html;
        sel.value = '';
        updateMod(ab, '');
      });

      trackUsed();

      // Reveal the assignment section and hide the initial prompt
      const prompt = document.getElementById('roll-prompt');
      const assign = document.getElementById('score-assignment');
      if (prompt) prompt.classList.add('hidden');
      if (assign) assign.classList.remove('hidden');

      // Reveal the Next button (was hidden before first roll)
      const nextBtn = document.getElementById('next-btn');
      if (nextBtn) nextBtn.style.display = '';
    })
    .catch(() => {
      // Silent fail — user can retry
    })
    .finally(() => {
      if (initBtn)   { initBtn.disabled   = false; initBtn.textContent   = 'Roll My Scores'; }
      if (rerollBtn) { rerollBtn.disabled = false; rerollBtn.textContent = 'Re-roll Scores'; }
    });
}

/* ── Point Buy live calculation ──────────────────────────────
   Expects PB_COSTS, PB_BUDGET, PB_MIN, PB_MAX, ABILITIES
   defined in the step 5 template's inline script block.       */
function pbUpdate() {
  if (typeof window.PB_COSTS === 'undefined') return;

  let spent = 0;
  let valid = true;

  (window.ABILITIES || []).forEach(ab => {
    const input = document.getElementById('score_pb_' + ab);
    const modEl = document.getElementById('pbmod_' + ab);
    const costEl= document.getElementById('pbcost_' + ab);
    if (!input) return;

    const score = parseInt(input.value, 10);

    // Show modifier
    if (modEl) {
      if (isNaN(score)) {
        modEl.textContent = '—';
      } else {
        const mod = Math.floor((score - 10) / 2);
        modEl.textContent = mod >= 0 ? '+' + mod : String(mod);
      }
    }

    // Show cost
    const cost = (isNaN(score) || score < window.PB_MIN || score > window.PB_MAX)
      ? null
      : (window.PB_COSTS[String(score)] ?? window.PB_COSTS[score] ?? 0);

    if (costEl) {
      costEl.textContent = cost !== null ? String(cost) : '!';
      costEl.style.color = cost === null ? '#c00' : '';
    }

    if (cost !== null) {
      spent += cost;
    } else {
      valid = false;
    }

    // Flag out-of-range
    if (!isNaN(score)) {
      input.style.borderColor = (score < window.PB_MIN || score > window.PB_MAX) ? '#c00' : '';
    }
  });

  const remaining = window.PB_BUDGET - spent;
  const remEl = document.getElementById('pb-remaining');
  if (remEl) {
    remEl.textContent = String(remaining);
    remEl.style.color = (remaining < 0 || !valid) ? '#c00' : '';
  }
}

/* ── Method panel switcher ───────────────────────────────────
   Called via onchange="switchMethod('standard_array')"       */
function _rebuildDropdowns(scores) {
  const uniqueScores = [...new Set(scores)].sort((a, b) => b - a);
  document.querySelectorAll('.score-select').forEach(sel => {
    const ab = sel.id.replace('score_', '');
    let html = '<option value="">—</option>';
    uniqueScores.forEach(s => {
      html += `<option value="${s}">${s}</option>`;
    });
    sel.innerHTML = html;
    sel.value = '';
    updateMod(ab, '');
  });
}

function _rebuildChips(scores) {
  const poolEl = document.getElementById('score-pool-display');
  if (!poolEl) return;
  poolEl.innerHTML = [...scores]
    .sort((a, b) => b - a)
    .map(s => `<span class="pool-chip" data-value="${s}">${s}</span>`)
    .join('');
}

function _loadStandardArray() {
  const sa = window.STANDARD_ARRAY || [15, 14, 13, 12, 10, 8];
  window.SCORE_POOL = sa;
  _rebuildChips(sa);
  _rebuildDropdowns(sa);

  const prompt = document.getElementById('roll-prompt');
  const assign = document.getElementById('score-assignment');
  if (prompt) prompt.classList.add('hidden');
  if (assign) assign.classList.remove('hidden');

  const nextBtn   = document.getElementById('next-btn');
  const rerollBtn = document.getElementById('reroll-btn');
  if (nextBtn)   nextBtn.style.display   = '';
  if (rerollBtn) rerollBtn.style.display = 'none';

  trackUsed();
}

function _loadRandomRoll() {
  const rolled = window.ROLLED_SCORES;
  if (rolled && rolled.length) {
    window.SCORE_POOL = rolled;
    _rebuildChips(rolled);
    _rebuildDropdowns(rolled);

    const prompt = document.getElementById('roll-prompt');
    const assign = document.getElementById('score-assignment');
    if (prompt) prompt.classList.add('hidden');
    if (assign) assign.classList.remove('hidden');

    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) nextBtn.style.display = '';

    const rerollBtn = document.getElementById('reroll-btn');
    if (rerollBtn) rerollBtn.style.display = '';
  } else {
    const prompt = document.getElementById('roll-prompt');
    const assign = document.getElementById('score-assignment');
    if (prompt) prompt.classList.remove('hidden');
    if (assign) assign.classList.add('hidden');

    const nextBtn = document.getElementById('next-btn');
    if (nextBtn) nextBtn.style.display = 'none';

    const rerollBtn = document.getElementById('reroll-btn');
    if (rerollBtn) rerollBtn.style.display = 'none';
  }

  trackUsed();
}

function switchMethod(method) {
  const panels = {
    'standard_array': 'panel-standard',
    'random_roll':    'panel-standard',
    'point_buy':      'panel-pb',
  };

  ['panel-standard', 'panel-pb'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.classList.add('hidden');
  });

  const target = panels[method];
  if (target) {
    const el = document.getElementById(target);
    if (el) el.classList.remove('hidden');
  }

  // Update card highlight
  document.querySelectorAll('.method-card').forEach(card => {
    const radio = card.querySelector('input[type="radio"]');
    card.classList.toggle('method-selected', radio && radio.checked);
  });

  // Reload panel content for array/roll methods
  if (method === 'standard_array') {
    _loadStandardArray();
  } else if (method === 'random_roll') {
    _loadRandomRoll();
  }
}

/* ── Init on page load ───────────────────────────────────────*/
document.addEventListener('DOMContentLoaded', function () {
  // Initialise modifier displays for saved scores
  document.querySelectorAll('.score-select').forEach(sel => {
    if (sel.value) {
      const ab = sel.id.replace('score_', '');
      updateMod(ab, sel.value);
    }
  });

  // Initialise point buy costs
  pbUpdate();

  // Mark any already-duplicate selects
  if (document.querySelector('.score-select')) {
    trackUsed();
  }
});
