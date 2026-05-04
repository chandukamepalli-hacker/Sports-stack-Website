const launcher = document.getElementById('chat-launcher');
const panel = document.getElementById('chat-panel');
const closeBtn = document.getElementById('chat-close');
const form = document.getElementById('chat-form');
const input = document.getElementById('chat-input');
const messages = document.getElementById('chat-messages');

function addMessage(text, role = 'bot') {
  const bubble = document.createElement('div');
  bubble.className = role === 'user' ? 'user-bubble' : 'bot-bubble';
  bubble.textContent = text;
  messages.appendChild(bubble);
  messages.scrollTop = messages.scrollHeight;
  return bubble;
}

launcher?.addEventListener('click', () => {
  panel.classList.add('open');
  input?.focus();
});
closeBtn?.addEventListener('click', () => panel.classList.remove('open'));

form?.addEventListener('submit', async (event) => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text) return;
  input.value = '';
  addMessage(text, 'user');
  const loading = addMessage('Thinking about sports products...', 'bot');
  try {
    const response = await fetch('/api/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-CSRF-Token': csrfToken
      },
      body: JSON.stringify({ message: text })
    });
    const payload = await response.json();
    loading.textContent = payload.ok ? payload.reply : (payload.error || 'Chat failed.');
  } catch (error) {
    loading.textContent = 'Chat is unavailable now, but the local sports store still works.';
  }
});
