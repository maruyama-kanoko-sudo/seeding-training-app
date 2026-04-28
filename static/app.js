// ============================================================
// State
// ============================================================
const state = {
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  page: 'home',
  params: {},
  currentQuestion: null,
  lastResult: null,
};

// ============================================================
// API
// ============================================================
async function api(method, path, body) {
  const opts = { method, headers: { 'Content-Type': 'application/json' } };
  if (state.token) opts.headers['Authorization'] = `Bearer ${state.token}`;
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch('/api' + path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || 'エラーが発生しました');
  return data;
}

// ============================================================
// Navigation
// ============================================================
function go(page, params = {}) {
  state.page = page;
  state.params = params;
  render();
  window.scrollTo(0, 0);
}

// ============================================================
// Toast
// ============================================================
function toast(msg, type = 'info') {
  let c = document.querySelector('.toast-container');
  if (!c) { c = document.createElement('div'); c.className = 'toast-container'; document.body.appendChild(c); }
  const el = document.createElement('div');
  el.className = 'toast-msg';
  el.style.background = type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#1e293b';
  el.textContent = msg;
  c.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ============================================================
// Loading
// ============================================================
let loadingEl = null;
function showLoading(msg = 'AI採点中...') {
  loadingEl = document.createElement('div');
  loadingEl.className = 'loading-overlay';
  loadingEl.innerHTML = `<div class="spinner-border text-light" role="status"></div><div class="loading-text">${msg}</div>`;
  document.body.appendChild(loadingEl);
}
function hideLoading() { loadingEl && loadingEl.remove(); loadingEl = null; }

// ============================================================
// Auth
// ============================================================
async function login(email, password) {
  const data = await api('POST', '/auth/login', { email, password });
  state.token = data.access_token;
  state.user = data.user;
  localStorage.setItem('token', state.token);
  localStorage.setItem('user', JSON.stringify(state.user));
  go('home');
}

function logout() {
  state.token = null; state.user = null;
  localStorage.removeItem('token'); localStorage.removeItem('user');
  go('login');
}

// ============================================================
// Render helpers
// ============================================================
function esc(str) {
  if (!str) return '';
  return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

function difficultyBadge(d) {
  const map = { easy: ['easy','かんたん'], normal: ['normal','ふつう'], hard: ['hard','むずかしい'] };
  const [cls, label] = map[d] || map.normal;
  return `<span class="difficulty-badge difficulty-${cls}">${label}</span>`;
}

function passedBadge(passed, ng) {
  if (ng) return `<span class="badge-ng">⚠ NG</span>`;
  if (passed) return `<span class="badge-passed">✓ 合格</span>`;
  return `<span class="badge-failed">✗ 不合格</span>`;
}

function sidebar() {
  const u = state.user;
  const isAdmin = u && u.role === 'admin';
  const navItem = (icon, label, page, params) => {
    const active = state.page === page ? ' active' : '';
    return `<button class="sidebar-nav-item${active}" onclick="go('${page}', ${JSON.stringify(params || {})})">
      <i class="bi bi-${icon}"></i>${label}</button>`;
  };

  let adminNav = '';
  if (isAdmin) {
    adminNav = `
      <div class="nav-label mt-2">管理者</div>
      ${navItem('speedometer2', 'ダッシュボード', 'admin-dashboard')}
      ${navItem('people', 'ユーザー管理', 'admin-users')}
      ${navItem('bar-chart-line', 'チーム別ランキング', 'admin-rankings')}
      ${navItem('journal-text', 'コンテンツ管理', 'admin-content')}
      ${navItem('chat-left-text', 'フィードバック確認', 'admin-feedback')}
    `;
  }

  return `<div class="sidebar" id="sidebar">
    <div class="sidebar-brand">
      <div class="sidebar-brand-name">⚔️ シーディング<br>冒険録</div>
      <div class="sidebar-brand-sub">営業スキル習得トレーニング</div>
    </div>
    <div class="sidebar-user">
      <div class="sidebar-user-name">${esc(u?.name || '')}</div>
      <div class="sidebar-user-role">${isAdmin ? '管理者' : '一般ユーザー'}${u?.team_name ? ' · ' + esc(u.team_name) : ''}</div>
    </div>
    <nav class="sidebar-nav">
      <div class="nav-label">メニュー</div>
      ${navItem('house', 'ホーム', 'home')}
      ${navItem('play-circle', 'トレーニング', 'training')}
      ${navItem('clock-history', '回答履歴', 'history')}
      ${adminNav}
    </nav>
    <div class="sidebar-footer">
      <button class="sidebar-nav-item" onclick="logout()"><i class="bi bi-box-arrow-left"></i>ログアウト</button>
    </div>
  </div>`;
}

// ============================================================
// Pages
// ============================================================

// ----- Login -----
function pageLogin() {
  return `<div class="login-page">
    <div class="login-card">
      <div class="login-logo">⚔️</div>
      <div class="fw-bold fs-4 mb-1" style="color:var(--gold)">シーディング冒険録</div>
      <div class="login-subtitle">営業スキル習得トレーニング</div>
      <div id="login-error" class="alert alert-danger d-none mb-3" role="alert"></div>
      <div class="mb-3">
        <label class="form-label fw-semibold">メールアドレス</label>
        <input type="email" id="login-email" class="form-control" placeholder="example@email.com" value="">
      </div>
      <div class="mb-4">
        <label class="form-label fw-semibold">パスワード</label>
        <input type="password" id="login-password" class="form-control" placeholder="パスワード">
      </div>
      <button class="btn-primary-custom w-100" id="login-btn" onclick="handleLogin()">ログイン</button>
      <div class="text-center mt-4 text-muted" style="font-size:0.78rem">
        管理者: admin@example.com / admin123<br>
        テスト: tanaka@example.com / test123
      </div>
    </div>
  </div>`;
}

async function handleLogin() {
  const email = document.getElementById('login-email').value.trim();
  const password = document.getElementById('login-password').value;
  const errEl = document.getElementById('login-error');
  errEl.classList.add('d-none');
  try {
    await login(email, password);
  } catch (e) {
    errEl.textContent = e.message;
    errEl.classList.remove('d-none');
  }
}

// ----- Home -----
async function pageHome() {
  try {
    const cats = await api('GET', '/categories');
    state.categories = cats;
    const icons = { '金額渋り': '💰', '相談渋り': '🤝', '他社比較渋り': '🔍', '時間渋り': '⏰' };

    const modeConfig = {
      '穴埋めシーディング': { icon: '📝', color: 'rgba(108,92,231,0.75)', border: 'rgba(162,155,254,0.5)' },
      '記述式シーディング': { icon: '✏️', color: 'rgba(0,184,148,0.7)',   border: 'rgba(0,206,201,0.5)' },
      '音声入力シーディング': { icon: '🎤', color: 'rgba(253,127,90,0.75)', border: 'rgba(253,203,110,0.5)' },
    };

    const modeCls = {
      '穴埋めシーディング': 'fill-mode',
      '記述式シーディング': 'free-mode',
      '音声入力シーディング': 'voice-mode',
    };

    const cards = cats.map(c => {
      const m = modeConfig[c.name] || { icon: '📋' };
      const cls = modeCls[c.name] || 'free-mode';
      return `<button class="mode-card ${cls}" onclick="startTraining(${c.id}, '${esc(c.name)}')">
        <span class="mc-icon">${m.icon}</span>
        <div class="mc-name">${esc(c.name)}</div>
        <div class="mc-desc">${esc((c.description || '').slice(0, 50))}...</div>
        <div class="mc-count">📚 ${c.question_count}問</div>
      </button>`;
    }).join('');

    return `<div class="home-fullscreen">
      <div class="home-overlay"></div>
      <div class="home-content">
        <div style="font-weight:800;font-size:1rem;color:var(--text);margin-bottom:14px;">🎮 トレーニングモードを選ぼう</div>
        <div class="mode-cards-glass">${cards}</div>
        <div style="margin-top:18px;text-align:center;">
          <button class="btn btn-sm btn-outline-secondary" onclick="go('history')">
            <i class="bi bi-clock-history me-1"></i>回答履歴を見る
          </button>
        </div>
      </div>
    </div>`;
  } catch (e) {
    return `<div class="alert alert-danger">${esc(e.message)}</div>`;
  }
}

// ----- Training: Select (= same as home mode cards) -----
async function pageTrainingSelect() {
  return pageHome();
}

async function startTraining(categoryId, categoryName) {
  showLoading('問題を読み込み中...');
  try {
    const q = await api('GET', `/questions/${categoryId}/random`);
    state.currentQuestion = q;
    state.trainingMode = 'free';
    go('training-question', { categoryId, categoryName });
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    hideLoading();
  }
}

function setTrainingMode(mode) {
  state.trainingMode = mode;
  render();
  setTimeout(() => {
    if (mode === 'voice') initVoiceInput();
  }, 100);
}

// Fill-in-the-blank helpers
function renderFillBlank(template) {
  const parts = template.split('[＿＿＿＿]');
  let html = '<div class="fill-blank-area" id="fill-blank-area">';
  parts.forEach((part, i) => {
    html += `<span>${esc(part).replace(/\n/g, '<br>')}</span>`;
    if (i < parts.length - 1) {
      html += `<input type="text" class="fill-blank" id="fill-blank-${i}" placeholder="　　　　" autocomplete="off">`;
    }
  });
  html += '</div>';
  return html;
}

function getFillBlankAnswer() {
  const area = document.getElementById('fill-blank-area');
  if (!area) return '';
  const template = state.currentQuestion.fill_template;
  const parts = template.split('[＿＿＿＿]');
  return parts.map((part, i) => {
    const input = document.getElementById(`fill-blank-${i}`);
    return part + (input ? input.value : '');
  }).join('');
}

// Voice input helpers
function renderVoiceInput() {
  return `<div class="text-center mb-3">
    <button class="mic-btn" id="mic-btn" onclick="toggleVoice()">
      <i class="bi bi-mic-fill" style="font-size:2rem"></i>
    </button>
    <div id="voice-status" class="mt-2" style="font-size:0.85rem;color:var(--gold-light)">マイクボタンを押して話す</div>
  </div>
  <textarea id="answer-input" class="answer-textarea" placeholder="音声認識結果がここに表示されます。手入力での修正も可能です。"></textarea>`;
}

let _recognition = null;
function initVoiceInput() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) {
    const statusEl = document.getElementById('voice-status');
    if (statusEl) statusEl.textContent = '⚠ このブラウザは音声入力に対応していません（Chrome推奨）';
    return;
  }
  _recognition = new SpeechRec();
  _recognition.lang = 'ja-JP';
  _recognition.continuous = true;
  _recognition.interimResults = true;

  _recognition.onresult = (e) => {
    let final = '';
    let interim = '';
    for (let i = 0; i < e.results.length; i++) {
      if (e.results[i].isFinal) final += e.results[i][0].transcript;
      else interim += e.results[i][0].transcript;
    }
    const ta = document.getElementById('answer-input');
    if (ta) ta.value = final + interim;
  };

  _recognition.onerror = (e) => {
    const statusEl = document.getElementById('voice-status');
    if (statusEl) statusEl.textContent = '⚠ 音声認識エラー: ' + e.error;
    const btn = document.getElementById('mic-btn');
    if (btn) btn.classList.remove('recording');
  };

  _recognition.onend = () => {
    const btn = document.getElementById('mic-btn');
    if (btn) btn.classList.remove('recording');
    const statusEl = document.getElementById('voice-status');
    if (statusEl) statusEl.textContent = 'マイクボタンを押して話す';
  };
}

function toggleVoice() {
  const btn = document.getElementById('mic-btn');
  const statusEl = document.getElementById('voice-status');
  if (!_recognition) { initVoiceInput(); if (!_recognition) return; }
  if (btn.classList.contains('recording')) {
    _recognition.stop();
    btn.classList.remove('recording');
    if (statusEl) statusEl.textContent = '認識停止。修正して採点ボタンを押してください。';
  } else {
    _recognition.start();
    btn.classList.add('recording');
    if (statusEl) statusEl.textContent = '● 録音中... もう一度押すと停止';
  }
}

// ----- Training: Question -----
function pageTrainingQuestion() {
  const q = state.currentQuestion;
  if (!q) { go('training'); return ''; }
  const mode = state.trainingMode || 'free';
  const hasFill = !!q.fill_template;

  const modeLabel = { fill: '📝 穴埋めシーディング', free: '✏️ 記述式シーディング', voice: '🎤 音声入力シーディング' };
  const modeIndicator = `<div class="mode-indicator ${mode}-mode mb-3">${modeLabel[mode] || modeLabel.free}</div>`;

  let inputArea;
  let inputHint;
  if (mode === 'fill' && hasFill) {
    inputArea = renderFillBlank(q.fill_template);
    inputHint = '空欄を埋めて採点ボタンを押してください 📝';
  } else if (mode === 'fill' && !hasFill) {
    // fill選択したが fill_template がない場合は記述式で代替
    inputArea = `<textarea id="answer-input" class="answer-textarea" placeholder="ここに営業トークを入力してください..."></textarea>`;
    inputHint = '※この問題には穴埋めテンプレートがありません。自由記述でどうぞ ✏️';
  } else if (mode === 'voice') {
    inputArea = renderVoiceInput();
    inputHint = 'マイクボタンを押して話してください 🎤（Chrome推奨）';
  } else {
    inputArea = `<textarea id="answer-input" class="answer-textarea" placeholder="ここに営業トークを入力してください..."></textarea>`;
    inputHint = 'シーディングトーク・渋り攻略トークを自由に入力してください ✏️';
  }

  return `<div class="page-header">
      <div class="d-flex align-items-center gap-2 mb-2">
        <button class="btn btn-sm btn-outline-secondary" onclick="go('home')">← ホームへ</button>
      </div>
      <h1 class="page-title">トレーニング</h1>
    </div>
    <div class="card p-4 mb-4">
      <div class="d-flex align-items-center gap-2 mb-3">
        <span class="category-badge"><i class="bi bi-tag"></i>${esc(q.category_name)}</span>
        ${difficultyBadge(q.difficulty)}
      </div>
      <div class="mb-2" style="font-size:0.8rem;font-weight:700;color:var(--text-muted)">👤 お客様の発言</div>
      <div class="question-bubble">${esc(q.customer_text)}</div>
    </div>
    <div class="card p-4">
      ${modeIndicator}
      <div class="mb-2 fw-bold" style="font-size:0.88rem;">あなたの回答</div>
      <div class="mb-3" style="font-size:0.8rem;color:var(--text-muted)">${inputHint}</div>
      ${inputArea}
      <div class="d-flex gap-3 mt-3 align-items-center flex-wrap">
        <button class="btn-primary-custom" id="submit-btn" onclick="handleSubmitAnswer()">
          <i class="bi bi-send me-1"></i>採点する
        </button>
        <button class="btn btn-outline-secondary btn-sm" onclick="startTraining(${q.category_id}, '${esc(q.category_name)}')">
          <i class="bi bi-arrow-clockwise me-1"></i>別の問題
        </button>
        <div id="submit-error" style="font-size:0.85rem;color:var(--coral)"></div>
      </div>
    </div>`;
}

async function handleSubmitAnswer() {
  const mode = state.trainingMode || 'free';
  let text = '';
  if (mode === 'fill') {
    text = getFillBlankAnswer().trim();
  } else {
    text = (document.getElementById('answer-input')?.value || '').trim();
  }
  const errEl = document.getElementById('submit-error');
  if (!text) { errEl.textContent = '回答を入力してください'; return; }
  errEl.textContent = '';
  if (_recognition) { try { _recognition.stop(); } catch(e) {} }
  showLoading('AI採点中... しばらくお待ちください');
  try {
    const result = await api('POST', '/answers', { question_id: state.currentQuestion.id, answer_text: text });
    state.lastResult = result;
    go('result');
  } catch (e) {
    toast(e.message, 'error');
  } finally {
    hideLoading();
  }
}

// ----- Result -----
function pageResult() {
  const r = state.lastResult;
  if (!r) { go('home'); return ''; }

  const circleClass = r.compliance_ng ? 'ng' : (r.passed ? 'passed' : 'failed');
  const detailLabels = {
    empathy: '共感・承認',
    essence: '本質の言語化',
    third_party_story: '第三者トーク',
    future_presentation: '未来提示・行動正当化',
    closing: 'クロージング設計',
  };

  const bars = Object.entries(r.details || {}).map(([key, val]) => {
    const pct = Math.round((val / 20) * 100);
    const color = val >= 16 ? '#10b981' : val >= 12 ? '#6366f1' : val >= 8 ? '#f59e0b' : '#ef4444';
    return `<div class="score-bar-row">
      <div class="score-bar-label"><span>${esc(detailLabels[key] || key)}</span><span>${val}/20点</span></div>
      <div class="score-bar-track"><div class="score-bar-fill" style="width:${pct}%;background:${color}"></div></div>
    </div>`;
  }).join('');

  const ngSection = r.compliance_ng ? `
    <div class="ng-alert mb-3">
      <div class="fw-bold mb-1"><i class="bi bi-exclamation-triangle me-1"></i>コンプライアンスNG</div>
      <ul class="mb-0 ps-3">${(r.compliance_reasons || []).map(x => `<li>${esc(x)}</li>`).join('')}</ul>
    </div>` : '';

  const feedbackSection = `
    <div class="mb-3">
      <div class="fw-semibold mb-2 text-success"><i class="bi bi-hand-thumbs-up me-1"></i>良かった点</div>
      <div class="feedback-box">${esc(r.good_points || '').replace(/\n/g, '<br>')}</div>
    </div>
    <div class="mb-3">
      <div class="fw-semibold mb-2 text-warning"><i class="bi bi-lightbulb me-1"></i>改善点</div>
      <div class="feedback-box">${esc(r.improvement_points || '').replace(/\n/g, '<br>')}</div>
    </div>
    <div class="mb-3">
      <div class="fw-semibold mb-2 text-primary"><i class="bi bi-chat-quote me-1"></i>改善トーク例</div>
      <div class="suggested-answer">${esc(r.suggested_answer || '')}</div>
    </div>`;

  const qId = state.currentQuestion?.id;

  return `<div class="page-header">
      <h1 class="page-title">採点結果</h1>
    </div>

    <div class="card p-4 mb-4">
      <div class="d-flex align-items-center gap-4 mb-4">
        <div class="score-circle ${circleClass}">
          <div class="score-num">${r.score}</div>
          <div class="score-unit">点</div>
        </div>
        <div>
          <div class="mb-1">${r.passed && !r.compliance_ng
            ? '<span class="result-badge passed">✓ 合格</span>'
            : '<span class="result-badge failed">✗ 不合格</span>'}</div>
          <div class="text-muted" style="font-size:0.85rem">カテゴリ: ${esc(r.category_name)}</div>
          <div class="text-muted" style="font-size:0.85rem">合格ライン: 80点以上・コンプラNGなし</div>
        </div>
      </div>
      ${ngSection}
      <div class="mb-1 fw-semibold">評価項目別スコア</div>
      ${bars}
    </div>

    <div class="card p-4 mb-4">
      <div class="fw-bold mb-3">AIフィードバック</div>
      ${feedbackSection}
    </div>

    <div class="card p-4 mb-4">
      <div class="fw-semibold mb-2 text-secondary" style="font-size:0.85rem">あなたの回答</div>
      <div class="feedback-box">${esc(r.answer_text).replace(/\n/g, '<br>')}</div>
    </div>

    <div class="card p-4 mb-4">
      <div class="fw-semibold mb-3">管理者へフィードバックを送る</div>
      <textarea id="fb-input" class="answer-textarea" style="min-height:80px" placeholder="問題や採点に対するご意見があればこちらへ..."></textarea>
      <button class="btn btn-outline-secondary btn-sm mt-2" onclick="sendFeedback(${qId})">送信</button>
    </div>

    <div class="d-flex gap-3 flex-wrap">
      <button class="btn-primary-custom" onclick="startTraining(${state.currentQuestion?.category_id}, '${esc(state.currentQuestion?.category_name)}')">
        <i class="bi bi-arrow-clockwise me-1"></i>もう一度練習する
      </button>
      <button class="btn btn-outline-secondary" onclick="go('history')">
        <i class="bi bi-clock-history me-1"></i>履歴を見る
      </button>
      <button class="btn btn-outline-secondary" onclick="go('home')">
        <i class="bi bi-house me-1"></i>ホームへ
      </button>
    </div>`;
}

async function sendFeedback(questionId) {
  const msg = (document.getElementById('fb-input')?.value || '').trim();
  if (!msg) { toast('フィードバックを入力してください'); return; }
  try {
    await api('POST', '/feedback', { question_id: questionId, message: msg });
    toast('フィードバックを送信しました', 'success');
    document.getElementById('fb-input').value = '';
  } catch (e) {
    toast(e.message, 'error');
  }
}

// ----- History -----
async function pageHistory() {
  try {
    const history = await api('GET', '/answers/history');
    if (!history.length) return `<div class="page-header"><h1 class="page-title">回答履歴</h1></div>
      <div class="empty-state"><i class="bi bi-clock-history"></i><div>まだ回答がありません。<br>トレーニングを始めましょう！</div></div>`;

    const items = history.map(h => `
      <div class="history-item" onclick="showHistoryDetail(${h.id})">
        <div class="d-flex justify-content-between align-items-center mb-1">
          <span class="category-badge" style="margin-bottom:0">${esc(h.category_name)}</span>
          <div class="d-flex align-items-center gap-2">
            ${passedBadge(h.passed, h.compliance_ng)}
            <span class="fw-bold" style="color:${h.score >= 80 ? '#10b981' : '#ef4444'}">${h.score}点</span>
          </div>
        </div>
        <div class="customer-text">${esc(h.customer_text)}</div>
        <div class="text-muted mt-1" style="font-size:0.75rem">${new Date(h.created_at).toLocaleString('ja-JP')}</div>
      </div>`).join('');

    return `<div class="page-header">
      <h1 class="page-title">回答履歴</h1>
      <p class="page-subtitle">過去の回答とAIフィードバックを確認できます</p>
    </div>
    <div id="history-list">${items}</div>
    <div id="history-detail"></div>`;
  } catch (e) {
    return `<div class="alert alert-danger">${esc(e.message)}</div>`;
  }
}

async function showHistoryDetail(answerId) {
  const history = await api('GET', '/answers/history');
  const h = history.find(x => x.id === answerId);
  if (!h) return;

  const detailLabels = { empathy: '共感・承認', essence: '本質の言語化', third_party_story: '第三者トーク', future_presentation: '未来提示・行動正当化', closing: 'クロージング設計' };
  const bars = Object.entries(h.details || {}).map(([key, val]) => {
    const pct = Math.round((val / 20) * 100);
    const color = val >= 16 ? '#10b981' : val >= 12 ? '#6366f1' : val >= 8 ? '#f59e0b' : '#ef4444';
    return `<div class="score-bar-row">
      <div class="score-bar-label"><span>${esc(detailLabels[key] || key)}</span><span>${val}/20点</span></div>
      <div class="score-bar-track"><div class="score-bar-fill" style="width:${pct}%;background:${color}"></div></div>
    </div>`;
  }).join('');

  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.innerHTML = `<div class="modal-box">
    <div class="d-flex justify-content-between align-items-start mb-3">
      <div>
        <span class="category-badge">${esc(h.category_name)}</span>
        <div class="fw-bold fs-5 mt-1">${h.score}点 ${passedBadge(h.passed, h.compliance_ng)}</div>
      </div>
      <button class="btn btn-sm btn-outline-secondary" onclick="this.closest('.modal-overlay').remove()">✕</button>
    </div>
    <div class="mb-3">
      <div class="text-muted mb-1" style="font-size:0.8rem">お客様発言</div>
      <div class="question-bubble">${esc(h.customer_text)}</div>
    </div>
    <div class="mb-3">
      <div class="text-muted mb-1" style="font-size:0.8rem">あなたの回答</div>
      <div class="feedback-box">${esc(h.answer_text).replace(/\n/g,'<br>')}</div>
    </div>
    ${bars}
    ${h.good_points ? `<div class="fw-semibold text-success mb-1 mt-2">良かった点</div><div class="feedback-box">${esc(h.good_points).replace(/\n/g,'<br>')}</div>` : ''}
    ${h.improvement_points ? `<div class="fw-semibold text-warning mb-1 mt-2">改善点</div><div class="feedback-box">${esc(h.improvement_points).replace(/\n/g,'<br>')}</div>` : ''}
    ${h.suggested_answer ? `<div class="fw-semibold text-primary mb-1 mt-2">改善トーク例</div><div class="suggested-answer">${esc(h.suggested_answer)}</div>` : ''}
  </div>`;
  document.body.appendChild(modal);
  modal.addEventListener('click', e => { if (e.target === modal) modal.remove(); });
}

// ----- Admin Dashboard -----
async function pageAdminDashboard() {
  try {
    const d = await api('GET', '/admin/dashboard');
    const recent = (d.recent_answers || []).map(a => `<tr>
      <td>${esc(a.user_name)}</td>
      <td>${esc(a.category_name)}</td>
      <td class="fw-bold" style="color:${a.score >= 80 ? '#10b981' : '#ef4444'}">${a.score}点</td>
      <td>${passedBadge(a.passed, a.compliance_ng)}</td>
      <td class="text-muted" style="font-size:0.8rem">${new Date(a.created_at).toLocaleString('ja-JP')}</td>
    </tr>`).join('');

    return `<div class="page-header"><h1 class="page-title">ダッシュボード</h1></div>
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-value text-primary">${d.total_answers}</div><div class="stat-label">総回答数</div></div></div>
      <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-value text-success">${d.avg_score}</div><div class="stat-label">平均スコア</div></div></div>
      <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-value text-info">${d.pass_rate}%</div><div class="stat-label">合格率</div></div></div>
      <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-value text-warning">${d.ng_count}</div><div class="stat-label">コンプラNG件数</div></div></div>
    </div>
    <div class="card">
      <div class="p-3 fw-bold border-bottom">最近の回答</div>
      <div class="table-responsive">
        <table class="data-table"><thead><tr><th>ユーザー</th><th>カテゴリ</th><th>スコア</th><th>結果</th><th>日時</th></tr></thead>
        <tbody>${recent || '<tr><td colspan="5" class="text-center text-muted py-3">回答がありません</td></tr>'}</tbody></table>
      </div>
    </div>`;
  } catch (e) {
    return `<div class="alert alert-danger">${esc(e.message)}</div>`;
  }
}

// ----- Admin Users -----
async function pageAdminUsers() {
  try {
    const users = await api('GET', '/admin/users');
    const rows = users.map(u => `<tr class="clickable" onclick="go('admin-user-detail', {userId: ${u.id}})">
      <td>${esc(u.name)}</td>
      <td class="text-muted">${esc(u.email)}</td>
      <td>${esc(u.team_name)}</td>
      <td>${u.total_answers}</td>
      <td class="fw-bold" style="color:${u.avg_score >= 80 ? '#10b981' : '#6366f1'}">${u.avg_score || 0}点</td>
      <td><span class="text-success">${u.passed_count}合格</span> / <span class="text-danger">${u.failed_count}不合格</span></td>
    </tr>`).join('');

    return `<div class="page-header">
      <div class="d-flex justify-content-between align-items-center">
        <div><h1 class="page-title">ユーザー管理</h1><p class="page-subtitle">ユーザーをクリックで詳細確認</p></div>
        <button class="btn btn-primary btn-sm" onclick="showAddUserModal()"><i class="bi bi-person-plus me-1"></i>ユーザー追加</button>
      </div>
    </div>
    <div class="card">
      <div class="table-responsive">
        <table class="data-table"><thead><tr><th>名前</th><th>メール</th><th>チーム</th><th>回答数</th><th>平均スコア</th><th>合格/不合格</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="6" class="text-center text-muted py-3">ユーザーがいません</td></tr>'}</tbody></table>
      </div>
    </div>`;
  } catch (e) {
    return `<div class="alert alert-danger">${esc(e.message)}</div>`;
  }
}

async function pageAdminUserDetail() {
  const { userId } = state.params;
  try {
    const u = await api('GET', `/admin/users/${userId}`);
    const rows = u.answers.map(a => `<tr>
      <td>${esc(a.category_name)}</td>
      <td class="text-muted" style="font-size:0.8rem;max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(a.customer_text)}</td>
      <td class="fw-bold" style="color:${a.score >= 80 ? '#10b981' : '#ef4444'}">${a.score}点</td>
      <td>${passedBadge(a.passed, a.compliance_ng)}</td>
      <td class="text-muted" style="font-size:0.8rem">${new Date(a.created_at).toLocaleString('ja-JP')}</td>
    </tr>`).join('');

    return `<div class="page-header">
      <button class="btn btn-sm btn-outline-secondary mb-2" onclick="go('admin-users')">← 一覧へ</button>
      <h1 class="page-title">${esc(u.name)}</h1>
      <p class="page-subtitle">${esc(u.email)} · ${esc(u.team_name)}</p>
    </div>
    <div class="row g-3 mb-4">
      <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-value text-primary">${u.total_answers}</div><div class="stat-label">総回答数</div></div></div>
      <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-value" style="color:${u.avg_score >= 80 ? '#10b981' : '#6366f1'}">${u.avg_score}</div><div class="stat-label">平均スコア</div></div></div>
      <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-value text-success">${u.passed_count}</div><div class="stat-label">合格数</div></div></div>
      <div class="col-6 col-md-3"><div class="stat-card"><div class="stat-value text-danger">${u.failed_count}</div><div class="stat-label">不合格数</div></div></div>
    </div>
    <div class="card">
      <div class="p-3 fw-bold border-bottom">回答履歴</div>
      <div class="table-responsive">
        <table class="data-table"><thead><tr><th>カテゴリ</th><th>お客様発言</th><th>スコア</th><th>結果</th><th>日時</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="5" class="text-center text-muted py-3">回答がありません</td></tr>'}</tbody></table>
      </div>
    </div>`;
  } catch (e) {
    return `<div class="alert alert-danger">${esc(e.message)}</div>`;
  }
}

// ----- Admin Rankings -----
async function pageAdminRankings() {
  try {
    const rankings = await api('GET', '/admin/rankings');
    const rows = rankings.map(r => `<tr>
      <td class="fw-bold text-center" style="font-size:1.2rem">${r.rank === 1 ? '🥇' : r.rank === 2 ? '🥈' : r.rank === 3 ? '🥉' : r.rank}</td>
      <td class="fw-semibold">${esc(r.team_name)}</td>
      <td>${r.member_count}人</td>
      <td>${r.total_answers}</td>
      <td class="fw-bold" style="color:${r.avg_score >= 80 ? '#10b981' : '#6366f1'}">${r.avg_score}点</td>
      <td>${r.pass_rate}%</td>
    </tr>`).join('');

    return `<div class="page-header"><h1 class="page-title">チーム別ランキング</h1></div>
    <div class="card">
      <div class="table-responsive">
        <table class="data-table"><thead><tr><th>順位</th><th>チーム名</th><th>人数</th><th>回答数</th><th>平均スコア</th><th>合格率</th></tr></thead>
        <tbody>${rows || '<tr><td colspan="6" class="text-center text-muted py-3">データがありません</td></tr>'}</tbody></table>
      </div>
    </div>`;
  } catch (e) {
    return `<div class="alert alert-danger">${esc(e.message)}</div>`;
  }
}

// ----- Admin Feedback -----
async function pageAdminFeedback() {
  try {
    const feedbacks = await api('GET', '/admin/feedback');
    if (!feedbacks.length) return `<div class="page-header"><h1 class="page-title">フィードバック確認</h1></div>
      <div class="empty-state"><i class="bi bi-chat-left-text"></i><div>フィードバックがありません</div></div>`;

    const items = feedbacks.map(f => `
      <div class="card p-3 mb-3">
        <div class="d-flex justify-content-between mb-1">
          <div class="fw-semibold">${esc(f.user_name)} <span class="text-muted fw-normal">· ${esc(f.category_name)}</span></div>
          <div class="text-muted" style="font-size:0.75rem">${new Date(f.created_at).toLocaleString('ja-JP')}</div>
        </div>
        <div class="text-muted mb-2" style="font-size:0.8rem">${esc(f.customer_text).slice(0, 80)}...</div>
        <div class="feedback-box">${esc(f.message).replace(/\n/g,'<br>')}</div>
      </div>`).join('');

    return `<div class="page-header"><h1 class="page-title">フィードバック確認</h1><p class="page-subtitle">受講者からのフィードバック一覧</p></div>${items}`;
  } catch (e) {
    return `<div class="alert alert-danger">${esc(e.message)}</div>`;
  }
}

// ----- Admin Content -----
async function pageAdminContent() {
  try {
    const [cats, questions, cases] = await Promise.all([
      api('GET', '/admin/categories'),
      api('GET', '/admin/questions'),
      api('GET', '/admin/cases'),
    ]);

    const qRows = questions.map(q => `<tr>
      <td>${esc(q.category_name)}</td>
      <td style="max-width:240px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(q.customer_text)}</td>
      <td>${difficultyBadge(q.difficulty)}</td>
      <td><span class="badge ${q.is_active ? 'bg-success' : 'bg-secondary'}">${q.is_active ? '表示中' : '非表示'}</span></td>
      <td>
        <button class="btn btn-xs btn-outline-secondary me-1" onclick="toggleQuestion(${q.id}, ${!q.is_active})">${q.is_active ? '非表示' : '表示'}</button>
      </td>
    </tr>`).join('');

    const caseRows = cases.map(c => `<tr>
      <td>${esc(c.category_name)}</td>
      <td class="fw-semibold">${esc(c.person_name)}</td>
      <td style="max-width:240px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">${esc(c.story_text)}</td>
      <td><span class="badge ${c.allowed ? 'bg-success' : 'bg-secondary'}">${c.allowed ? '使用可' : '使用不可'}</span></td>
      <td>
        <button class="btn btn-xs btn-outline-secondary" onclick="toggleCase(${c.id}, ${!c.allowed})">${c.allowed ? '使用停止' : '使用許可'}</button>
      </td>
    </tr>`).join('');

    const catOptions = cats.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('');

    return `<div class="page-header"><h1 class="page-title">コンテンツ管理</h1></div>

    <div class="card mb-4">
      <div class="p-3 fw-bold border-bottom d-flex justify-content-between">
        <span>問題一覧</span>
        <button class="btn btn-primary btn-sm" onclick="showAddQuestionModal(${JSON.stringify(cats).replace(/"/g,"'")})">+ 問題追加</button>
      </div>
      <div class="table-responsive">
        <table class="data-table"><thead><tr><th>カテゴリ</th><th>お客様発言</th><th>難易度</th><th>状態</th><th>操作</th></tr></thead>
        <tbody>${qRows}</tbody></table>
      </div>
    </div>

    <div class="card mb-4">
      <div class="p-3 fw-bold border-bottom d-flex justify-content-between">
        <span>第三者トーク事例</span>
        <button class="btn btn-primary btn-sm" onclick="showAddCaseModal(${JSON.stringify(cats).replace(/"/g,"'")})">+ 事例追加</button>
      </div>
      <div class="table-responsive">
        <table class="data-table"><thead><tr><th>カテゴリ</th><th>人物名</th><th>トーク内容</th><th>状態</th><th>操作</th></tr></thead>
        <tbody>${caseRows}</tbody></table>
      </div>
    </div>

    <div class="card">
      <div class="p-3 fw-bold border-bottom d-flex justify-content-between">
        <span>カテゴリ一覧</span>
        <button class="btn btn-primary btn-sm" onclick="showAddCategoryModal()">+ カテゴリ追加</button>
      </div>
      <div class="table-responsive">
        <table class="data-table"><thead><tr><th>カテゴリ名</th><th>説明</th></tr></thead>
        <tbody>${cats.map(c => `<tr><td class="fw-semibold">${esc(c.name)}</td><td class="text-muted">${esc(c.description || '')}</td></tr>`).join('')}</tbody>
      </div>
    </div>`;
  } catch (e) {
    return `<div class="alert alert-danger">${esc(e.message)}</div>`;
  }
}

async function toggleQuestion(id, active) {
  try {
    await api('PUT', `/admin/questions/${id}`, { is_active: active });
    toast(active ? '問題を表示しました' : '問題を非表示にしました', 'success');
    render();
  } catch (e) { toast(e.message, 'error'); }
}

async function toggleCase(id, allowed) {
  try {
    await api('PUT', `/admin/cases/${id}`, { allowed });
    toast(allowed ? '事例を使用許可にしました' : '事例を使用停止にしました', 'success');
    render();
  } catch (e) { toast(e.message, 'error'); }
}

// ----- Modals -----
function showModal(html) {
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.innerHTML = `<div class="modal-box">${html}</div>`;
  document.body.appendChild(overlay);
  overlay.addEventListener('click', e => { if (e.target === overlay) overlay.remove(); });
  return overlay;
}

function showAddUserModal() {
  showModal(`
    <div class="fw-bold fs-5 mb-3">ユーザー追加</div>
    <div class="mb-2"><label class="form-label">名前</label><input id="m-name" class="form-control" placeholder="山田 太郎"></div>
    <div class="mb-2"><label class="form-label">メール</label><input id="m-email" class="form-control" type="email" placeholder="yamada@example.com"></div>
    <div class="mb-2"><label class="form-label">パスワード</label><input id="m-pass" class="form-control" type="password" placeholder="パスワード"></div>
    <div class="mb-3"><label class="form-label">権限</label>
      <select id="m-role" class="form-select"><option value="user">一般ユーザー</option><option value="admin">管理者</option></select>
    </div>
    <div id="m-err" class="text-danger mb-2"></div>
    <div class="d-flex gap-2">
      <button class="btn btn-primary" onclick="submitAddUser()">追加</button>
      <button class="btn btn-outline-secondary" onclick="this.closest('.modal-overlay').remove()">キャンセル</button>
    </div>`);
}

async function submitAddUser() {
  const name = document.getElementById('m-name').value.trim();
  const email = document.getElementById('m-email').value.trim();
  const password = document.getElementById('m-pass').value;
  const role = document.getElementById('m-role').value;
  const errEl = document.getElementById('m-err');
  if (!name || !email || !password) { errEl.textContent = '全項目を入力してください'; return; }
  try {
    await api('POST', '/admin/users', { name, email, password, role });
    document.querySelector('.modal-overlay')?.remove();
    toast('ユーザーを追加しました', 'success');
    render();
  } catch (e) { errEl.textContent = e.message; }
}

function showAddQuestionModal(cats) {
  const opts = cats.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('');
  showModal(`
    <div class="fw-bold fs-5 mb-3">問題追加</div>
    <div class="mb-2"><label class="form-label">カテゴリ</label><select id="m-cat" class="form-select">${opts}</select></div>
    <div class="mb-2"><label class="form-label">お客様発言</label><textarea id="m-text" class="form-control" rows="4" placeholder="例：受講料が高くて不安です..."></textarea></div>
    <div class="mb-2"><label class="form-label">必須要素（採点ヒント）</label><input id="m-pts" class="form-control" placeholder="例：共感→第三者トーク→クロージング"></div>
    <div class="mb-3"><label class="form-label">難易度</label>
      <select id="m-diff" class="form-select"><option value="easy">かんたん</option><option value="normal" selected>ふつう</option><option value="hard">むずかしい</option></select>
    </div>
    <div id="m-err" class="text-danger mb-2"></div>
    <div class="d-flex gap-2">
      <button class="btn btn-primary" onclick="submitAddQuestion()">追加</button>
      <button class="btn btn-outline-secondary" onclick="this.closest('.modal-overlay').remove()">キャンセル</button>
    </div>`);
}

async function submitAddQuestion() {
  const category_id = parseInt(document.getElementById('m-cat').value);
  const customer_text = document.getElementById('m-text').value.trim();
  const expected_points = document.getElementById('m-pts').value.trim();
  const difficulty = document.getElementById('m-diff').value;
  const errEl = document.getElementById('m-err');
  if (!customer_text) { errEl.textContent = 'お客様発言を入力してください'; return; }
  try {
    await api('POST', '/admin/questions', { category_id, customer_text, expected_points, difficulty });
    document.querySelector('.modal-overlay')?.remove();
    toast('問題を追加しました', 'success');
    render();
  } catch (e) { errEl.textContent = e.message; }
}

function showAddCaseModal(cats) {
  const opts = cats.map(c => `<option value="${c.id}">${esc(c.name)}</option>`).join('');
  showModal(`
    <div class="fw-bold fs-5 mb-3">第三者トーク事例追加</div>
    <div class="mb-2"><label class="form-label">カテゴリ</label><select id="m-cat" class="form-select">${opts}</select></div>
    <div class="mb-2"><label class="form-label">人物名</label><input id="m-name" class="form-control" placeholder="例：さくらさん"></div>
    <div class="mb-3"><label class="form-label">トーク内容</label><textarea id="m-story" class="form-control" rows="6" placeholder="例：前に〇〇さんという方がいて..."></textarea></div>
    <div id="m-err" class="text-danger mb-2"></div>
    <div class="d-flex gap-2">
      <button class="btn btn-primary" onclick="submitAddCase()">追加</button>
      <button class="btn btn-outline-secondary" onclick="this.closest('.modal-overlay').remove()">キャンセル</button>
    </div>`);
}

async function submitAddCase() {
  const category_id = parseInt(document.getElementById('m-cat').value);
  const person_name = document.getElementById('m-name').value.trim();
  const story_text = document.getElementById('m-story').value.trim();
  const errEl = document.getElementById('m-err');
  if (!person_name || !story_text) { errEl.textContent = '全項目を入力してください'; return; }
  try {
    await api('POST', '/admin/cases', { category_id, person_name, story_text });
    document.querySelector('.modal-overlay')?.remove();
    toast('事例を追加しました', 'success');
    render();
  } catch (e) { errEl.textContent = e.message; }
}

function showAddCategoryModal() {
  showModal(`
    <div class="fw-bold fs-5 mb-3">カテゴリ追加</div>
    <div class="mb-2"><label class="form-label">カテゴリ名</label><input id="m-name" class="form-control" placeholder="例：価格渋り"></div>
    <div class="mb-3"><label class="form-label">説明</label><textarea id="m-desc" class="form-control" rows="3" placeholder="カテゴリの説明..."></textarea></div>
    <div id="m-err" class="text-danger mb-2"></div>
    <div class="d-flex gap-2">
      <button class="btn btn-primary" onclick="submitAddCategory()">追加</button>
      <button class="btn btn-outline-secondary" onclick="this.closest('.modal-overlay').remove()">キャンセル</button>
    </div>`);
}

async function submitAddCategory() {
  const name = document.getElementById('m-name').value.trim();
  const description = document.getElementById('m-desc').value.trim();
  const errEl = document.getElementById('m-err');
  if (!name) { errEl.textContent = 'カテゴリ名を入力してください'; return; }
  try {
    await api('POST', '/admin/categories', { name, description });
    document.querySelector('.modal-overlay')?.remove();
    toast('カテゴリを追加しました', 'success');
    render();
  } catch (e) { errEl.textContent = e.message; }
}

// ============================================================
// Main Render
// ============================================================
async function render() {
  const app = document.getElementById('app');

  if (!state.token || !state.user || state.page === 'login') {
    app.innerHTML = pageLogin();
    const emailEl = document.getElementById('login-email');
    const passEl = document.getElementById('login-password');
    if (emailEl) {
      emailEl.addEventListener('keydown', e => { if (e.key === 'Enter') passEl?.focus(); });
    }
    if (passEl) {
      passEl.addEventListener('keydown', e => { if (e.key === 'Enter') handleLogin(); });
    }
    return;
  }

  const isAdmin = state.user.role === 'admin';
  const contentId = 'main-content-area';

  const isFullPage = (state.page === 'home' || state.page === 'training' || state.page === 'training-select');

  app.innerHTML = `<div class="app-layout">
    ${sidebar()}
    <div class="main-content${isFullPage ? ' main-fullpage' : ''}">
      ${isFullPage ? '' : '<div class="content-inner">'}
      <div id="${contentId}"><div class="d-flex justify-content-center py-5"><div class="spinner-border text-primary"></div></div></div>
      ${isFullPage ? '' : '</div>'}
    </div>
  </div>`;

  const contentEl = document.getElementById(contentId);
  const pageMap = {
    home: pageHome,
    training: pageTrainingSelect,
    'training-select': pageTrainingSelect,
    'training-question': pageTrainingQuestion,
    result: pageResult,
    history: pageHistory,
    'admin-dashboard': isAdmin ? pageAdminDashboard : () => '<div class="alert alert-danger">権限がありません</div>',
    'admin-users': isAdmin ? pageAdminUsers : () => '<div class="alert alert-danger">権限がありません</div>',
    'admin-user-detail': isAdmin ? pageAdminUserDetail : () => '<div class="alert alert-danger">権限がありません</div>',
    'admin-rankings': isAdmin ? pageAdminRankings : () => '<div class="alert alert-danger">権限がありません</div>',
    'admin-content': isAdmin ? pageAdminContent : () => '<div class="alert alert-danger">権限がありません</div>',
    'admin-feedback': isAdmin ? pageAdminFeedback : () => '<div class="alert alert-danger">権限がありません</div>',
  };

  const pageFn = pageMap[state.page] || pageHome;
  try {
    const html = await pageFn();
    if (contentEl) contentEl.innerHTML = html || '';
    if (state.page === 'training-question' && (state.trainingMode === 'voice')) {
      setTimeout(initVoiceInput, 100);
    }
  } catch (e) {
    if (contentEl) contentEl.innerHTML = `<div class="alert alert-danger">${esc(e.message)}</div>`;
  }
}

// ============================================================
// Init
// ============================================================
window.addEventListener('DOMContentLoaded', () => {
  if (!state.token) {
    state.page = 'login';
  }
  render();
});
