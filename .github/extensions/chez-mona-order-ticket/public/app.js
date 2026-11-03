const token = new URLSearchParams(location.search).get('token');
const error = document.querySelector('#error');
const connection = document.querySelector('#connection');
let pending = false;
let revision = -1;
const escape = value => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);

const tabs = [...document.querySelectorAll('[role="tab"]')];
let activeStep = 0;
function selectStep(index, focus = false) {
  activeStep = index;
  tabs.forEach((tab, position) => {
    const selected = position === index;
    tab.setAttribute('aria-selected', String(selected));
    tab.tabIndex = selected ? 0 : -1;
    document.getElementById(tab.getAttribute('aria-controls')).hidden = !selected;
  });
  document.querySelector('#previous-step').hidden = index === 0;
  const next = document.querySelector('#next-step');
  next.hidden = index === tabs.length - 1;
  document.querySelector('#copy-status').textContent = '';
  if (focus) tabs[index].focus();
}
tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => selectStep(index));
  tab.addEventListener('keydown', event => {
    let target;
    if (event.key === 'ArrowRight') target = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') target = (index + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') target = 0;
    if (event.key === 'End') target = tabs.length - 1;
    if (target !== undefined) {
      event.preventDefault();
      selectStep(target, true);
    }
  });
});
document.querySelector('#previous-step').addEventListener('click', () => selectStep(activeStep - 1, true));
document.querySelector('#next-step').addEventListener('click', () => selectStep(activeStep + 1, true));

function render(ticket) {
  if (ticket.revision < revision) return;
  revision = ticket.revision;
  document.querySelector('#menu').innerHTML = ticket.menu.map(dish =>
    `<article class="dish"><button data-action="add_dish" data-dish="${escape(dish.id)}">Add ${escape(dish.name)}</button></article>`).join('');
  document.querySelector('#total').textContent = `${ticket.total} ${ticket.total === 1 ? 'dish' : 'dishes'}`;
  document.querySelector('#items').innerHTML = ticket.items.length ? ticket.items.map(item =>
    `<div class="item"><div><span class="quantity">${item.quantity} x</span><strong>${escape(item.name)}</strong></div><button class="secondary" data-action="remove_dish" data-dish="${escape(item.dishId)}" aria-label="Remove one ${escape(item.name)}">Remove</button></div>`).join('') :
    '<p class="empty">Your ticket is empty.</p>';
  document.querySelector('#clear').hidden = !ticket.items.length;
  for (const button of document.querySelectorAll('#workspace button')) button.disabled = pending;
}

async function act(action, input) {
  if (pending) return;
  pending = true;
  error.hidden = true;
  for (const button of document.querySelectorAll('#workspace button')) button.disabled = true;
  try {
    const response = await fetch('/action', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-Ticket-Token': token },
      body: JSON.stringify({ action, input })
    });
    const ticket = await response.json();
    if (!response.ok) throw new Error(ticket.error);
    render(ticket);
  } catch (failure) {
    console.error('Ticket action:', failure);
    error.textContent = `Could not confirm the ticket change: ${failure.message}. Check the ticket before trying again.`;
    error.hidden = false;
  } finally {
    pending = false;
    for (const button of document.querySelectorAll('#workspace button')) button.disabled = false;
  }
}
document.querySelector('main').addEventListener('click', event => {
  const button = event.target.closest('[data-action]');
  if (button) act(button.dataset.action, { dishId: button.dataset.dish, quantity: 1 });
});
document.querySelector('#clear').addEventListener('click', () => act('clear_ticket', {}));
document.querySelectorAll('[data-copy]').forEach(button => {
  button.addEventListener('click', async () => {
    const status = document.querySelector('#copy-status');
    const prompt = document.getElementById(button.dataset.copy).textContent;
    try {
      await navigator.clipboard.writeText(prompt);
      status.textContent = 'Prompt copied. Paste it into the chat and send it.';
    } catch (failure) {
      console.error('Copy prompt:', failure);
      status.textContent = 'Could not copy the prompt. Select the prompt text above and copy it manually, then paste it into chat.';
    }
  });
});
document.querySelectorAll('[data-send]').forEach(button => {
  button.addEventListener('click', async () => {
    const status = document.querySelector('#copy-status');
    button.disabled = true;
    try {
      const response = await fetch('/prompt', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Ticket-Token': token },
        body: JSON.stringify({ promptId: button.dataset.send })
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.error);
      status.textContent = 'Prompt sent. Check your chat.';
    } catch (failure) {
      console.error('Send prompt:', failure);
      status.textContent = `Could not send the prompt: ${failure.message}. Type it into chat instead.`;
    } finally {
      button.disabled = false;
    }
  });
});
const events = new EventSource(`/events?token=${encodeURIComponent(token)}`);
events.onmessage = event => {
  try {
    render(JSON.parse(event.data));
    connection.hidden = true;
  } catch (failure) {
    console.error('Ticket update:', failure);
    error.textContent = `Could not read the ticket update: ${failure.message}`;
    error.hidden = false;
  }
};
events.onerror = () => {
  connection.textContent = 'Connection interrupted. Reconnecting...';
  connection.hidden = false;
};
window.addEventListener('pagehide', () => events.close());
