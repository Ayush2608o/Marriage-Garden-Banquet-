/*
 * Royal Venue — customer chat
 * WhatsApp-style conversation with the venue team.
 *  - live updates by polling /account/messages/feed/
 *  - optimistic sending (clock → ✓ sent → ✓✓ blue when the team has opened it)
 *  - failed messages can be retried by tapping them
 * All message text is inserted with textContent / text nodes (never innerHTML).
 */
(() => {
  'use strict';

  const root = document.getElementById('chat');
  const initialEl = document.getElementById('chat-initial');
  if (!root || !initialEl) return;

  const feedUrl = root.dataset.feedUrl;
  const sendUrl = root.dataset.sendUrl;
  const $ = (id) => document.getElementById(id);
  const scroller = $('chat-body');
  const list = $('chat-list');
  const form = $('chat-form');
  const input = $('chat-input');
  const sendBtn = $('chat-send');
  const statusEl = $('chat-status');
  const banner = $('chat-banner');
  const downBtn = $('chat-down');
  const downCount = $('chat-down-count');
  const emojiBtn = $('emoji-btn');
  const emojiPanel = $('chat-emoji');

  const initial = JSON.parse(initialEl.textContent);
  const MAX = initial.max_length || 4000;
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const coarsePointer = window.matchMedia('(pointer: coarse)').matches;
  const baseTitle = document.title;

  const ICON = {
    one: '<svg viewBox="0 0 16 11" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-label="Sent"><path d="M2 5.8l3.2 3.2L12.4 1.8"/></svg>',
    two: '<svg viewBox="0 0 16 11" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-label="Seen"><path d="M1 5.8l3.2 3.2L11 1.8"/><path d="M5.6 8.4l.6.6 7.2-7.2"/></svg>',
    clock: '<svg viewBox="0 0 16 11" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" aria-label="Sending"><circle cx="8" cy="5.5" r="4.2"/><path d="M8 3.3v2.4l1.5 1"/></svg>',
    warn: '<svg viewBox="0 0 16 11" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" aria-label="Not sent"><circle cx="8" cy="5.5" r="4.4"/><path d="M8 3.4v2.5M8 7.6v.1"/></svg>',
  };

  /* ---------------- helpers ---------------- */
  const fmtTime = (iso) => new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  const dayKey = (iso) => { const d = new Date(iso); return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`; };
  const dayLabel = (iso) => {
    const d = new Date(iso);
    const today = new Date();
    const yesterday = new Date(); yesterday.setDate(today.getDate() - 1);
    if (dayKey(iso) === dayKey(today.toISOString())) return 'Today';
    if (dayKey(iso) === dayKey(yesterday.toISOString())) return 'Yesterday';
    return d.toLocaleDateString([], { day: 'numeric', month: 'long', year: 'numeric' });
  };

  // turn http(s) links into safe anchors, everything else stays plain text
  const URL_RE = /https?:\/\/[^\s<]+/g;
  const appendLinkified = (el, text) => {
    let last = 0;
    for (const match of text.matchAll(URL_RE)) {
      let url = match[0];
      const trail = url.match(/[.,;:!?)\]}'"]+$/);
      if (trail) url = url.slice(0, -trail[0].length);
      if (match.index > last) el.append(document.createTextNode(text.slice(last, match.index)));
      const a = document.createElement('a');
      a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer nofollow'; a.textContent = url;
      el.append(a);
      last = match.index + url.length;
    }
    if (last < text.length) el.append(document.createTextNode(text.slice(last)));
  };

  /* ---------------- state ---------------- */
  const known = new Set();          // server ids already on screen
  const entries = [];               // every bubble: {id, key, from, el, status}
  let lastId = 0;                   // highest server id returned by the feed
  let lastDay = null;
  let lastFrom = null;
  let welcomeEl = null;
  let unseen = 0;                   // new team messages while scrolled up
  let hiddenNew = 0;                // new team messages while the tab was hidden
  let dead = false;                 // session expired

  /* ---------------- scrolling ---------------- */
  const nearBottom = () => scroller.scrollHeight - scroller.scrollTop - scroller.clientHeight < 90;
  const toBottom = (smooth = false) => {
    scroller.scrollTo({ top: scroller.scrollHeight, behavior: smooth && !reduceMotion ? 'smooth' : 'auto' });
  };
  const updateDown = () => {
    const away = !nearBottom();
    downBtn.hidden = !away;
    if (!away) unseen = 0;
    downCount.hidden = unseen === 0;
    downCount.textContent = String(unseen);
  };
  scroller.addEventListener('scroll', updateDown, { passive: true });
  downBtn.addEventListener('click', () => { unseen = 0; toBottom(true); });

  /* ---------------- rendering ---------------- */
  const setStatus = (entry, status) => {
    entry.status = status;
    entry.el.dataset.status = status;
    const tick = entry.el.querySelector('.msg__tick');
    if (tick) tick.innerHTML = ICON[{ pending: 'clock', sent: 'one', read: 'two', failed: 'warn' }[status]];
    const fail = entry.el.querySelector('.msg__fail');
    if (status === 'failed' && !fail) {
      const note = document.createElement('span');
      note.className = 'msg__fail';
      note.textContent = 'Not sent. Tap to retry.';
      entry.el.querySelector('.msg__bubble').append(note);
    } else if (status !== 'failed' && fail) {
      fail.remove();
    }
  };

  const chip = (className, text) => {
    const el = document.createElement('div');
    el.className = className;
    el.textContent = text;
    return el;
  };

  const removeWelcome = () => { if (welcomeEl) { welcomeEl.remove(); welcomeEl = null; } };

  // add one message bubble (handles date chips + grouping)
  const addMessage = (m, { animate = false, status = null } = {}) => {
    removeWelcome();
    const day = dayKey(m.ts);
    if (day !== lastDay) { list.append(chip('chat__day', dayLabel(m.ts))); lastDay = day; lastFrom = null; }
    const first = lastFrom !== m.from;
    lastFrom = m.from;

    const row = document.createElement('div');
    row.className = `msg msg--${m.from}${first ? ' msg--first' : ''}${animate ? ' msg--in' : ''}`;
    const bubble = document.createElement('div');
    bubble.className = 'msg__bubble';
    const text = document.createElement('span');
    text.className = 'msg__text';
    appendLinkified(text, m.text);
    const meta = document.createElement('span');
    meta.className = 'msg__meta';
    const time = document.createElement('time');
    time.dateTime = m.ts;
    time.textContent = fmtTime(m.ts);
    meta.append(time);
    if (m.from === 'me') {
      const tick = document.createElement('span');
      tick.className = 'msg__tick';
      meta.append(tick);
    }
    bubble.append(text, meta);
    row.append(bubble);
    list.append(row);

    const entry = { id: m.id || null, key: m.key || null, from: m.from, el: row, status: null, text: m.text };
    if (m.from === 'me') setStatus(entry, status || (m.read ? 'read' : 'sent'));
    entries.push(entry);
    if (m.id) known.add(m.id);
    return entry;
  };

  const showWelcome = () => {
    welcomeEl = document.createElement('div');
    welcomeEl.className = 'msg msg--team msg--first msg--welcome';
    const bubble = document.createElement('div');
    bubble.className = 'msg__bubble';
    const who = document.createElement('span');
    who.className = 'msg__who';
    who.textContent = 'Royal Venue team';
    const text = document.createElement('span');
    text.textContent = `Hi ${initial.first_name || 'there'}! 👋 Welcome to Royal Venue. Ask us anything about our spaces, dates, pricing or planning your day, and we’ll reply right here.`;
    bubble.append(who, text);
    welcomeEl.append(bubble);
    list.append(welcomeEl);
  };

  const applyRead = (through) => {
    if (!through) return;
    for (const e of entries) {
      if (e.from === 'me' && e.id && e.id <= through && e.status === 'sent') setStatus(e, 'read');
    }
  };

  /* ---------------- connection state ---------------- */
  const setConnected = (ok) => {
    if (ok) { statusEl.textContent = statusEl.dataset.default; statusEl.classList.remove('is-warn'); }
    else { statusEl.textContent = 'Reconnecting…'; statusEl.classList.add('is-warn'); }
  };
  const sessionExpired = () => {
    dead = true;
    banner.hidden = false;
    banner.replaceChildren(document.createTextNode('Your session has expired. '));
    const a = document.createElement('a');
    a.href = `/signin/?next=${encodeURIComponent(location.pathname)}`;
    a.textContent = 'Sign in again';
    banner.append(a, document.createTextNode(' to keep chatting.'));
  };

  /* ---------------- receiving ---------------- */
  const ingest = (messages) => {
    let teamNew = 0;
    const stick = nearBottom();
    for (const m of messages) {
      if (known.has(m.id)) { lastId = Math.max(lastId, m.id); continue; }
      lastId = Math.max(lastId, m.id);
      // our own message arrived via the feed before the send call returned: adopt it, don't draw it twice
      const mine = m.cid && entries.find((e) => e.key === m.cid && !e.id);
      if (mine) { mine.id = m.id; known.add(m.id); setStatus(mine, m.read ? 'read' : 'sent'); continue; }
      addMessage(m, { animate: true });
      if (m.from === 'team') teamNew += 1;
    }
    if (!messages.length) return;
    if (stick) toBottom(true);
    else if (teamNew) { unseen += teamNew; }
    updateDown();
    if (teamNew && document.hidden) {
      hiddenNew += teamNew;
      document.title = `(${hiddenNew}) ${baseTitle}`;
    }
  };

  let polling = false;
  let failures = 0;
  let timer = 0;
  const schedule = () => {
    clearTimeout(timer);
    if (dead) return;
    const base = document.hidden ? 12000 : 3000;
    const delay = failures ? Math.min(base * 2 ** Math.min(failures, 3), 30000) : base;
    timer = setTimeout(poll, delay);
  };
  async function poll() {
    if (polling || dead) return;
    polling = true;
    try {
      const seen = document.visibilityState === 'visible' ? 1 : 0;
      const res = await fetch(`${feedUrl}?after=${lastId}&seen=${seen}`, {
        credentials: 'same-origin', cache: 'no-store',
        headers: { Accept: 'application/json', 'X-Requested-With': 'XMLHttpRequest' },
      });
      if (res.status === 401 || res.redirected) { sessionExpired(); return; }
      if (!res.ok) throw new Error(`feed ${res.status}`);
      const data = await res.json();
      failures = 0;
      setConnected(true);
      ingest(data.messages || []);
      applyRead(data.read_through);
    } catch (err) {
      failures += 1;
      if (failures >= 2) setConnected(false);
    } finally {
      polling = false;
      schedule();
    }
  }

  /* ---------------- sending ---------------- */
  const queue = [];
  let sending = false;
  let counter = 0;
  const newKey = () => `${Date.now().toString(36)}${Math.random().toString(36).slice(2, 8)}${counter++}`;

  const showError = (message) => {
    banner.hidden = false;
    banner.textContent = message;
    clearTimeout(showError.t);
    showError.t = setTimeout(() => { if (!dead) banner.hidden = true; }, 6000);
  };

  async function pump() {
    if (sending) return;
    sending = true;
    while (queue.length) {
      const job = queue[0];
      try {
        const res = await fetch(sendUrl, {
          method: 'POST', credentials: 'same-origin',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': form.querySelector('[name=csrfmiddlewaretoken]').value, 'X-Requested-With': 'XMLHttpRequest' },
          body: JSON.stringify({ message: job.text, client_id: job.key }),
        });
        if (res.status === 401 || res.redirected) { sessionExpired(); throw new Error('expired'); }
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(res.status === 403 ? 'Security check expired. Please refresh the page.' : data.error || 'Could not send your message.');
        }
        const m = data.message;
        job.entry.id = m.id;
        known.add(m.id);
        job.entry.el.querySelector('time').textContent = fmtTime(m.ts);
        setStatus(job.entry, m.read ? 'read' : 'sent');
        failures = 0;
        setConnected(true);
      } catch (err) {
        setStatus(job.entry, 'failed');
        if (err.message && err.message !== 'expired' && err.message !== 'Failed to fetch') showError(err.message);
        else if (err.message === 'Failed to fetch') setConnected(false);
      }
      queue.shift();
    }
    sending = false;
    poll(); // pick up anything the team wrote meanwhile
  }

  const submit = (text) => {
    const key = newKey();
    const entry = addMessage({ id: null, key, from: 'me', text, ts: new Date().toISOString() }, { animate: true, status: 'pending' });
    toBottom(true);
    queue.push({ key, text, entry });
    pump();
  };

  // tap a failed message to retry it
  list.addEventListener('click', (event) => {
    const row = event.target.closest('.msg');
    const entry = row && entries.find((e) => e.el === row);
    if (!entry || entry.status !== 'failed' || dead) return;
    setStatus(entry, 'pending');
    queue.push({ key: entry.key || newKey(), text: entry.text, entry });
    pump();
  });

  /* ---------------- composer ---------------- */
  const autosize = () => {
    input.style.height = 'auto';
    input.style.height = `${Math.min(input.scrollHeight, 124)}px`;
  };
  const refreshSend = () => { sendBtn.disabled = dead || input.value.trim().length === 0; };
  input.addEventListener('input', () => { autosize(); refreshSend(); });
  input.addEventListener('keydown', (event) => {
    // desktop: Enter sends, Shift+Enter = new line. Phones: Enter = new line (use the send button).
    if (event.key === 'Enter' && !event.shiftKey && !coarsePointer && !event.isComposing) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || dead) return;
    submit(text.slice(0, MAX));
    input.value = '';
    autosize();
    refreshSend();
    closeEmoji();
    if (!coarsePointer) input.focus();
  });

  /* ---------------- emoji ---------------- */
  const EMOJIS = ['😊', '😀', '😍', '🥰', '😂', '🙏', '👍', '❤️', '💍', '💐', '🎉', '✨', '🥂', '🎊', '👰', '🤵', '💒', '🌹', '🪔', '🎶', '📅', '📍', '💬', '😅', '🙌', '👏', '🤝', '🎂', '🍽️', '🏰', '🌸', '💫', '😉', '🤗', '😢', '😮', '🔥', '💯', '✅', '❓'];
  EMOJIS.forEach((emoji) => {
    const b = document.createElement('button');
    b.type = 'button'; b.textContent = emoji; b.setAttribute('aria-label', `Insert ${emoji}`);
    b.addEventListener('click', () => {
      const start = input.selectionStart ?? input.value.length;
      const end = input.selectionEnd ?? input.value.length;
      input.setRangeText(emoji, start, end, 'end');
      input.dispatchEvent(new Event('input'));
      if (!coarsePointer) input.focus();
    });
    emojiPanel.append(b);
  });
  function closeEmoji() { emojiPanel.hidden = true; emojiBtn.setAttribute('aria-expanded', 'false'); }
  emojiBtn.addEventListener('click', () => {
    const open = emojiPanel.hidden;
    emojiPanel.hidden = !open;
    emojiBtn.setAttribute('aria-expanded', String(open));
    if (nearBottom()) requestAnimationFrame(() => toBottom());
  });
  document.addEventListener('keydown', (event) => { if (event.key === 'Escape') closeEmoji(); });
  scroller.addEventListener('pointerdown', closeEmoji);

  /* ---------------- tab visibility ---------------- */
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) { hiddenNew = 0; document.title = baseTitle; failures = 0; poll(); }
    else schedule();
  });
  window.addEventListener('focus', () => { hiddenNew = 0; document.title = baseTitle; });
  window.addEventListener('online', () => { failures = 0; poll(); });
  window.addEventListener('resize', () => { if (nearBottom()) toBottom(); });

  /* ---------------- boot ---------------- */
  if (!initial.messages.length) {
    showWelcome();
  } else {
    for (const m of initial.messages) {
      if (m.id === initial.first_unread_id) {
        const unreadCount = initial.messages.filter((x) => x.from === 'team' && x.id >= m.id && !x.read).length;
        list.append(chip('chat__unread', `${unreadCount} unread message${unreadCount === 1 ? '' : 's'}`));
        lastFrom = null;
      }
      addMessage(m);
      lastId = Math.max(lastId, m.id);
    }
    applyRead(initial.read_through);
  }
  requestAnimationFrame(() => { toBottom(); updateDown(); if (!coarsePointer) input.focus(); });
  schedule();
})();
