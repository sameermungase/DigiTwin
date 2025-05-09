// server.js
import express from 'express';
import expressWs from 'express-ws';

const app = express();
expressWs(app);

const publishers = new Set();  // should be just one in your case
const subscribers = new Set();

// Endpoint for your Jetson to publish into:
app.ws('/publish', (ws, req) => {
  publishers.add(ws);
  ws.on('close', () => publishers.delete(ws));
});

// Endpoint for browsers to subscribe:
app.ws('/subscribe', (ws, req) => {
  subscribers.add(ws);
  ws.on('close', () => subscribers.delete(ws));
});

// Relay loop: whenever a publisher sends a frame, broadcast to subs
publishers.forEach(pubWs => {
  pubWs.on('message', (msg) => {
    // msg is a Buffer containing JPEG bytes
    for (let sub of subscribers) {
      if (sub.readyState === sub.OPEN) {
        sub.send(msg);
      }
    }
  });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => console.log(`Render server listening on :${PORT}`));
