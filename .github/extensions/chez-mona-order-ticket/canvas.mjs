import path from 'node:path';
import { TicketStore, startTicketServer, menu } from './ticket.mjs';

const noInput = { type: 'object', properties: {}, additionalProperties: false };
const dishInput = {
  type: 'object',
  properties: {
    dishId: { type: 'string', enum: menu.map(dish => dish.id) },
    quantity: { type: 'integer', minimum: 1, maximum: 20, default: 1 }
  },
  required: ['dishId'],
  additionalProperties: false
};

export function createOrderTicketCanvas({ createCanvas, CanvasError, workspacePath, sendPrompt }) {
  const sessions = new Map();
  async function entry(ctx) {
    let pending = sessions.get(ctx.sessionId);
    if (!pending) {
      pending = (async () => {
        const workspace = workspacePath();
        if (!workspace) throw new CanvasError('workspace_unavailable', 'Session workspace is unavailable. Reopen this session before opening the ticket.');
        const store = new TicketStore(path.join(workspace, 'artifacts', 'chez-mona-order-ticket.json'));
        await store.load();
        return { store, server: null, panels: new Set() };
      })();
      sessions.set(ctx.sessionId, pending);
      pending.catch(() => sessions.delete(ctx.sessionId));
    }
    return pending;
  }

  const action = (name, description, inputSchema) => ({
    name, description, inputSchema,
    handler: async ctx => {
      try {
        const current = await entry(ctx);
        return await current.store.apply(name, ctx.input ?? {});
      } catch (error) {
        throw new CanvasError('ticket_action_failed', error.message);
      }
    }
  });

  const canvas = createCanvas({
    id: 'chez-mona-order-ticket',
    displayName: 'Chez Mona Order Ticket',
    description: 'An interactive Chez Mona order ticket: guests and the agent can add and remove dishes together.',
    inputSchema: noInput,
    actions: [
      action('get_ticket', 'Read the current order ticket and available menu dish IDs.', noInput),
      action('add_dish', 'Add a menu dish to the order ticket; quantity defaults to one.', dishInput),
      action('remove_dish', 'Remove a quantity of a dish from the ticket; quantity defaults to one.', dishInput),
      action('clear_ticket', 'Remove all dishes from the order ticket.', noInput)
    ],
    open: async ctx => {
      const current = await entry(ctx);
      current.server ??= startTicketServer(current.store, sendPrompt);
      current.panels.add(ctx.instanceId);
      try {
        return { title: 'Chez Mona Order Ticket', url: (await current.server).url };
      } catch (error) {
        current.server = null;
        throw new CanvasError('ticket_open_failed', error.message);
      }
    },
    onClose: async ctx => {
      const pending = sessions.get(ctx.sessionId);
      if (!pending) return;
      const current = await pending;
      current.panels.delete(ctx.instanceId);
      if (!current.panels.size && current.server) {
        const server = await current.server;
        current.server = null;
        await server.close();
      }
    }
  });

  async function close() {
    await Promise.all([...sessions.values()].map(async pending => {
      const current = await pending;
      if (current.server) await (await current.server).close();
    }));
    sessions.clear();
  }
  return { canvas, close };
}
