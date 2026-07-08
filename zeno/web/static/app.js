/**
 * Zeno Web UI — client-side logic.
 * Handles chat, voice input (Web Speech API), settings, peers, and timers.
 */

(function () {
  'use strict';

  const DOM = {
    chatLog: document.getElementById('chat-log'),
    chatContainer: document.getElementById('chat-container'),
    input: document.getElementById('text-input'),
    sendBtn: document.getElementById('btn-send'),
    voiceBtn: document.getElementById('btn-voice'),
    settingsBtn: document.getElementById('btn-settings'),
    settingsPanel: document.getElementById('settings-panel'),
    closeSettings: document.getElementById('btn-close-settings'),
    clearBtn: document.getElementById('btn-clear'),
    toast: document.getElementById('status-toast'),
    peersBtn: document.getElementById('btn-peers'),
    peersPanel: document.getElementById('peers-panel'),
    peersList: document.getElementById('peers-list'),
    closePeers: document.getElementById('btn-close-peers'),
  };

  let toastTimer = null;

  // ---------- Toast ----------

  function showToast(msg, duration = 2000) {
    DOM.toast.textContent = msg;
    DOM.toast.classList.remove('hidden');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => DOM.toast.classList.add('hidden'), duration);
  }

  // ---------- Chat ----------

  function formatMarkdown(text) {
    const escaped = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
    const blocks = escaped.split(/(```[\s\S]*?```)/);
    return blocks.map((b, i) => {
      if (i % 2 === 0) {
        return b
          .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
          .replace(/`([^`]+)`/g, '<code>$1</code>')
          .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
          .replace(/\n/g, '<br>');
      }
      const code = b.slice(3, -3);
      const lang = code.split('\n')[0].trim();
      const body = code.includes('\n') ? code.slice(code.indexOf('\n')) : code;
      const langClass = lang ? ` class="lang-${lang}"` : '';
      return `<pre${langClass}><code>${body.trim()}</code></pre>`;
    }).join('');
  }

  function addMessage(text, role) {
    const div = document.createElement('div');
    div.className = `msg ${role}-msg`;

    const label = document.createElement('div');
    label.className = `msg-label ${role}-label`;
    const now = new Date();
    const ts = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}`;
    label.textContent = role === 'user' ? `You — ${ts}` : `Zeno — ${ts}`;
    div.appendChild(label);

    const content = document.createElement('div');
    if (role === 'zeno') {
      content.innerHTML = formatMarkdown(text);
    } else {
      content.textContent = text;
    }
    div.appendChild(content);

    DOM.chatLog.appendChild(div);
    scrollToBottom();
  }

  function showTyping() {
    const div = document.createElement('div');
    div.className = 'typing';
    div.id = 'typing-indicator';
    div.innerHTML = '<div class="typing-dots"><span></span><span></span><span></span></div>';
    DOM.chatLog.appendChild(div);
    scrollToBottom();
  }

  function hideTyping() {
    const el = document.getElementById('typing-indicator');
    if (el) el.remove();
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      DOM.chatContainer.scrollTop = DOM.chatContainer.scrollHeight;
    });
  }

  async function sendText(text) {
    if (!text.trim()) return;

    addMessage(text, 'user');
    DOM.input.value = '';
    DOM.input.style.height = 'auto';
    showTyping();

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      hideTyping();

      if (data.response) {
        addMessage(data.response, 'zeno');
      }
    } catch (err) {
      hideTyping();
      addMessage('Sorry, something went wrong. Please try again.', 'zeno');
      console.error('Chat error:', err);
    }
  }

  // ---------- Voice Input (Web Speech API) ----------

  let recognition = null;
  let isRecording = false;

  function initSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) return false;

    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      isRecording = true;
      DOM.voiceBtn.classList.add('recording');
      showToast('Listening...');
    };

    recognition.onresult = (e) => {
      const transcript = e.results[0][0].transcript.trim();
      if (transcript) {
        DOM.input.value = transcript;
        sendText(transcript);
      }
    };

    recognition.onerror = (e) => {
      console.error('Speech error:', e.error);
      if (e.error === 'not-allowed') {
        showToast('Microphone access denied. Using text input.', 3000);
      } else if (e.error === 'no-speech') {
        showToast('No speech detected.', 1500);
      } else {
        showToast(`Voice error: ${e.error}`, 3000);
      }
      stopRecording();
    };

    recognition.onend = () => {
      stopRecording();
    };

    return true;
  }

  function toggleVoice() {
    if (!recognition) {
      const supported = initSpeechRecognition();
      if (!supported) {
        showToast('Voice input not supported in this browser. Use text input.', 3000);
        return;
      }
    }

    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }

  function startRecording() {
    if (!recognition) return;
    try {
      recognition.start();
    } catch (_) {
      // already started
    }
  }

  function stopRecording() {
    if (recognition) {
      try { recognition.stop(); } catch (_) {}
    }
    isRecording = false;
    DOM.voiceBtn.classList.remove('recording');
  }

  // ---------- Settings ----------

  async function loadSettings() {
    try {
      const res = await fetch('/api/health');
      const data = await res.json();
      document.getElementById('setting-platform').textContent = data.platform || 'unknown';
      const c = data.caps || {};
      document.getElementById('setting-voice').textContent = c.tts && c.stt ? 'Full' : c.tts ? 'TTS only' : c.stt ? 'STT only' : 'None';
      document.getElementById('setting-notif').textContent = c.notifications ? 'Yes' : 'No';
      document.getElementById('setting-vol').textContent = c.volume ? 'Yes' : 'No';
      document.getElementById('setting-bright').textContent = c.brightness ? 'Yes' : 'No';
      document.getElementById('setting-lock').textContent = c.lock_screen ? 'Yes' : 'No';
    } catch (_) {}
  }

  async function loadProfile() {
    try {
      const res = await fetch('/api/profile');
      const data = await res.json();
      document.getElementById('edit-name').value = data.name || '';
      document.getElementById('edit-location').value = data.location || '';
      document.getElementById('edit-owm-key').value = data.owm_api_key || '';
      document.getElementById('edit-units').value = data.units || 'celsius';
      document.getElementById('edit-timezone').value = data.timezone || '';
    } catch (_) {}
  }

  async function saveProfile() {
    const body = {
      name: document.getElementById('edit-name').value.trim(),
      location: document.getElementById('edit-location').value.trim(),
      owm_api_key: document.getElementById('edit-owm-key').value.trim(),
      units: document.getElementById('edit-units').value,
      timezone: document.getElementById('edit-timezone').value.trim(),
    };
    try {
      const res = await fetch('/api/profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (res.ok) {
        const status = document.getElementById('profile-status');
        status.textContent = 'Profile saved.';
        status.style.display = 'block';
        setTimeout(() => { status.style.display = 'none'; }, 2000);
        showToast('Profile saved');
      }
    } catch (_) {
      showToast('Failed to save profile', 2000);
    }
  }

  document.getElementById('btn-save-profile').addEventListener('click', saveProfile);

  // ---------- History ----------

  async function loadHistory() {
    try {
      const res = await fetch('/api/history');
      const data = await res.json();
      const history = data.history || [];

      const welcome = DOM.chatLog.querySelector('.welcome');
      if (history.length > 0 && welcome) welcome.remove();

      for (const entry of history) {
        if (entry.user) addMessage(entry.user, 'user');
        if (entry.zeno) addMessage(entry.zeno, 'zeno');
      }
    } catch (_) {}
  }

  async function clearHistory() {
    try {
      await fetch('/api/history', { method: 'DELETE' });
      DOM.chatLog.innerHTML = `
        <div class="welcome">
          <div class="zeno-msg msg">Conversation cleared. Start fresh!</div>
        </div>`;
      showToast('History cleared');
    } catch (_) {
      showToast('Failed to clear history', 2000);
    }
  }

  // ---------- Timers Panel ----------

  let timersInterval = null;

  const DOM_T = {
    panel: document.getElementById('timers-panel'),
    btn: document.getElementById('btn-timers'),
    close: document.getElementById('btn-close-timers'),
    list: document.getElementById('timers-list'),
  };

  async function refreshTimers() {
    try {
      const res = await fetch('/api/timers');
      const data = await res.json();
      const timers = data.timers || [];
      DOM_T.list.innerHTML = '';

      if (timers.length === 0) {
        DOM_T.list.innerHTML = '<div class="setting-info">No active timers or alarms.</div>';
        return;
      }

      for (const t of timers) {
        const card = document.createElement('div');
        card.className = 'timer-card';
        card.dataset.id = t.id;
        card.dataset.remaining = t.remaining;
        card.dataset.total = t.total;

        const pct = t.total > 0 ? ((t.total - t.remaining) / t.total * 100) : 0;
        const mins = Math.floor(t.remaining / 60);
        const secs = t.remaining % 60;
        const timeStr = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;

        card.innerHTML = `
          <div class="timer-label">${t.is_alarm ? '⏰' : '⏱'} ${t.label}</div>
          <div class="timer-remaining">${timeStr}</div>
          <div class="timer-bar"><div class="timer-bar-fill" style="width:${pct}%"></div></div>
          <button class="timer-cancel" data-id="${t.id}">Cancel</button>
        `;

        card.querySelector('.timer-cancel').addEventListener('click', async () => {
          await fetch(`/api/timers/${t.id}/cancel`, { method: 'POST' });
          refreshTimers();
        });

        DOM_T.list.appendChild(card);
      }
    } catch (_) {}
  }

  DOM_T.btn.addEventListener('click', () => {
    DOM_T.panel.classList.remove('hidden');
    refreshTimers();
    timersInterval = setInterval(refreshTimers, 1000);
  });

  DOM_T.close.addEventListener('click', () => {
    DOM_T.panel.classList.add('hidden');
    clearInterval(timersInterval);
  });

  document.addEventListener('click', (e) => {
    if (!DOM_T.panel.classList.contains('hidden') &&
        !DOM_T.panel.contains(e.target) &&
        e.target !== DOM_T.btn &&
        !DOM_T.btn.contains(e.target)) {
      DOM_T.panel.classList.add('hidden');
      clearInterval(timersInterval);
    }
  });

  // ---------- Peers Panel ----------

  let peersInterval = null;

  const DOM_P = {
    panel: document.getElementById('peers-panel'),
    btn: document.getElementById('btn-peers'),
    close: document.getElementById('btn-close-peers'),
    list: document.getElementById('peers-list'),
  };

  async function refreshPeers() {
    try {
      const res = await fetch('/api/sync/peers');
      const data = await res.json();
      const peers = data.peers || [];
      DOM_P.list.innerHTML = '';

      if (peers.length === 0) {
        DOM_P.list.innerHTML = '<div class="setting-info">No LAN peers found. Ensure other Zeno instances are running with sync enabled on the same network.</div>';
        return;
      }

      for (const p of peers) {
        const card = document.createElement('div');
        card.className = 'peer-card';
        const age = Date.now() / 1000 - (p.last_seen || 0);
        const online = age < 60;
        card.innerHTML = `
          <div class="peer-name">${p.name || p.id}</div>
          <div class="peer-host">${p.host}:${p.port}</div>
          <div class="peer-status ${online ? '' : 'offline'}">${online ? 'Online' : 'Offline'}</div>
        `;
        DOM_P.list.appendChild(card);
      }
    } catch (_) {
      DOM_P.list.innerHTML = '<div class="setting-info">Could not reach sync service.</div>';
    }
  }

  DOM_P.btn.addEventListener('click', () => {
    DOM_P.panel.classList.remove('hidden');
    refreshPeers();
    peersInterval = setInterval(refreshPeers, 5000);
  });

  DOM_P.close.addEventListener('click', () => {
    DOM_P.panel.classList.add('hidden');
    clearInterval(peersInterval);
  });

  document.addEventListener('click', (e) => {
    if (!DOM_P.panel.classList.contains('hidden') &&
        !DOM_P.panel.contains(e.target) &&
        e.target !== DOM_P.btn &&
        !DOM_P.btn.contains(e.target)) {
      DOM_P.panel.classList.add('hidden');
      clearInterval(peersInterval);
    }
  });

  // ---------- Event Bindings ----------

  DOM.sendBtn.addEventListener('click', () => sendText(DOM.input.value));
  DOM.voiceBtn.addEventListener('click', toggleVoice);
  DOM.settingsBtn.addEventListener('click', () => {
    DOM.settingsPanel.classList.remove('hidden');
    loadSettings();
    loadProfile();
  });
  DOM.closeSettings.addEventListener('click', () => DOM.settingsPanel.classList.add('hidden'));
  DOM.clearBtn.addEventListener('click', clearHistory);

  function autoResizeInput() {
    DOM.input.style.height = 'auto';
    DOM.input.style.height = Math.min(DOM.input.scrollHeight, 120) + 'px';
  }

  DOM.input.addEventListener('input', autoResizeInput);

  DOM.input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      DOM.sendBtn.click();
    }
  });

  document.addEventListener('click', (e) => {
    if (!DOM.settingsPanel.classList.contains('hidden') &&
        !DOM.settingsPanel.contains(e.target) &&
        e.target !== DOM.settingsBtn &&
        !DOM.settingsBtn.contains(e.target)) {
      DOM.settingsPanel.classList.add('hidden');
    }
  });

  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
      DOM.sendBtn.click();
    }
  });

  // ---------- Init ----------

  initSpeechRecognition();
  loadHistory();
  loadSettings();
  DOM.input.focus();

})();
