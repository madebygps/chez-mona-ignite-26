import { createServer } from 'node:http';
import { randomBytes, randomUUID } from 'node:crypto';
import { mkdir, readFile, writeFile, rename, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { EventEmitter } from 'node:events';

export const menu = [
  { id: 'omelette', name: 'Omelette', lab: 'Canvas 101' },
  { id: 'fried-chicken', name: 'Fried Chicken', lab: 'Copilot SDK' },
  { id: 'soup', name: 'Soup', lab: 'Agentic Workflows' },
  { id: 'dip', name: 'Dip', lab: 'PR review' }
];
const assets = path.join(path.dirname(fileURLToPath(import.meta.url)), 'public');
// The panel can only send these fixed lesson prompts to chat, never arbitrary text.
export const lessonPrompts = {
  'add-soup': 'Add two Soups to my ticket.'
};

export class TicketStore extends EventEmitter {
  constructor(file) {
    super();
    this.file = file;
    this.state = null;
    this.queue = Promise.resolve();
  }

  async load() {
    await mkdir(path.dirname(this.file), { recursive: true });
    try {
      this.state = JSON.parse(await readFile(this.file, 'utf8'));
    } catch (error) {
      if (error.code !== 'ENOENT') throw new Error(`Could not read ticket: ${error.message}`);
      this.state = { revision: 0, items: [] };
      await writeFile(this.file, JSON.stringify(this.state), { flag: 'wx' });
    }
    const state = this.state;
    if (!Number.isSafeInteger(state.revision) || state.revision < 0 || !Array.isArray(state.items) ||
        new Set(state.items.map(item => item.dishId)).size !== state.items.length ||
        state.items.some(item => !menu.some(dish => dish.id === item.dishId) ||
          !Number.isInteger(item.quantity) || item.quantity < 1 || item.quantity > 20)) {
      throw new Error('Stored ticket is invalid. Staff must inspect the session artifact; it has not been reset.');
    }
    return this.snapshot();
  }

  snapshot() {
    if (!this.state) throw new Error('Ticket has not been loaded.');
    return structuredClone({
      ...this.state,
      menu,
      items: this.state.items.map(item => ({ ...menu.find(dish => dish.id === item.dishId), ...item })),
      total: this.state.items.reduce((sum, item) => sum + item.quantity, 0)
    });
  }

  apply(action, input = {}) {
    const operation = this.queue.then(async () => {
      if (!['get_ticket', 'add_dish', 'remove_dish', 'clear_ticket'].includes(action)) throw new Error('Unknown ticket action.');
      if (!input || typeof input !== 'object' || Array.isArray(input)) throw new Error('Action input must be an object.');
      const changesDish = action === 'add_dish' || action === 'remove_dish';
      if (Object.keys(input).some(key => !(changesDish ? ['dishId', 'quantity'] : []).includes(key))) throw new Error('Unexpected ticket action field.');
      if (action === 'get_ticket') return this.snapshot();
      const next = structuredClone(this.state);
      if (action === 'clear_ticket') next.items = [];
      else {
        const quantity = input.quantity ?? 1;
        if (!menu.some(dish => dish.id === input.dishId)) throw new Error('Choose a dish from the menu.');
        if (!Number.isInteger(quantity) || quantity < 1 || quantity > 20) throw new Error('Quantity must be an integer from 1 to 20.');
        const item = next.items.find(item => item.dishId === input.dishId);
        if (action === 'add_dish') {
          if ((item?.quantity ?? 0) + quantity > 20) throw new Error('A dish can have at most 20 portions on this demo ticket.');
          if (item) item.quantity += quantity;
          else next.items.push({ dishId: input.dishId, quantity });
        } else {
          if (!item) throw new Error('That dish is not on the ticket.');
          if (quantity > item.quantity) throw new Error(`Only ${item.quantity} portion(s) of that dish are on the ticket.`);
          item.quantity -= quantity;
          next.items = next.items.filter(item => item.quantity > 0);
        }
      }
      next.revision++;
      const temporary = `${this.file}.${randomUUID()}.tmp`;
      try {
        await writeFile(temporary, JSON.stringify(next, null, 2), { flag: 'wx' });
        await rename(temporary, this.file);
      } catch (error) {
        await rm(temporary, { force: true });
        throw new Error(`Could not save ticket: ${error.message}`);
      }
      this.state = next;
      const snapshot = this.snapshot();
      this.emit('change', snapshot);
      return snapshot;
    });
    // Keep later actions usable after a rejected input; the caller still receives the rejection.
    this.queue = operation.catch(() => {});
    return operation;
  }
}

export async function startTicketServer(store, sendPrompt) {
  const token = randomBytes(32).toString('hex');
  const connections = new Set();
  const send = snapshot => {
    for (const response of connections) response.write(`data: ${JSON.stringify(snapshot)}\n\n`);
  };
  store.on('change', send);
  const server = createServer(async (req, res) => {
    res.setHeader('Cache-Control', 'no-store');
    res.setHeader('X-Content-Type-Options', 'nosniff');
    res.setHeader('Referrer-Policy', 'no-referrer');
    res.setHeader('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; base-uri 'none'; form-action 'none'");
    const reply = (status, data) => {
      res.writeHead(status, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify(data));
    };
    try {
      const origin = `http://127.0.0.1:${server.address().port}`;
      if (req.headers.host !== new URL(origin).host) return reply(403, { error: 'Use this canvas loopback address.' });
      const url = new URL(req.url, origin);
      if (req.method === 'GET' && ['/', '/app.js', '/style.css'].includes(url.pathname)) {
        if (url.pathname === '/' && url.searchParams.get('token') !== token) return reply(403, { error: 'Canvas token required.' });
        const filename = url.pathname === '/' ? 'index.html' : url.pathname.slice(1);
        const type = filename.endsWith('.html') ? 'text/html' : filename.endsWith('.js') ? 'text/javascript' : 'text/css';
        const content = await readFile(path.join(assets, filename));
        res.writeHead(200, { 'Content-Type': `${type}; charset=utf-8` });
        return res.end(content);
      }
      if (req.method === 'GET' && url.pathname === '/events') {
        if (url.searchParams.get('token') !== token) return reply(403, { error: 'Canvas token required.' });
        res.writeHead(200, { 'Content-Type': 'text/event-stream', Connection: 'keep-alive' });
        res.write(`data: ${JSON.stringify(store.snapshot())}\n\n`);
        connections.add(res);
        req.on('close', () => connections.delete(res));
        return;
      }
      if (req.method === 'POST' && (url.pathname === '/action' || url.pathname === '/prompt')) {
        if (req.headers.origin !== origin || req.headers['x-ticket-token'] !== token ||
            req.headers['content-type'] !== 'application/json') return reply(403, { error: 'Canvas request rejected. Reopen the canvas.' });
        let body = '';
        for await (const chunk of req) {
          body += chunk;
          if (Buffer.byteLength(body) > 2048) return reply(413, { error: 'Action input is too large.' });
        }
        let payload;
        try { payload = JSON.parse(body); } catch { return reply(400, { error: 'Invalid action JSON.' }); }
        if (url.pathname === '/prompt') {
          const prompt = Object.hasOwn(lessonPrompts, payload?.promptId) ? lessonPrompts[payload.promptId] : null;
          if (!prompt) return reply(400, { error: 'Unknown lesson prompt.' });
          if (!sendPrompt) return reply(503, { error: 'Sending to chat is unavailable.' });
          try { await sendPrompt(prompt); return reply(200, { sent: true }); }
          catch (error) { return reply(502, { error: `Could not send the prompt: ${error.message}` }); }
        }
        try { return reply(200, await store.apply(payload.action, payload.input)); }
        catch (error) { return reply(400, { error: error.message }); }
      }
      reply(404, { error: 'Not found.' });
    } catch (error) {
      console.error('Order ticket server:', error);
      if (!res.headersSent) reply(500, { error: error.message });
      else res.destroy(error);
    }
  });
  try {
    await new Promise((resolve, reject) => {
      server.once('error', reject);
      server.listen(0, '127.0.0.1', resolve);
    });
  } catch (error) {
    store.off('change', send);
    throw error;
  }
  return {
    url: `http://127.0.0.1:${server.address().port}/?token=${token}`,
    async close() {
      store.off('change', send);
      for (const response of connections) response.end();
      connections.clear();
      server.closeIdleConnections();
      await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()));
    }
  };
}
