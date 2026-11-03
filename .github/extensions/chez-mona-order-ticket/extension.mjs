import { createCanvas, CanvasError, joinSession } from '@github/copilot-sdk/extension';
import { createOrderTicketCanvas } from './canvas.mjs';

let session;
const { canvas, close } = createOrderTicketCanvas({
  createCanvas,
  CanvasError,
  workspacePath: () => session?.workspacePath,
  sendPrompt: prompt => {
    if (!session) throw new Error('Session is not ready yet.');
    return session.send({ prompt });
  }
});

session = await joinSession({
  canvases: [canvas],
  hooks: {
    onSessionEnd: close
  }
});

process.once('SIGTERM', () => {
  close().then(() => process.exit(0), error => {
    console.error('Could not close the order ticket:', error);
    process.exit(1);
  });
});
