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
   Called via onchange="updateMod('str', this.value)"         */
function updateMod(ability, scoreStr) {
  const el = document.getElementById('mod_' + ability);
  if (!el) return;
  const score = parseInt(scoreStr, 10);
  if (isNaN(score)) { el.textContent = '—'; return; }
  const mod = Math.floor((score - 10) / 2);
  el.textContent = mod >= 0 ? '+' + mod : String(mod);
}

/* ── Track duplicate selections in Standard Array / Random Roll */
function trackUsed() {
  const selects = Array.from(document.querySelectorAll('.score-select'));
  const used    = {};
  selects.forEach(s => {
    const v = s.value;
    if (v) used[v] = (used[v] || 0) + 1;
  });

  selects.forEach(s => {
    const v = s.value;
    const isDup = v && used[v] > 1;
    s.style.borderColor = isDup ? '#c00' : '';
    s.setAttribute('aria-invalid', isDup ? 'true' : 'false');
  });
}

/* ── Point Buy live calculation ──────────────────────────────
   Expects PB_COSTS, PB_BUDGET, PB_MIN, PB_MAX, ABILITIES
   defined in the step 5 template's inline script block.       */
function pbUpdate() {
  if (typeof PB_COSTS === 'undefined') return;

  let spent = 0;
  let valid = true;

  ABILITIES.forEach(ab => {
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
    const cost = (isNaN(score) || score < PB_MIN || score > PB_MAX)
      ? null
      : (PB_COSTS[String(score)] ?? PB_COSTS[score] ?? 0);

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
      input.style.borderColor = (score < PB_MIN || score > PB_MAX) ? '#c00' : '';
    }
  });

  const remaining = PB_BUDGET - spent;
  const remEl = document.getElementById('pb-remaining');
  if (remEl) {
    remEl.textContent = String(remaining);
    remEl.style.color = (remaining < 0 || !valid) ? '#c00' : '';
  }
}

/* ── Method panel switcher ───────────────────────────────────
   Called via onchange="switchMethod('standard_array')"       */
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
