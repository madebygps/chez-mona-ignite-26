"use strict";

// Chez Mona launcher: one page, one screen at a time.
// Screens: scan, menu, intro, starting, start-error, explore, quiz, print, wrap.

const app = document.getElementById("app");
const progress = document.getElementById("progress");
const PROGRESS_FOR = { intro: "intro", starting: "intro", "start-error": "intro", explore: "explore", quiz: "quiz", print: "print", wrap: "print" };
const ORDER = ["intro", "explore", "quiz", "print"];
const SCAN_COOLDOWN_MS = 4000;

const state = {
  dishes: {},
  station: { idle_seconds: { default: 120, explore: 600, prompt: 30 } },
  screen: null,
  dish: null,
  question: 0,
  hints: [],
};

// ---------- helpers ----------

function escapeHtml(text) {
  return String(text).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

// Content uses a tiny Markdown subset: `code` and **bold**.
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

function openTab(url) {
  window.open(url, "_blank", "noopener");
}

function shuffle(items) {
  const copy = items.slice();
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function show(screen, html) {
  state.screen = screen;
  app.innerHTML = html;
  const current = PROGRESS_FOR[screen];
  progress.hidden = !current;
  progress.querySelectorAll("li").forEach((li) => {
    const index = ORDER.indexOf(li.dataset.step);
    const at = ORDER.indexOf(current);
    li.className = index < at ? "done" : index === at ? "current" : "";
  });
  idle.reset();
  window.scrollTo(0, 0);
}

function on(id, handler) {
  const el = document.getElementById(id);
  if (el) el.addEventListener("click", handler);
  return el;
}

// ---------- idle handling ----------

const idle = {
  timer: null,
  countdown: null,
  overlay: document.getElementById("idle"),
  count: document.getElementById("idle-count"),

  limitFor(screen) {
    const s = state.station.idle_seconds;
    if (screen === "explore") return s.explore;
    if (["intro", "start-error", "quiz", "print", "wrap"].includes(screen)) return s.default;
    return null; // scan, menu and starting never time out
  },

  reset() {
    clearTimeout(this.timer);
    if (!this.overlay.hidden) return; // only "Keep cooking" dismisses the prompt
    const limit = this.limitFor(state.screen);
    if (limit) this.timer = setTimeout(() => this.prompt(), limit * 1000);
  },

  prompt() {
    let left = state.station.idle_seconds.prompt;
    this.count.textContent = left;
    this.overlay.hidden = false;
    document.getElementById("idle-keep").focus();
    this.countdown = setInterval(() => {
      left -= 1;
      this.count.textContent = left;
      if (left <= 0) {
        this.dismiss();
        endLab();
      }
    }, 1000);
  },

  dismiss() {
    clearInterval(this.countdown);
    this.overlay.hidden = true;
    this.reset();
  },
};

on("idle-keep", () => idle.dismiss());
["pointerdown", "pointermove", "keydown", "wheel", "focus"].forEach((type) =>
  window.addEventListener(type, () => idle.reset(), { passive: true })
);

// Ends whatever the guest started and goes back to Scan. Repeated taps while
// cleanup is running (it can take a few seconds for VS Code) share one request.
let ending = null;
function endLab() {
  if (!ending) {
    ending = (async () => {
      try {
        await api("/api/session/end", {});
      } catch (error) {
        console.warn("Cleanup failed:", error);
      }
      ending = null;
      renderScan();
    })();
  }
  return ending;
}

// ---------- Scan ----------

const scanner = {
  stream: null,
  video: null,
  canvas: document.createElement("canvas"),
  running: false,
  generation: 0,
  lastCode: null,
  lastAt: 0,

  // Each start or stop bumps the generation, so a start that is still waiting
  // for the camera gives up instead of leaving a second stream running.
  async start(video, message) {
    const generation = ++this.generation;
    this.video = video;
    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
    } catch (error) {
      if (generation !== this.generation) return;
      message.textContent = "Camera unavailable. Tap Manually select a lab instead to pick a dish.";
      message.hidden = false;
      return;
    }
    if (generation !== this.generation || state.screen !== "scan") {
      stream.getTracks().forEach((track) => track.stop());
      return;
    }
    this.stream = stream;
    video.srcObject = stream;
    await video.play().catch(() => {});
    if (generation !== this.generation) return;
    this.running = true;
    this.tick(generation);
  },

  stop() {
    this.generation++;
    this.running = false;
    if (this.stream) this.stream.getTracks().forEach((track) => track.stop());
    this.stream = null;
  },

  tick(generation) {
    if (!this.running || generation !== this.generation) return;
    const video = this.video;
    if (video.readyState >= 2 && video.videoWidth) {
      const scale = Math.min(1, 960 / video.videoWidth);
      const w = Math.round(video.videoWidth * scale);
      const h = Math.round(video.videoHeight * scale);
      this.canvas.width = w;
      this.canvas.height = h;
      const ctx = this.canvas.getContext("2d", { willReadFrequently: true });
      ctx.drawImage(video, 0, 0, w, h);
      const result = jsQR(ctx.getImageData(0, 0, w, h).data, w, h, { inversionAttempts: "attemptBoth" });
      if (result && result.data) this.found(result.data);
    }
    if (this.running) setTimeout(() => requestAnimationFrame(() => this.tick(generation)), 120);
  },

  found(raw) {
    const code = raw.trim().toLowerCase().replace(/[\s_]+/g, "-");
    const now = Date.now();
    if (code === this.lastCode && now - this.lastAt < SCAN_COOLDOWN_MS) return;
    this.lastCode = code;
    this.lastAt = now;
    if (state.dishes[code]) {
      this.stop();
      renderIntro(code);
    } else {
      const notice = document.getElementById("scan-notice");
      if (notice) notice.textContent = "That's not a Chez Mona ticket. Try another one.";
    }
  },
};

function renderScan() {
  scanner.stop();
  state.dish = null;
  // Keep the last ticket from restarting a lab right after "Next guest".
  scanner.lastAt = Date.now();
  show("scan", `
    <section class="scan">
      <p class="eyebrow">Welcome to Chez Mona</p>
      <h1>Scan your ticket</h1>
      <p class="lede">Hold the QR code on your fridge ticket up to the camera.</p>
      <div class="camera">
        <video id="video" muted playsinline></video>
        <div class="frame"></div>
        <div class="camera-msg" id="camera-msg" hidden></div>
      </div>
      <button id="choose-lab">Manually select a lab instead</button>
      <p class="notice" id="scan-notice"></p>
    </section>`);
  on("choose-lab", renderMenu);
  scanner.start(document.getElementById("video"), document.getElementById("camera-msg"));
}

function renderMenu() {
  scanner.stop();
  show("menu", `
    <section class="menu">
      <p class="eyebrow">Today's menu</p>
      <h1>Choose a lab</h1>
      <p class="lede">Choose a dish based on what you'd like to learn.<br>Each takes about 5 minutes.</p>
      <div class="menu-grid">
        ${Object.values(state.dishes).map((d) => `
          <button class="menu-item" data-dish="${escapeHtml(d.id)}">
            <span class="menu-dish">${escapeHtml(d.dish)}</span>
            <span class="menu-lab">${escapeHtml(d.lab)}</span>
            <span class="menu-learn">${fmt(d.pitch)}</span>
          </button>`).join("")}
      </div>
      <div class="row">
        <button id="back-to-scan">Scan a ticket instead</button>
      </div>
    </section>`);
  app.querySelectorAll(".menu-item").forEach((b) =>
    b.addEventListener("click", () => renderIntro(b.dataset.dish))
  );
  on("back-to-scan", renderScan);
}

// ---------- Intro and start ----------

function renderIntro(id) {
  scanner.stop();
  const dish = state.dishes[id];
  state.dish = dish;
  state.question = 0;
  show("intro", `
    <section class="card intro">
      <p class="eyebrow">${escapeHtml(dish.lab)}</p>
      <h1>${escapeHtml(dish.dish)}</h1>
      <p class="confirm-meta">${dish.uses.map(escapeHtml).join(" · ")}</p>
      <div class="confirm-about">
        <p class="confirm-label">You'll learn</p>
        <ul>${dish.about.map((point) => `<li>${fmt(point)}</li>`).join("")}</ul>
      </div>
      <div class="row">
        <button class="primary" id="start">Start lab</button>
        <button class="link" id="back">Not my dish</button>
      </div>
    </section>`);
  on("start", startLab);
  on("back", endLab);
}

async function startLab() {
  const dish = state.dish;
  const start = dish.start;
  // Open tabs inside the click so the browser does not block the pop-up.
  if (start.type === "open_url") openTab(start.url);
  if (start.type === "sdk") {
    show("starting", `
      <section class="card center">
        <h2>Preparing your kitchen…</h2>
        <p class="lede">Copying the starter for you.</p>
      </section>`);
  }
  try {
    await api("/api/session/start", { dish: dish.id });
    renderExplore();
  } catch (error) {
    show("start-error", `
      <section class="card center">
        <h2 class="status-error">Something went wrong in the kitchen</h2>
        <p class="lede">Please ask a chef for help.</p>
        <pre class="detail">${escapeHtml(error.message)}</pre>
        <div class="row" style="justify-content:center">
          <button class="primary" id="retry">Try again</button>
          <button id="back">Back to scan</button>
        </div>
      </section>`);
    on("retry", startLab);
    on("back", endLab);
  }
}

// ---------- Explore ----------

function stepHtml(step, index) {
  const body = step.html
    ? `<div class="concept">${step.html}</div>`
    : `<div class="step-title">${fmt(step.text)}</div>`;
  const stepBody = step.body ? `<p class="step-body">${fmt(step.body)}</p>` : "";
  const image = step.image
    ? `<img class="step-image" src="/${escapeHtml(step.image)}" alt="${escapeHtml(step.alt)}">`
    : "";
  const prompt = step.prompt
    ? `<div class="step-prompt"><code>${escapeHtml(step.prompt)}</code><button data-copy="${index}">Copy</button></div>`
    : "";
  const details = step.details
    ? `<ul class="step-details">${step.details.map((d) => `<li>${fmt(d)}</li>`).join("")}</ul>`
    : "";
  const action = step.action
    ? `<div class="step-action"><button data-step="${index}">${escapeHtml(step.action.label)}</button><span class="muted small" id="action-msg-${index}"></span></div>`
    : "";
  return `<li><div class="card">${body}${stepBody}${image}${prompt}${details}${action}</div></li>`;
}

function renderExplore() {
  const dish = state.dish;
  show("explore", `
    <section>
      <p class="eyebrow">${escapeHtml(dish.dish)} · ${escapeHtml(dish.lab)}</p>
      <h2>Let's cook</h2>
      <ol class="steps">${dish.steps.map(stepHtml).join("")}</ol>
      <div class="row">
        <button class="primary" id="ready">I'm ready for the quiz</button>
      </div>
    </section>`);
  app.querySelectorAll(".concept a").forEach((a) => {
    a.target = "_blank";
    a.rel = "noopener";
  });
  app.querySelectorAll("button[data-step]").forEach((button) => {
    button.addEventListener("click", () => runAction(Number(button.dataset.step), button));
  });
  app.querySelectorAll("button[data-copy]").forEach((button) => {
    button.addEventListener("click", () => copyPrompt(dish.steps[Number(button.dataset.copy)].prompt, button));
  });
  on("ready", () => renderQuiz(0));
}

async function copyPrompt(text, button) {
  try {
    await navigator.clipboard.writeText(text);
    button.textContent = "Copied";
  } catch {
    getSelection().selectAllChildren(button.previousElementSibling);
    button.textContent = "Press Ctrl+C";
  }
  setTimeout(() => (button.textContent = "Copy"), 2000);
}

async function runAction(index, button) {
  const action = state.dish.steps[index].action;
  const message = document.getElementById(`action-msg-${index}`);
  if (action.type === "open_url") return openTab(action.url);
  if (action.type === "open_vscode") {
    button.disabled = true;
    message.textContent = "Opening VS Code…";
    try {
      await api("/api/session/open-vscode", {});
      message.textContent = "VS Code is open.";
    } catch (error) {
      message.textContent = error.message;
    } finally {
      button.disabled = false;
    }
  }
}

// ---------- Quiz ----------

function renderQuiz(index) {
  const dish = state.dish;
  const q = dish.quiz[index];
  state.question = index;
  if (index === 0) state.hints = dish.quiz.map(() => 0);
  const choices = shuffle([q.answer, ...q.others]);
  show("quiz", `
    <section class="card">
      <p class="eyebrow">Question ${index + 1} of ${dish.quiz.length}</p>
      <h2>${fmt(q.question)}</h2>
      <div class="choices">
        ${choices.map((c, i) => `<button class="choice" data-i="${i}">${fmt(c)}</button>`).join("")}
      </div>
      <div id="hint"></div>
    </section>`);
  app.querySelectorAll(".choice").forEach((button) => {
    button.addEventListener("click", () => {
      const picked = choices[Number(button.dataset.i)];
      if (picked === q.answer) {
        button.classList.add("right");
        app.querySelectorAll(".choice").forEach((b) => (b.disabled = true));
        document.getElementById("hint").innerHTML = `<p class="status-ok"><strong>Correct!</strong></p>`;
        setTimeout(() => (index + 1 < dish.quiz.length ? renderQuiz(index + 1) : renderWrap()), 900);
      } else {
        button.classList.add("wrong");
        button.disabled = true;
        state.hints[index] += 1;
        document.getElementById("hint").innerHTML = `<div class="hint"><strong>Not quite.</strong> ${fmt(q.hint)}</div>`;
      }
    });
  });
}

// ---------- Print ----------

async function renderPrint() {
  const dish = state.dish;
  show("print", `
    <section class="card center">
      <p class="eyebrow">Well done</p>
      <h2>Printing your receipt…</h2>
    </section>`);
  try {
    await api("/api/print", { dish: dish.id, hints: state.hints });
    show("print", `
      <section class="card center">
        <p class="eyebrow">Thanks for cooking with us</p>
        <h2 class="status-ok">Your receipt is on its way</h2>
        <p class="lede">Pick it up from the printer.</p>
        <div class="row" style="justify-content:center">
          <button class="primary" id="next">Next guest</button>
        </div>
      </section>`);
    on("next", endLab);
  } catch (error) {
    show("print", `
      <section class="card center">
        <h2 class="status-error">The receipt did not print</h2>
        <p class="lede">Please ask a chef. You still finished the lab!</p>
        <pre class="detail">${escapeHtml(error.message)}</pre>
        <div class="row" style="justify-content:center">
          <button class="primary" id="next">Next guest</button>
          <button id="again">Staff: print again</button>
        </div>
      </section>`);
    on("next", endLab);
    on("again", renderPrint);
  }
}

// ---------- Wrap up ----------

async function renderWrap() {
  const dish = state.dish;
  const sdk = dish.start.type === "sdk";
  show("wrap", `
    <section class="card">
      <p class="eyebrow">Well done</p>
      <h2>Clean up before your receipt</h2>
      <ul class="step-details">${dish.wrap_up.map((w) => `<li>${fmt(w)}</li>`).join("")}</ul>
      <p class="muted" id="cleanup">${sdk ? "Cleaning up…" : ""}</p>
      <div class="row">
        <button class="primary" id="next">Print my receipt</button>
      </div>
    </section>`);
  on("next", renderPrint);
  api("/api/complete", { dish: dish.id }).catch((error) => console.warn("Could not record completion:", error));
  if (sdk) {
    const cleanup = document.getElementById("cleanup");
    try {
      const result = await api("/api/session/end", {});
      const notes = [];
      if (result.window_still_open) notes.push("Please close the VS Code window.");
      if (result.ended && !result.deleted) notes.push("Staff: the starter folder could not be deleted yet; it is removed on the next start.");
      cleanup.textContent = notes.length ? notes.join(" ") : "All clean.";
    } catch (error) {
      cleanup.textContent = `Staff: cleanup failed. ${error.message}`;
    }
  }
}

// ---------- Staff panel ----------

const staff = {
  overlay: document.getElementById("staff"),

  async open() {
    this.overlay.hidden = false;
    const list = document.getElementById("staff-dishes");
    list.innerHTML = Object.values(state.dishes)
      .map((d) => `<button data-dish="${escapeHtml(d.id)}">${escapeHtml(d.dish)}<br><span class="small muted">${escapeHtml(d.lab)}</span></button>`)
      .join("");
    list.querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", async () => {
        this.close();
        await api("/api/session/end", {}).catch(() => {});
        renderIntro(b.dataset.dish);
      })
    );
    const line = document.getElementById("staff-printer");
    line.textContent = "Checking printer…";
    this.showStats();
    try {
      const p = await api("/api/printer");
      line.textContent = p.error ? p.error : `${p.printer}: ${p.problems.length ? p.problems.join(", ") : "ready"}.`;
    } catch (error) {
      line.textContent = error.message;
    }
  },

  close() {
    this.overlay.hidden = true;
  },

  async showStats() {
    const box = document.getElementById("staff-stats");
    box.textContent = "Loading today's labs…";
    try {
      const s = await api("/api/stats");
      box.innerHTML = `
        <table class="stats">
          <thead><tr><th>Today</th><th>Started</th><th>Completed</th><th>Receipts</th></tr></thead>
          <tbody>${s.labs.map((l) => `<tr><td>${escapeHtml(l.dish)}</td><td>${l.started}</td><td>${l.completed}</td><td>${l.receipt}</td></tr>`).join("")}</tbody>
        </table>`;
    } catch (error) {
      box.textContent = error.message;
    }
  },
};

on("staff-close", () => staff.close());
on("staff-scan", () => {
  staff.close();
  endLab();
});
window.addEventListener("keydown", (event) => {
  if (event.ctrlKey && event.shiftKey && event.key.toLowerCase() === "m") {
    event.preventDefault();
    staff.open();
  }
  if (event.key === "Escape" && !staff.overlay.hidden) staff.close();
});

// Touch fallback: hold the logo for 3 seconds.
(() => {
  let holdTimer = null;
  const brand = document.getElementById("brand");
  brand.addEventListener("pointerdown", () => (holdTimer = setTimeout(() => staff.open(), 3000)));
  ["pointerup", "pointerleave", "pointercancel"].forEach((t) => brand.addEventListener(t, () => clearTimeout(holdTimer)));
})();

// ---------- boot ----------

(async () => {
  try {
    const data = await api("/api/labs");
    data.dishes.forEach((d) => (state.dishes[d.id] = d));
    state.station = data.station;
    await endLab();
  } catch (error) {
    app.innerHTML = `<h2 class="status-error">The launcher could not load</h2><pre class="detail">${escapeHtml(error.message)}</pre>`;
  }
})();
