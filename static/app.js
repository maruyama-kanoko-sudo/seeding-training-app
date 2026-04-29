'use strict';

const App = (() => {
  // ── State ──────────────────────────────────────────────────────────────
  let state = {
    user: null,
    selectedCategory: null,
    selectedCategoryName: null,
    selectedMode: null,
    categoryProgress: null,
    questions: [],
    questionIndex: 0,
    currentTemplate: null,
    reorderSelected: [],
    idealOpen: false,
  };

  // ── API ────────────────────────────────────────────────────────────────
  async function api(path, method = 'GET', body = null) {
    const opts = { method, credentials: 'include', headers: { 'Content-Type': 'application/json' } };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch('/api' + path, opts);
    return res.json();
  }

  // ── Helpers ────────────────────────────────────────────────────────────
  function showScreen(id) {
    document.querySelectorAll('.screen').forEach(s => s.classList.remove('active'));
    document.getElementById(id).classList.add('active');
    window.scrollTo(0, 0);
  }

  function toast(msg, duration = 2500) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.classList.add('show');
    setTimeout(() => el.classList.remove('show'), duration);
  }

  function escHtml(s) {
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function escAttr(s) { return String(s).replace(/'/g, "\\'"); }

  function scoreToTitle(score) {
    if (!score || score <= 59) return '練習スタート';
    if (score <= 69) return '見習い営業';
    if (score <= 79) return 'あと少し';
    if (score <= 89) return '現場OK';
    if (score <= 99) return '即決メーカー';
    return 'シーディングマスター';
  }

  // ── Auth ───────────────────────────────────────────────────────────────
  async function login() {
    const name = document.getElementById('login-name').value.trim();
    const email = document.getElementById('login-email').value.trim();
    if (!name || !email) { toast('⚠️ 名前とメールアドレスを入力してください'); return; }
    const data = await api('/register', 'POST', { name, email });
    if (data.error) { toast('❌ ' + data.error); return; }
    state.user = data.user;
    toast('🎉 ' + (data.message || 'ようこそ！'));
    await loadHome();
  }

  async function logout() {
    await api('/logout', 'POST');
    state.user = null;
    showScreen('cover-screen');
  }

  // ── Home ───────────────────────────────────────────────────────────────
  async function loadHome() {
    showScreen('home-screen');

    const [homeData, catsData] = await Promise.all([api('/home'), api('/categories')]);
    if (homeData.error) { showScreen('cover-screen'); return; }

    state.user = homeData.user;
    document.getElementById('home-username').textContent = homeData.user.name + ' さん';

    const latestScore = homeData.latest_score;
    if (latestScore !== null && latestScore !== undefined) {
      document.getElementById('home-score-text').textContent =
        `最新スコア: ${latestScore}点 ／ ${homeData.title || ''}`;
    } else {
      document.getElementById('home-score-text').textContent = '最新スコア: ---';
    }

    // Show admin nav if admin
    const isAdmin = state.user.role === 'admin';
    ['nav-admin-history', 'nav-admin-home'].forEach(id => {
      const btn = document.getElementById(id);
      if (btn) btn.style.display = isAdmin ? 'flex' : 'none';
    });

    renderIslands(catsData.categories || []);
  }

  const ISLAND_THEMES = ['theme-gold', 'theme-teal', 'theme-purple', 'theme-blue'];

  function renderIslands(categories) {
    const grid = document.getElementById('home-islands');

    grid.innerHTML = categories.map((c, i) => {
      const prog = c.progress || {};
      const theme = ISLAND_THEMES[i % ISLAND_THEMES.length];

      const dots = ['quick', 'reproduction', 'simulation'].map(mode => {
        const m = prog[mode] || {};
        let cls = '';
        if (!m.unlocked) {
          cls = 'locked';
        } else if (m.best_score !== null && m.best_score !== undefined && m.best_score >= 80) {
          cls = 'done';
        } else if (m.count > 0) {
          cls = 'in-progress';
        }
        const labels = { quick: 'クイック', reproduction: '再現', simulation: '実戦' };
        return `<div class="mode-dot ${cls}" title="${labels[mode]}"></div>`;
      }).join('');

      const simBest = (prog.simulation || {}).best_score;
      const quickBest = (prog.quick || {}).best_score;
      const allCleared = simBest !== null && simBest !== undefined && simBest >= 80;
      const scoreText = allCleared
        ? '🏆 クリア済み'
        : quickBest !== null && quickBest !== undefined
          ? `最高 ${quickBest}点`
          : '未挑戦';

      // Short name for display (strip "渋りトーク" suffix)
      const shortName = c.name.replace('渋りトーク', '').replace('トーク', '');

      return `
        <div class="island-card ${theme}" onclick="App.selectCategory(${c.id}, '${escAttr(c.name)}')">
          <div class="island-icon-area">
            <span class="island-emoji">${c.emoji}</span>
          </div>
          <div class="island-info">
            <div class="island-name">${escHtml(shortName)}</div>
            <div class="island-desc">${escHtml(c.description || '')}</div>
            <div class="island-footer">
              <div class="island-progress">${dots}</div>
              <div class="island-score">${scoreText}</div>
            </div>
          </div>
        </div>`;
    }).join('');
  }

  function showHome() { loadHome(); }

  // ── Mode Selection ─────────────────────────────────────────────────────
  async function selectCategory(categoryId, categoryName) {
    state.selectedCategory = categoryId;
    state.selectedCategoryName = categoryName;
    document.getElementById('mode-screen-title').textContent = categoryName;

    const data = await api('/progress/' + categoryId);
    state.categoryProgress = data.progress || {};
    updateModeCards(state.categoryProgress);
    showScreen('mode-screen');
  }

  function updateModeCards(progress) {
    const configs = [
      { mode: 'quick',        cardId: 'mode-card-quick', bestId: 'mode-best-quick', lockId: 'mode-lock-quick' },
      { mode: 'reproduction', cardId: 'mode-card-repro', bestId: 'mode-best-repro', lockId: 'mode-lock-repro' },
      { mode: 'simulation',   cardId: 'mode-card-sim',   bestId: 'mode-best-sim',   lockId: 'mode-lock-sim'   },
    ];
    const lockMessages = {
      reproduction: '🔒 クイック暗記で80点を取るとアンロック',
      simulation:   '🔒 再現チャレンジで80点を取るとアンロック',
    };

    configs.forEach(({ mode, cardId, bestId, lockId }) => {
      const p = progress[mode] || {};
      const card = document.getElementById(cardId);
      const bestEl = document.getElementById(bestId);
      const lockEl = document.getElementById(lockId);

      card.classList.remove('locked', 'done');

      if (!p.unlocked) {
        card.classList.add('locked');
        bestEl.className = 'mode-best none';
        bestEl.textContent = '🔒 ロック中';
        lockEl.textContent = lockMessages[mode] || '';
      } else {
        lockEl.textContent = '';
        if (p.best_score !== null && p.best_score !== undefined) {
          const passed = p.best_score >= 80;
          if (passed) card.classList.add('done');
          bestEl.className = 'mode-best ' + (passed ? 'passed' : 'in-progress');
          bestEl.textContent = '最高 ' + p.best_score + '点';
        } else {
          bestEl.className = 'mode-best none';
          bestEl.textContent = '未挑戦';
        }
      }
    });
  }

  // ── Start Mode ─────────────────────────────────────────────────────────
  async function startMode(mode) {
    const prog = state.categoryProgress || {};
    const p = prog[mode] || {};
    if (!p.unlocked) {
      const msg = {
        reproduction: '🔒 まずクイック暗記で80点以上を取ろう！',
        simulation:   '🔒 まず再現チャレンジで80点以上を取ろう！',
      }[mode] || '🔒 まずは前のモードをクリアしよう！';
      toast(msg, 3000);
      return;
    }

    state.selectedMode = mode;
    const modeLabels = { quick: 'クイック暗記', reproduction: '再現チャレンジ', simulation: '実戦シミュレーション' };
    document.getElementById('quiz-mode-label').textContent = modeLabels[mode] || mode;
    document.getElementById('quiz-cat-label').textContent = state.selectedCategoryName || '';

    const data = await api(`/questions?mode=${mode}&category_id=${state.selectedCategory}`);
    if (!data.questions || data.questions.length === 0) {
      toast('⚠️ この学習モードの問題がありません');
      return;
    }

    state.questions = data.questions;
    state.questionIndex = 0;

    if (data.questions[0].talk_template_id) {
      const t = await api('/templates/' + data.questions[0].talk_template_id);
      state.currentTemplate = t.template;
    } else {
      state.currentTemplate = null;
    }

    await showQuizQuestion();
    showScreen('quiz-screen');
  }

  // ── Quiz ───────────────────────────────────────────────────────────────
  async function showQuizQuestion() {
    const q = state.questions[state.questionIndex];
    const total = state.questions.length;
    const idx = state.questionIndex;

    document.getElementById('quiz-counter').textContent = `${idx + 1}/${total}`;
    document.getElementById('quiz-bar').style.width = `${(idx / total) * 100}%`;

    const body = document.getElementById('quiz-body');
    const submitBtn = document.getElementById('quiz-submit-btn');

    if (q.question_type === 'fill_blank') {
      body.innerHTML = renderFillBlank(q);
      submitBtn.style.display = 'block';
      submitBtn.textContent = '回答する';
      setTimeout(() => { const inp = document.getElementById('fill-input'); if (inp) inp.focus(); }, 100);
    } else if (q.question_type === 'reorder') {
      state.reorderSelected = [];
      body.innerHTML = renderReorder(q);
      submitBtn.style.display = 'block';
      submitBtn.textContent = '並び順を確認する';
    } else if (q.question_type === 'model_check') {
      body.innerHTML = renderModelCheck();
      submitBtn.style.display = 'block';
      submitBtn.textContent = '確認しました！次へ';
    } else {
      body.innerHTML = renderFreeText(q);
      submitBtn.style.display = 'none';
    }
  }

  function renderFillBlank(q) {
    return `
      <div class="customer-bubble">${escHtml(q.customer_text || '')}</div>
      <div style="font-size:14px;font-weight:700;color:var(--primary);margin-bottom:12px;">
        ${escHtml(q.prompt_text || '【　】に入る言葉は？')}
      </div>
      <input id="fill-input" class="fill-blank-input" type="text" placeholder="ここに入力" autocomplete="off"
        onkeydown="if(event.key==='Enter') App.submitAnswer()">`;
  }

  function renderReorder(q) {
    const choices = q.choices ? JSON.parse(q.choices) : [];
    const shuffled = [...choices].sort(() => Math.random() - 0.5);
    return `
      <div style="font-size:14px;font-weight:700;color:var(--text);margin-bottom:12px;">${escHtml(q.prompt_text || '')}</div>
      <div class="selected-order" id="reorder-selected">
        <div class="selected-order-placeholder">ここに選んだ順番が並びます</div>
      </div>
      <div class="reorder-area" id="reorder-choices">
        ${shuffled.map((c, i) => `
          <div class="reorder-chip" id="rchip-${i}" onclick="App.selectReorderChip(${i}, '${escAttr(c)}')">${escHtml(c)}</div>
        `).join('')}
      </div>
      <button class="btn-outline w-full" style="margin-top:8px;" onclick="App.resetReorder()">リセット</button>`;
  }

  function renderModelCheck() {
    const script = state.currentTemplate ? state.currentTemplate.full_script : '';
    const kp = state.currentTemplate ? (state.currentTemplate.key_phrases || []) : [];
    return `
      <div style="font-size:14px;font-weight:700;color:var(--primary);margin-bottom:10px;">📖 模範トークを読んで覚えましょう</div>
      <div class="script-box">${escHtml(script)}</div>
      ${kp.length ? `
        <div style="font-size:12px;font-weight:700;color:var(--text-light);margin:10px 0 8px;">🔑 必須キーフレーズ</div>
        <div>${kp.map(p => `<div style="background:#fff3cd;border-radius:8px;padding:8px 12px;margin-bottom:6px;font-size:13px;font-weight:600;">🔑 ${escHtml(p)}</div>`).join('')}</div>` : ''}`;
  }

  function renderFreeText(q) {
    const modeLabel = { reproduction: '📝 再現チャレンジ', simulation: '🎯 実戦シミュレーション' }[q.mode] || q.mode;
    const hintHtml = state.currentTemplate ? `
      <div style="margin-bottom:14px;">
        <button class="ideal-toggle" onclick="App.toggleHint()">
          💡 模範トークを見る <span id="hint-arrow">▼</span>
        </button>
        <div class="ideal-content" id="hint-content">${escHtml(state.currentTemplate.full_script)}</div>
      </div>` : '';
    return `
      <div style="font-size:12px;font-weight:700;color:var(--primary);margin-bottom:8px;">${modeLabel}</div>
      <div class="customer-bubble">${escHtml(q.customer_text || '')}</div>
      <div style="font-size:13px;color:var(--text-light);margin-bottom:12px;">${escHtml(q.prompt_text || '')}</div>
      ${hintHtml}
      <textarea id="free-textarea" class="answer-textarea" placeholder="ここにトークを入力してください..."></textarea>
      <button id="free-submit-btn" class="btn-primary mt-16" onclick="App.submitFree()">🤖 AI採点する</button>`;
  }

  function toggleHint() {
    const content = document.getElementById('hint-content');
    const arrow = document.getElementById('hint-arrow');
    if (!content || !arrow) return;
    content.classList.toggle('open');
    arrow.textContent = content.classList.contains('open') ? '▲' : '▼';
  }

  // ── Submit ─────────────────────────────────────────────────────────────
  async function submitAnswer() {
    const q = state.questions[state.questionIndex];
    if (q.question_type === 'fill_blank') {
      const inp = document.getElementById('fill-input');
      const answer = inp ? inp.value.trim() : '';
      if (!answer) { toast('⚠️ 答えを入力してください'); return; }
      await _doSubmit(q.id, answer);
    } else if (q.question_type === 'reorder') {
      const correct = q.correct_answer ? JSON.parse(q.correct_answer) : [];
      if (state.reorderSelected.length < correct.length) {
        toast('⚠️ すべてのステップを選んでください'); return;
      }
      await _doSubmit(q.id, JSON.stringify(state.reorderSelected));
    } else if (q.question_type === 'model_check') {
      await _doSubmit(q.id, '(模範トーク確認)');
    }
  }

  async function submitFree() {
    const q = state.questions[state.questionIndex];
    const textarea = document.getElementById('free-textarea');
    const answer = textarea ? textarea.value.trim() : '';
    if (!answer) { toast('⚠️ 回答を入力してください'); return; }
    const btn = document.getElementById('free-submit-btn');
    if (btn) { btn.textContent = '🤖 AI採点中...（10〜20秒かかります）'; btn.disabled = true; }
    await _doSubmit(q.id, answer);
    if (btn) { btn.textContent = '🤖 AI採点する'; btn.disabled = false; }
  }

  async function _doSubmit(questionId, answerText) {
    const data = await api('/answers', 'POST', { question_id: questionId, answer_text: answerText });
    if (data.error) { toast('❌ ' + data.error); return; }

    const q = state.questions[state.questionIndex];
    if (q && q.mode === 'simulation' && data.answer.score_total >= 80) {
      showCelebration(data.answer.score_total, data.answer.title);
      return;
    }

    showFeedback(data.answer, data.feedback);
  }

  // ── Reorder helpers ────────────────────────────────────────────────────
  function selectReorderChip(idx, value) {
    const chip = document.getElementById('rchip-' + idx);
    if (!chip || chip.classList.contains('used')) return;
    chip.classList.add('used');
    state.reorderSelected.push(value);
    renderSelectedOrder();
  }

  function renderSelectedOrder() {
    const container = document.getElementById('reorder-selected');
    if (!container) return;
    if (state.reorderSelected.length === 0) {
      container.innerHTML = '<div class="selected-order-placeholder">ここに選んだ順番が並びます</div>';
    } else {
      container.innerHTML = state.reorderSelected.map((v, i) => `
        <div class="selected-order-item">
          <span>${i + 1}. ${escHtml(v)}</span>
          <span style="cursor:pointer;opacity:0.7;" onclick="App.removeReorderItem(${i})">✕</span>
        </div>`).join('');
    }
  }

  function removeReorderItem(idx) {
    const removed = state.reorderSelected.splice(idx, 1)[0];
    document.querySelectorAll('.reorder-chip').forEach(c => {
      if (c.textContent === removed) c.classList.remove('used');
    });
    renderSelectedOrder();
  }

  function resetReorder() {
    state.reorderSelected = [];
    document.querySelectorAll('.reorder-chip').forEach(c => c.classList.remove('used'));
    renderSelectedOrder();
  }

  // ── Celebration ────────────────────────────────────────────────────────
  function showCelebration(score, title) {
    document.getElementById('celeb-score').textContent = score;
    document.getElementById('celeb-msg').innerHTML =
      `称号：<strong>${escHtml(title || scoreToTitle(score))}</strong>！<br>このトークを現場で使い続けよう！`;

    const container = document.getElementById('confetti-container');
    container.innerHTML = '';
    const colors = ['#f9ca24', '#6c5ce7', '#00b894', '#fd79a8', '#74b9ff', '#ff7675', '#a29bfe', '#ffffff'];
    for (let i = 0; i < 90; i++) {
      const piece = document.createElement('div');
      piece.className = 'confetti-piece';
      const color = colors[i % colors.length];
      const left = Math.random() * 100;
      const width = 6 + Math.random() * 10;
      const height = 8 + Math.random() * 14;
      const duration = 2.5 + Math.random() * 2.5;
      const delay = Math.random() * 2.5;
      piece.style.cssText = `left:${left}%;width:${width}px;height:${height}px;background:${color};` +
        `animation-duration:${duration}s;animation-delay:${delay}s;`;
      container.appendChild(piece);
    }

    showScreen('celebration-screen');
  }

  // ── Feedback ───────────────────────────────────────────────────────────
  function showFeedback(answer, feedback) {
    showScreen('feedback-screen');
    const score = answer.score_total;
    const passed = answer.is_passed;
    const q = state.questions[state.questionIndex];
    const modeMap = { quick: '⚡ クイック', reproduction: '📝 再現', simulation: '🎯 実戦' };

    let html = `
      <div class="card text-center">
        <div class="score-circle ${passed ? 'passed' : score < 40 ? 'failed' : ''}" style="margin:0 auto 12px;">
          <div class="score-number">${score}</div>
          <div class="score-label">点</div>
        </div>
        <div class="title-badge" style="margin-bottom:8px;">${escHtml(answer.title || '')}</div>
        <div style="margin-top:8px;display:flex;gap:6px;justify-content:center;flex-wrap:wrap;">
          <span class="badge ${passed ? 'badge-green' : 'badge-purple'}">${passed ? '✅ 合格！' : score >= 70 ? '📈 もう少し！' : '💪 練習しよう'}</span>
          ${q ? `<span class="badge badge-purple">${modeMap[q.mode] || q.mode}</span>` : ''}
        </div>
      </div>`;

    if (answer.has_compliance_ng && answer.compliance_ng_words && answer.compliance_ng_words.length) {
      html += `<div class="compliance-warning">⚠️ コンプライアンスNG：${escHtml(answer.compliance_ng_words.join('、'))}</div>`;
    }

    if (feedback) {
      if (feedback.structure_detail) {
        const sd = feedback.structure_detail;
        html += `
          <div class="card">
            <div class="card-title">スコア内訳</div>
            ${barRow('構成評価', answer.score_structure, 60)}
            ${barRow('共感・承認', sd.empathy, 12)}
            ${barRow('本質の言語化', sd.essence, 12)}
            ${barRow('第三者トーク', sd.third_party, 12)}
            ${barRow('未来提示', sd.future, 12)}
            ${barRow('クロージング', sd.closing, 12)}
            ${barRow('トーク再現度', answer.score_reproduction, 40)}
          </div>`;
      }

      if (feedback.good_points && feedback.good_points.length) {
        html += `
          <div class="card feedback-section">
            <h4>良かった点</h4>
            <div class="feedback-list">
              ${feedback.good_points.map(p => `<div class="feedback-item"><span class="icon">✅</span><span>${escHtml(p)}</span></div>`).join('')}
            </div>
          </div>`;
      }

      if (feedback.improvement_points && feedback.improvement_points.length) {
        html += `
          <div class="card feedback-section">
            <h4>改善ポイント</h4>
            <div class="feedback-list">
              ${feedback.improvement_points.map(p => `<div class="feedback-item"><span class="icon">🔧</span><span>${escHtml(p)}</span></div>`).join('')}
            </div>
          </div>`;
      }

      if (feedback.missing_key_phrases && feedback.missing_key_phrases.length) {
        html += `
          <div class="card">
            <div class="card-title">使えなかったキーフレーズ</div>
            ${feedback.missing_key_phrases.map(p => `<div style="background:#fff3cd;border-radius:8px;padding:8px 12px;margin-bottom:6px;font-size:13px;">🔑 ${escHtml(p)}</div>`).join('')}
          </div>`;
      }

      if (feedback.ideal_answer) {
        html += `
          <div class="card">
            <button class="ideal-toggle" onclick="App.toggleIdeal()">
              💡 理想のトーク例を見る <span id="ideal-arrow">▼</span>
            </button>
            <div class="ideal-content" id="fb-ideal-content">${escHtml(feedback.ideal_answer)}</div>
          </div>`;
      }
    }

    const hasNext = state.questionIndex < state.questions.length - 1;
    html += `<div style="display:flex;flex-direction:column;gap:10px;margin-top:8px;">`;
    if (hasNext) html += `<button class="btn-primary" onclick="App.nextQuestion()">次の問題へ →</button>`;
    html += `<button class="btn-outline" onclick="App.showHome()">ホームに戻る</button></div>`;

    document.getElementById('feedback-body').innerHTML = html;
  }

  function barRow(label, value, max) {
    const pct = Math.min(100, Math.round(((value || 0) / max) * 100));
    return `
      <div class="score-bar-row">
        <div class="score-bar-label">${label}</div>
        <div class="score-bar"><div class="score-bar-fill" style="width:${pct}%"></div></div>
        <div class="score-bar-num">${value !== undefined && value !== null ? value : '--'}</div>
      </div>`;
  }

  function toggleIdeal() {
    const content = document.getElementById('fb-ideal-content');
    const arrow = document.getElementById('ideal-arrow');
    if (!content) return;
    content.classList.toggle('open');
    if (arrow) arrow.textContent = content.classList.contains('open') ? '▲' : '▼';
  }

  async function nextQuestion() {
    state.questionIndex++;
    if (state.questionIndex >= state.questions.length) { showHome(); return; }
    const q = state.questions[state.questionIndex];
    if (q.talk_template_id && (!state.currentTemplate || state.currentTemplate.id !== q.talk_template_id)) {
      const t = await api('/templates/' + q.talk_template_id);
      state.currentTemplate = t.template;
    }
    await showQuizQuestion();
    showScreen('quiz-screen');
  }

  // ── History ────────────────────────────────────────────────────────────
  async function showHistory() {
    showScreen('history-screen');

    // Show admin nav
    const adminBtn = document.getElementById('nav-admin-history');
    if (adminBtn) adminBtn.style.display = state.user && state.user.role === 'admin' ? 'flex' : 'none';

    // Load mode stats
    const statsData = await api('/stats');
    const stats = statsData.stats || {};
    [
      { key: 'quick',        bestId: 'stat-quick-best', countId: 'stat-quick-count' },
      { key: 'reproduction', bestId: 'stat-repro-best', countId: 'stat-repro-count' },
      { key: 'simulation',   bestId: 'stat-sim-best',   countId: 'stat-sim-count'   },
    ].forEach(({ key, bestId, countId }) => {
      const s = stats[key] || {};
      const bestEl = document.getElementById(bestId);
      const countEl = document.getElementById(countId);
      if (bestEl) bestEl.textContent = s.best_score !== null && s.best_score !== undefined ? s.best_score + '点' : '--';
      if (countEl) countEl.textContent = (s.count || 0) + '回';
    });

    // Load answer history
    const data = await api('/answers');
    const list = document.getElementById('history-list');
    if (!data.answers || data.answers.length === 0) {
      list.innerHTML = '<div class="text-center text-muted" style="padding:40px;">まだ学習記録がありません</div>';
      return;
    }

    const modeMap = { quick: '⚡ クイック', reproduction: '📝 再現', simulation: '🎯 実戦' };
    list.innerHTML = data.answers.map((a, i) => {
      const date = new Date(a.created_at).toLocaleDateString('ja-JP',
        { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      const fb = a.ai_feedback || {};
      const qMode = a.question ? (modeMap[a.question.mode] || a.question.mode) : '';
      return `
        <div class="history-item" onclick="App.toggleHistory(${i})">
          <div class="history-item-header">
            <div>
              <div class="history-cat">${escHtml(a.category_name || '')} <span class="badge badge-purple">${qMode}</span></div>
              <div class="history-date">${date}</div>
            </div>
            <div class="history-score ${a.is_passed ? 'passed' : ''}">${a.score_total}点</div>
          </div>
          <div class="history-detail" id="hist-detail-${i}">
            <div style="font-size:13px;font-weight:700;margin-bottom:6px;">称号：${escHtml(a.title || '')}</div>
            ${(fb.good_points || []).map(p => `<div style="font-size:13px;color:var(--success);margin-bottom:4px;">✅ ${escHtml(p)}</div>`).join('')}
            ${(fb.improvement_points || []).map(p => `<div style="font-size:13px;color:var(--primary);margin-bottom:4px;">🔧 ${escHtml(p)}</div>`).join('')}
            ${(a.admin_comments || []).map(c => `
              <div style="background:#f0f4ff;border-radius:10px;padding:10px 12px;margin-top:8px;font-size:13px;">
                <div style="font-weight:700;color:var(--primary);margin-bottom:4px;">👑 ${escHtml(c.admin_name || '管理者')} のコメント</div>
                ${escHtml(c.comment)}
              </div>`).join('')}
          </div>
        </div>`;
    }).join('');
  }

  function toggleHistory(idx) {
    const el = document.getElementById('hist-detail-' + idx);
    if (el) el.classList.toggle('open');
  }

  // ── Admin ──────────────────────────────────────────────────────────────
  async function showAdmin() {
    showScreen('admin-screen');
    const data = await api('/admin/dashboard');
    const body = document.getElementById('admin-body');
    if (data.error) {
      body.innerHTML = '<div class="text-muted text-center" style="padding:40px;">アクセス権がありません</div>';
      return;
    }
    if (!data.members || data.members.length === 0) {
      body.innerHTML = '<div class="text-muted text-center" style="padding:40px;">メンバーがいません</div>';
      return;
    }

    const modes = ['quick', 'reproduction', 'simulation'];
    const modeLabels = { quick: 'クイック', reproduction: '再現', simulation: '実戦' };

    body.innerHTML = data.members.map(m => {
      const cs = m.category_stats || {};

      const catRows = Object.values(cs).map(cat => {
        const cells = modes.map(mode => {
          const s = (cat.modes || {})[mode] || {};
          const best = s.best_score != null ? s.best_score + '点' : '--';
          const passed = s.best_score >= 80;
          return `
            <div class="admin-cell ${passed ? 'passed' : s.count > 0 ? 'tried' : ''}">
              <div class="admin-cell-score">${best}</div>
              <div class="admin-cell-count">${s.count || 0}回</div>
            </div>`;
        }).join('');

        return `
          <div class="admin-cat-row">
            <div class="admin-cat-label">${cat.emoji} ${cat.name.replace('渋りトーク','')}</div>
            <div class="admin-cat-cells">${cells}</div>
          </div>`;
      }).join('');

      return `
        <div class="member-card" onclick="App.showMemberDetail(${m.user.id}, '${escAttr(m.user.name)}')">
          <div class="admin-member-header">
            <div class="member-name">${escHtml(m.user.name)}</div>
            <div class="admin-total-badge">合計 ${m.total_answers}回</div>
          </div>
          <div class="admin-mode-header">
            <div class="admin-cat-label-spacer"></div>
            ${modes.map(md => `<div class="admin-mode-label">${modeLabels[md]}</div>`).join('')}
          </div>
          ${catRows}
        </div>`;
    }).join('');
  }

  async function showMemberDetail(userId, userName) {
    document.getElementById('member-detail-title').textContent = escHtml(userName) + ' さん';
    showScreen('member-detail-screen');

    const data = await api('/admin/members/' + userId);
    const body = document.getElementById('member-detail-body');
    if (!data.answers || data.answers.length === 0) {
      body.innerHTML = '<div class="text-muted text-center" style="padding:40px;">学習記録がありません</div>';
      return;
    }

    const modeMap = { quick: '⚡ クイック', reproduction: '📝 再現', simulation: '🎯 実戦' };
    body.innerHTML = data.answers.map(a => {
      const date = new Date(a.created_at).toLocaleDateString('ja-JP',
        { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      const fb = a.ai_feedback || {};
      const qMode = a.question ? (modeMap[a.question.mode] || '') : '';
      return `
        <div class="history-item">
          <div class="history-item-header">
            <div>
              <div class="history-cat">${escHtml(a.category_name || '')} <span class="badge badge-purple">${qMode}</span></div>
              <div class="history-date">${date}</div>
            </div>
            <div class="history-score ${a.is_passed ? 'passed' : ''}">${a.score_total}点</div>
          </div>
          <div style="margin-top:10px;">
            ${a.answer_text && a.answer_text !== '(模範トーク確認)' ? `
              <div style="font-size:12px;color:var(--text-light);margin-bottom:4px;">回答：</div>
              <div style="font-size:13px;background:#f8f7ff;border-radius:10px;padding:10px;margin-bottom:8px;max-height:100px;overflow:auto;">${escHtml(a.answer_text)}</div>` : ''}
            ${(fb.good_points || []).map(p => `<div style="font-size:13px;color:var(--success);margin-bottom:4px;">✅ ${escHtml(p)}</div>`).join('')}
            ${(fb.improvement_points || []).map(p => `<div style="font-size:13px;color:var(--primary);margin-bottom:4px;">🔧 ${escHtml(p)}</div>`).join('')}
            <div style="margin-top:10px;">
              <textarea id="comment-${a.id}" class="answer-textarea" style="min-height:60px;font-size:13px;"
                placeholder="上司コメントを入力..."></textarea>
              <button class="btn-primary btn-sm" style="margin-top:6px;" onclick="App.addComment(${a.id})">💬 コメント送信</button>
            </div>
            <div id="comment-list-${a.id}">
              ${(a.admin_comments || []).map(c => `
                <div style="background:#f0f4ff;border-radius:10px;padding:10px 12px;margin-top:8px;font-size:13px;">
                  <div style="font-weight:700;color:var(--primary);margin-bottom:4px;">👑 ${escHtml(c.admin_name || '管理者')}</div>
                  ${escHtml(c.comment)}
                </div>`).join('')}
            </div>
          </div>
        </div>`;
    }).join('');
  }

  async function addComment(answerId) {
    const textarea = document.getElementById('comment-' + answerId);
    const text = textarea ? textarea.value.trim() : '';
    if (!text) { toast('⚠️ コメントを入力してください'); return; }
    const data = await api('/admin/comments', 'POST', { answer_id: answerId, comment: text });
    if (data.error) { toast('❌ ' + data.error); return; }
    toast('✅ コメントを送信しました');
    if (textarea) textarea.value = '';
    const list = document.getElementById('comment-list-' + answerId);
    if (list) list.innerHTML += `
      <div style="background:#f0f4ff;border-radius:10px;padding:10px 12px;margin-top:8px;font-size:13px;">
        <div style="font-weight:700;color:var(--primary);margin-bottom:4px;">👑 ${escHtml(data.comment.admin_name || '管理者')}</div>
        ${escHtml(data.comment.comment)}
      </div>`;
  }

  // ── Init ───────────────────────────────────────────────────────────────
  async function init() {
    const data = await api('/me');
    if (data.user) {
      state.user = data.user;
      await loadHome();
    } else {
      showScreen('cover-screen');
    }
  }

  init();

  return {
    login, logout, showHome, showHistory, showAdmin,
    selectCategory, startMode,
    submitAnswer, submitFree, toggleHint, toggleIdeal,
    selectReorderChip, removeReorderItem, resetReorder,
    nextQuestion, toggleHistory,
    showMemberDetail, addComment,
  };
})();
