import express from 'express';
import expressWs from 'express-ws';

const app = express();
expressWs(app);

const publishers = new Set();     // usually 1 device
const subscribers = new Set();    // 0..N viewers

// Publisher WebSocket endpoint (e.g., Jetson camera)
app.ws('/publish', (ws, req) => {
  console.log('[Publisher] connected');
  publishers.add(ws);

  ws.on('message', (msg) => {
    // Broadcast this frame to all subscribers
    for (const sub of subscribers) {
      if (sub.readyState === sub.OPEN) {
        sub.send(msg);
      }
    }
  });

  ws.on('close', () => {
    console.log('[Publisher] disconnected');
    publishers.delete(ws);
  });
});

// Subscriber WebSocket endpoint (e.g., browser client)
app.ws('/subscribe', (ws, req) => {
  console.log('[Subscriber] connected');
  subscribers.add(ws);

  ws.on('close', () => {
    console.log('[Subscriber] disconnected');
    subscribers.delete(ws);
  });
});

const PORT = process.env.PORT || 8080;
app.listen(PORT, () => {
  console.log(`✅ Server running at http://localhost:${PORT}`);
});
