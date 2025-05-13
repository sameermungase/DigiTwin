import express from 'express';
import expressWs from 'express-ws';
import path from 'path';
import { fileURLToPath } from 'url';
import WebSocket from 'ws';

const app = express();
expressWs(app);

// Serve the index.html page
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
app.use(express.static(path.join(__dirname, 'public')));

// WebSocket sets
const publishers = new Set();
const subscribers = new Set();

app.ws('/publish', (ws, req) => {
  publishers.add(ws);
  ws.on('close', () => publishers.delete(ws));
});

app.ws('/subscribe', (ws, req) => {
  subscribers.add(ws);
  ws.on('close', () => subscribers.delete(ws));
});

// Relay messages
publishers.forEach(pubWs => {
  pubWs.on('message', (msg) => {
    for (let sub of subscribers) {
      if (sub.readyState === sub.OPEN) {
        sub.send(msg);
      }
    }
  });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`✅ Server running on :${PORT}`));
