let ws = null;
let micMuted = false;
let timerInterval = null;
let sessionStart = null;
let transcript = [];
let questionCount = 0;
let userTurns = 0;

// helpers 
function show(id) {
  ['setup','interview','results'].forEach(s => {
    document.getElementById(s).style.display = s === id ? 'flex' : 'none';
  });
  if (id === 'interview') document.getElementById('interview').style.flexDirection = 'column';
}

function showError(msg) {
  const t = document.getElementById('error-toast');
  t.textContent = msg;
  t.style.display = 'block';
  setTimeout(() => t.style.display = 'none', 4000);
}

// timer
function startTimer() {
  sessionStart = Date.now();
  timerInterval = setInterval(() => {
    const s = Math.floor((Date.now() - sessionStart) / 1000);
    const mm = String(Math.floor(s / 60)).padStart(2,'0');
    const ss = String(s % 60).padStart(2,'0');
    document.getElementById('timer').textContent = `${mm}:${ss}`;
  }, 1000);
}

function stopTimer() {
  clearInterval(timerInterval);
  const s = Math.floor((Date.now() - sessionStart) / 1000);
  const mm = String(Math.floor(s / 60)).padStart(2,'0');
  const ss = String(s % 60).padStart(2,'0');
  return `${mm}:${ss}`;
}

function setAIState(state) {
  const dot  = document.getElementById('status-dot');
  const text = document.getElementById('status-text');
  const bars = document.querySelectorAll('.wave-bar');

  dot.className = `status-dot ${state}`;
  bars.forEach(b => b.classList.remove('active'));

  if (state === 'speaking') {
    text.textContent = 'Alex is speaking…';
  } else if (state === 'listening') {
    text.textContent = 'Your turn — speak now';
    bars.forEach(b => b.classList.add('active'));
  } else if (state === 'connecting') {
    text.textContent = 'Connecting…';
  } else {
    text.textContent = 'Connected';
  }
}

// transcript 
function addMessage(speaker, text) {
  document.getElementById('empty-state')?.remove();

  transcript.push({ speaker, text });
  if (speaker === 'Alex') questionCount++;
  else userTurns++;

  const box = document.getElementById('transcript');
  const msg = document.createElement('div');
  msg.className = `msg ${speaker === 'Alex' ? 'alex' : 'user'}`;
  msg.innerHTML = `
    <div class="msg-label">${speaker}</div>
    <div class="msg-bubble">${text}</div>
  `;
  box.appendChild(msg);
  box.scrollTop = box.scrollHeight;
}

// mic toggle 
function toggleMic() {
  micMuted = !micMuted;
  const btn = document.getElementById('mic-btn');
  if (micMuted) {
    btn.className = 'mic-btn muted';
    btn.textContent = '🔇 Mic Off';
    ws?.send(JSON.stringify({ type: 'mic_mute', muted: true }));
  } else {
    btn.className = 'mic-btn active';
    btn.textContent = '🎙️ Mic On';
    ws?.send(JSON.stringify({ type: 'mic_mute', muted: false }));
  }
}

// session start 
function startSession() {
  const config = {
    role:       document.getElementById('role').value,
    company:    document.getElementById('company').value,
    focus:      document.getElementById('focus').value,
    difficulty: document.getElementById('difficulty').value,
  };

  // Reset state
  transcript = []; questionCount = 0; userTurns = 0; micMuted = false;
  document.getElementById('mic-btn').className = 'mic-btn active';
  document.getElementById('mic-btn').textContent = '🎙️ Mic On';
  document.getElementById('transcript').innerHTML = '<div class="empty-state" id="empty-state">Waiting for the interviewer to connect…</div>';
  document.getElementById('timer').textContent = '00:00';

  // Update header
  document.getElementById('header-role').textContent = config.role;
  document.getElementById('header-meta').textContent = `${config.company} · ${config.focus} · ${config.difficulty}`;

  show('interview');
  setAIState('connecting');

  // Connect WebSocket
  const sessionId = Math.random().toString(36).slice(2);
  const protocol  = location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${protocol}://${location.host}/ws/${sessionId}`);

  ws.onopen = () => {
    ws.send(JSON.stringify(config));
    startTimer();
  };

  ws.onmessage = (e) => {
    const msg = JSON.parse(e.data);

    if (msg.type === 'status' && msg.message === 'connected') {
      setAIState('listening');
    } else if (msg.type === 'ai_state') {
      setAIState(msg.state);
    } else if (msg.type === 'transcript') {
      addMessage(msg.speaker, msg.text);
    } else if (msg.type === 'error') {
      showError('Error: ' + msg.message);
    }
  };

  ws.onclose = () => {
    if (document.getElementById('interview').style.display !== 'none') {
      showError('Connection closed.');
    }
  };

  ws.onerror = () => showError('WebSocket connection failed. Is the server running?');
}

// session end
function endSession() {
  ws?.close();
  const duration = stopTimer();

  document.getElementById('r-duration').textContent  = duration;
  document.getElementById('r-questions').textContent = questionCount;
  document.getElementById('r-turns').textContent     = userTurns;

  const replay = document.getElementById('transcript-replay');
  if (!transcript.length) {
    replay.innerHTML = '<span style="color:#aeaeb2">No transcript recorded.</span>';
  } else {
    replay.innerHTML = transcript.map(e => `
      <div class="replay-entry">
        <div class="replay-speaker ${e.speaker === 'Alex' ? 'alex-lbl' : 'user-lbl'}">${e.speaker}</div>
        <div>${e.text}</div>
      </div>
    `).join('');
  }

  show('results');
}

function goBack() {
  ws?.close();
  show('setup');
}