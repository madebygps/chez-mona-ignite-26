"use strict";

// Chez Mona fridge: pick a dish, confirm, print an order ticket.
// Screens: menu, confirm, printing, done, error.

const app = document.getElementById("app");
const CONFIRM_SECONDS = 30;
const DONE_SECONDS = 12;

const state = {
  dishes: [],
  station: { fridge_number: 1, dry_run: true },
  screen: null,
  timer: null,
};

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function fmt(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
}

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
  const response = await fetch(path, options);
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || `Request failed (${response.status})`);
  return data;
}

function on(id, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener("click", handler);
  return el;
}

// Returns to the menu after a while, so an abandoned screen does not block the next guest.
function show(screen, html, resetAfterSeconds) {
  state.screen = screen;
  app.innerHTML = html;
  clearTimeout(state.timer);
  if (resetAfterSeconds) state.timer = setTimeout(renderMenu, resetAfterSeconds * 1000);
  window.scrollTo(0, 0);
}

function dish(id) {
  return state.dishes.find((d) => d.id === id);
}

function renderMenu() {
  show("menu", `
    <section class="menu">
      <p class="eyebrow">Today's menu</p>
      <h1>What would you like to cook?</h1>
      <p class="lede">Pick a dish. Take your ticket to any open cooking station.</p>
      <div class="menu-grid">
        ${state.dishes.map((d) => `
          <button class="menu-item" data-dish="${escapeHtml(d.id)}">
            <span class="menu-dish">${escapeHtml(d.dish)}</span>
            <span class="menu-lab">${escapeHtml(d.lab)}</span>
            <span class="menu-learn">${fmt(d.learn)}</span>
          </button>`).join("")}
      </div>
    </section>`);
  app.querySelectorAll(".menu-item").forEach((b) => b.addEventListener("click", () => renderConfirm(b.dataset.dish)));
}

function renderConfirm(id) {
  const d = dish(id);
  show("confirm", `
    <section class="card center confirm">
      <p class="eyebrow">Your order</p>
      <h1>${escapeHtml(d.dish)}</h1>
      <p class="lede">${escapeHtml(d.lab)}. ${fmt(d.learn)}</p>
      <div class="row" style="justify-content: center">
        <button class="primary" id="order">Print my ticket</button>
        <button id="back">Back to menu</button>
      </div>
    </section>`, CONFIRM_SECONDS);
  on("order", () => printTicket(id));
  on("back", renderMenu);
}

async function printTicket(id) {
  const d = dish(id);
  show("printing", `
    <section class="card center">
      <h1>Printing your ticket…</h1>
      <p class="lede">${escapeHtml(d.dish)}</p>
    </section>`);
  try {
    const result = await api("/api/ticket", { dish: id });
    const preview = result.status === "dry_run"
      ? `<p class="muted small">Dry run: nothing was printed. This is the ticket.</p>
         <img class="receipt-preview" src="${result.preview}" alt="Ticket preview">`
      : "";
    show("done", `
      <section class="card center">
        <p class="eyebrow">Order #${escapeHtml(result.order)}</p>
        <h1>Take your ticket</h1>
        <p class="lede">Scan it at any open cooking station to cook <strong>${escapeHtml(d.dish)}</strong>.</p>
        ${preview}
        <div class="row" style="justify-content: center">
          <button class="primary" id="next">Done</button>
        </div>
      </section>`, DONE_SECONDS);
    on("next", renderMenu);
  } catch (error) {
    // No automatic retry: the printer may have printed even if the request failed.
    show("error", `
      <section class="card center">
        <h1>The ticket did not print</h1>
        <p class="lede">Please ask a member of staff for help.</p>
        <pre class="detail">${escapeHtml(error.message)}</pre>
        <div class="row" style="justify-content: center">
          <button class="primary" id="retry">Try again</button>
          <button id="back">Back to menu</button>
        </div>
      </section>`, 120);
    on("retry", () => printTicket(id));
    on("back", renderMenu);
  }
}

const staff = {
  overlay: document.getElementById("staff"),

  async open() {
    this.overlay.hidden = false;
    const line = document.getElementById("staff-printer");
    line.textContent = "Checking printer…";
    try {
      const p = await api("/api/printer");
      const mode = p.dry_run ? "Dry run (printing off)." : "Printing on.";
      const queue = p.error ? p.error : `${p.printer}: ${p.problems.length ? p.problems.join(", ") : "ready"}.`;
      line.textContent = `${mode} ${queue}`;
    } catch (error) {
      line.textContent = error.message;
    }
  },

  close() {
    this.overlay.hidden = true;
  },
};

on("staff-close", () => staff.close());
window.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "m") {
    event.preventDefault();
    staff.open();
  }
  if (event.key === "Escape" && !staff.overlay.hidden) staff.close();
});

(async function init() {
  try {
    const data = await api("/api/labs");
    state.dishes = data.dishes;
    state.station = data.station;
    document.getElementById("fridge-tag").textContent =
      `Fridge ${state.station.fridge_number}${state.station.dry_run ? " · dry run" : ""}`;
    renderMenu();
  } catch (error) {
    show("error", `<section class="card center"><h1>Fridge is not ready</h1><pre class="detail">${escapeHtml(error.message)}</pre></section>`);
  }
})();
