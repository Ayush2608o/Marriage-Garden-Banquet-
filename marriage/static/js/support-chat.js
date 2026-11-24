(() => {
  const panel = document.getElementById('support-panel');
  const openButton = document.getElementById('support-open');
  const closeButton = document.getElementById('support-close');
  const startForm = document.getElementById('support-form');
  const chat = document.getElementById('support-chat');
  const messages = document.getElementById('support-messages');
  const result = document.getElementById('support-result');
  const replyForm = document.getElementById('support-reply-form');
  const replyInput = document.getElementById('support-reply-text');
  const csrfToken = startForm.querySelector('[name="csrfmiddlewaretoken"]').value;
  let threadId = null;
  let refreshTimer = null;
  let loading = false;

  async function request(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.headers || {}),
        'X-CSRFToken': csrfToken,
      },
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || 'Chat is temporarily unavailable. Please try again.');
    }
    return data;
  }

  function showChat() {
    startForm.hidden = true;
    chat.hidden = false;
    result.textContent = '';
    loadMessages();
    window.clearInterval(refreshTimer);
    refreshTimer = window.setInterval(loadMessages, 3000);
    replyInput.focus();
  }

  function renderMessages(items) {
    if (!items.length) {
      const empty = document.createElement('p');
      empty.className = 'support-chat-empty';
      empty.textContent = 'Your message is here. Our team will reply shortly.';
      messages.replaceChildren(empty);
      return;
    }
    messages.replaceChildren(...items.map((item) => {
      const bubble = document.createElement('article');
      bubble.className = `support-message${item.sender_type === 'CUSTOMER' ? ' is-mine' : ''}`;
      bubble.append(document.createTextNode(item.message_text || '[Attachment]'));
      const time = document.createElement('time');
      time.className = 'support-message-time';
      time.dateTime = item.timestamp;
      time.textContent = new Date(item.timestamp).toLocaleString();
      bubble.append(time);
      return bubble;
    }));
    messages.scrollTop = messages.scrollHeight;
  }

  async function loadMessages() {
    if (!threadId || loading || document.hidden) return;
    loading = true;
    try {
      const data = await request(`/api/whatsapp/threads/${threadId}/messages/`);
      renderMessages(data.messages);
      result.textContent = '';
    } catch (error) {
      result.textContent = error.message;
      window.clearInterval(refreshTimer);
    } finally {
      loading = false;
    }
  }

  openButton.addEventListener('click', () => {
    panel.hidden = !panel.hidden;
    openButton.setAttribute('aria-expanded', String(!panel.hidden));
    if (!panel.hidden && threadId) showChat();
  });

  closeButton.addEventListener('click', () => {
    panel.hidden = true;
    openButton.setAttribute('aria-expanded', 'false');
    window.clearInterval(refreshTimer);
  });

  startForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    const submit = startForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    result.textContent = 'Sending your message…';
    try {
      const data = await request('/api/whatsapp/threads/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(Object.fromEntries(new FormData(startForm))),
      });
      threadId = data.thread_id;
      startForm.reset();
      showChat();
    } catch (error) {
      result.textContent = error.message;
    } finally {
      submit.disabled = false;
    }
  });

  replyForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    if (!threadId || !replyInput.value.trim()) return;
    const submit = replyForm.querySelector('button[type="submit"]');
    submit.disabled = true;
    result.textContent = '';
    try {
      await request(`/api/whatsapp/threads/${threadId}/send/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: replyInput.value }),
      });
      replyInput.value = '';
      await loadMessages();
    } catch (error) {
      result.textContent = error.message;
    } finally {
      submit.disabled = false;
    }
  });

  request('/api/whatsapp/threads/current/')
    .then((data) => {
      if (data.thread_id) {
        threadId = data.thread_id;
        startForm.hidden = true;
      }
    })
    .catch((error) => {
      result.textContent = error.message;
    });
})();
