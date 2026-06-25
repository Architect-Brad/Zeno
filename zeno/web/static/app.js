/**
 * Zeno Web UI — client-side logic.
 * Handles chat, voice input (Web Speech API), settings, and session management.
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

  function addMessage(text, role) {
    const div = document.createElement('div');
    div.className = `msg ${role}-msg`;

    const label = document.createElement('div');
    label.className = `msg-label ${role}-label`;
    label.textContent = role === 'user' ? 'You' : 'Zeno';
    div.appendChild(label);

    const content = document.createElement('div');
    content.textContent = text;
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
      document.getElementById('setting-voice').textContent = c.tts && c.stt ? '✅ Full' : c.tts ? '🔊 TTS only' : c.stt ? '🎤 STT only' : '❌ None';
      document.getElementById('setting-notif').textContent = c.notifications ? '✅ Yes' : '❌ No';
      document.getElementById('setting-vol').textContent = c.volume ? '✅ Yes' : '❌ No';
      document.getElementById('setting-bright').textContent = c.brightness ? '✅ Yes' : '❌ No';
      document.getElementById('setting-lock').textContent = c.lock_screen ? '✅ Yes' : '❌ No';
    } catch (_) {}
  }

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

  // ---------- Event Bindings ----------

  DOM.sendBtn.addEventListener('click', () => sendText(DOM.input.value));
  DOM.voiceBtn.addEventListener('click', toggleVoice);
  DOM.settingsBtn.addEventListener('click', () => {
    DOM.settingsPanel.classList.remove('hidden');
    loadSettings();
  });
  DOM.closeSettings.addEventListener('click', () => DOM.settingsPanel.classList.add('hidden'));
  DOM.clearBtn.addEventListener('click', clearHistory);

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
