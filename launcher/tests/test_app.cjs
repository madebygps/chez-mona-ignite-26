const assert = require("node:assert/strict");
const { readFileSync } = require("node:fs");
const { join } = require("node:path");
const { test } = require("node:test");
const vm = require("node:vm");

const source = readFileSync(join(__dirname, "..", "static", "app.js"), "utf8");
const content = JSON.parse(readFileSync(join(__dirname, "..", "content", "labs.json"), "utf8"));
const settle = () => new Promise(setImmediate);

async function launcher(getUserMedia = async () => ({ getTracks: () => [] })) {
  const elements = new Map();
  function element() {
    return {
      hidden: true,
      innerHTML: "",
      dataset: {},
      handlers: {},
      addEventListener(type, handler) { this.handlers[type] = handler; },
      querySelectorAll(selector) {
        if (selector !== ".menu-item") return [];
        if (this.menuHTML !== this.innerHTML) {
          this.menuHTML = this.innerHTML;
          this.menuButtons = [...this.innerHTML.matchAll(/data-dish="([^"]+)"/g)].map((match) => {
            const button = element();
            button.dataset.dish = match[1];
            return button;
          });
        }
        return this.menuButtons;
      },
      play: async () => {},
    };
  }
  const requests = [];
  const context = vm.createContext({
    document: {
      getElementById(id) {
        if (!elements.has(id)) elements.set(id, element());
        return elements.get(id);
      },
      createElement: element,
    },
    window: { addEventListener() {}, scrollTo() {} },
    navigator: { mediaDevices: { getUserMedia } },
    fetch: async (path) => {
      requests.push(path);
      return {
        ok: true,
        json: async () => path === "/api/labs"
          ? { dishes: content.dishes, station: { idle_seconds: { default: 120, explore: 600, prompt: 30 } } }
          : {},
      };
    },
    console,
    setTimeout() {},
    clearTimeout() {},
    setInterval() {},
    clearInterval() {},
  });
  vm.runInContext(source, context);
  await settle();
  return {
    elements,
    requests,
    run: (code) => vm.runInContext(code, context),
    click: (id) => elements.get(id).handlers.click(),
  };
}

test("visible picker lists every lab and opens the same intro as scanning", async () => {
  const page = await launcher();
  assert.match(page.elements.get("app").innerHTML, /<button id="choose-lab">Manually select a lab instead/);
  const requestsBefore = page.requests.length;
  for (const dish of content.dishes) {
    page.click("choose-lab");
    assert.equal(page.run("state.screen"), "menu");
    assert.equal(page.run("progress.hidden"), true);
    const menu = page.elements.get("app");
    assert.equal(menu.querySelectorAll(".menu-item").length, content.dishes.length);
    assert.match(menu.innerHTML, /Choose a dish based on what you/);
    page.run(`
      app.querySelectorAll(".menu-item")
        .find((button) => button.dataset.dish === ${JSON.stringify(dish.id)})
        .handlers.click();
    `);
    assert.equal(page.run("state.screen"), "intro");
    assert.equal(page.run("state.dish.id"), dish.id);
    const manualIntro = menu.innerHTML;
    assert.match(manualIntro, /You'll learn/);
    assert.equal((manualIntro.match(/<li>/g) || []).length, dish.about.length);
    page.run(`renderScan(); scanner.found(${JSON.stringify(dish.id)});`);
    assert.equal(menu.innerHTML, manualIntro);
    page.run("renderScan()");
  }
  assert.equal(page.requests.length, requestsBefore, "selection must not start a session or print a ticket");
});

test("manual selection stops the camera and returning to scan restarts it", async () => {
  let starts = 0;
  let stops = 0;
  const page = await launcher(async () => {
    starts++;
    return { getTracks: () => [{ stop() { stops++; } }] };
  });
  assert.equal(starts, 1);
  page.click("choose-lab");
  assert.equal(stops, 1);
  assert.equal(page.run("scanner.running"), false);
  page.click("back-to-scan");
  await settle();
  assert.equal(starts, 2);
  assert.equal(page.run("state.screen"), "scan");
  assert.equal(page.run("state.dish"), null);
});

test("a pending camera request is stopped after opening the picker", async () => {
  let resolveCamera;
  let stops = 0;
  const page = await launcher(() => new Promise((resolve) => { resolveCamera = resolve; }));
  page.click("choose-lab");
  resolveCamera({ getTracks: () => [{ stop() { stops++; } }] });
  await settle();
  assert.equal(stops, 1);
  assert.equal(page.run("state.screen"), "menu");
  assert.equal(page.run("scanner.running"), false);
});

test("camera failure points guests to the visible picker", async () => {
  const page = await launcher(async () => { throw new Error("Permission denied"); });
  const message = page.elements.get("camera-msg");
  assert.equal(message.hidden, false);
  assert.match(message.textContent, /Manually select a lab instead/);
  assert.doesNotMatch(message.textContent, /Ctrl|Staff/);
  page.click("choose-lab");
  assert.equal(page.run("state.screen"), "menu");
});

test("cleanup checklist gates the receipt and stamps the receipt rank", async () => {
  const page = await launcher();
  const dish = content.dishes.find((d) => d.start.type !== "sdk" && d.wrap_up.length);
  page.run(`state.dish = state.dishes[${JSON.stringify(dish.id)}]; state.hints = [1, 1]; renderWrap();`);
  await settle();
  const html = page.elements.get("app").innerHTML;
  assert.match(html, /Clean your station/);
  assert.match(html, /You earned<strong>Sous chef<\/strong>/);
  assert.match(html, /id="next" disabled>Check, please!/);
  dish.wrap_up.forEach((_, i) => page.click(`chore-${i}`));
  assert.equal(page.elements.get("next").disabled, false);
  page.click("chore-0");
  assert.equal(page.elements.get("next").disabled, true);
});

test("sdk cleanup ticks itself and opens the receipt", async () => {
  const page = await launcher();
  const dish = content.dishes.find((d) => d.start.type === "sdk");
  page.run(`state.dish = state.dishes[${JSON.stringify(dish.id)}]; state.hints = [0, 0]; renderWrap();`);
  await settle();
  assert.match(page.elements.get("app").innerHTML, /You earned<strong>Head chef<\/strong>/);
  assert.ok(page.requests.includes("/api/session/end"));
  assert.equal(page.elements.get("chore-0").className, "chore done");
  assert.equal(page.elements.get("chore-status-0").textContent, "Spotless");
  assert.equal(page.elements.get("next").disabled, false);
});
