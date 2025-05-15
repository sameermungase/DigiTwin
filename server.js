const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');
const { v4: uuidv4 } = require('uuid');

// Create Express app
const app = express();
const server = http.createServer(app);

// Set up WebSocket server
const wss = new WebSocket.Server({ server });

// Store connected clients
const clients = {
  jetson: null,
  laptop: null
};

// Serve static files if needed
app.use(express.static(path.join(__dirname, 'public')));

// Home route
app.get('/', (req, res) => {
  res.send('Jetson Nano Camera Relay Server');
});

// Health check route for Render
app.get('/health', (req, res) => {
  res.status(200).send('OK');
});

// WebSocket connection handler
wss.on('connection', (ws, req) => {
  const clientId = uuidv4();
  ws.id = clientId;
  
  console.log(`New client connected: ${clientId}`);
  
  // Handle messages from clients
  ws.on('message', (message) => {
    try {
      const data = JSON.parse(message);
      console.log(`Received message type: ${data.type} from ${clientId}`);
      
      // Handle client registration
      if (data.type === 'register') {
        if (data.client_type === 'jetson') {
          clients.jetson = ws;
          console.log('Jetson Nano registered');
        } else if (data.client_type === 'laptop') {
          clients.laptop = ws;
          console.log('Laptop client registered');
        }
      } 
      // Handle start capture command from laptop
      else if (data.type === 'start_capture') {
        if (clients.jetson && clients.jetson.readyState === WebSocket.OPEN) {
          clients.jetson.send(message);
          console.log(`Forwarded start_capture to Jetson: ${JSON.stringify(data)}`);
        } else {
          if (clients.laptop && clients.laptop.readyState === WebSocket.OPEN) {
            clients.laptop.send(JSON.stringify({
              type: 'error',
              message: 'Jetson Nano is not connected'
            }));
          }
          console.log('Failed to forward start_capture - Jetson not connected');
        }
      } 
      // Handle stop capture command from laptop
      else if (data.type === 'stop_capture') {
        if (clients.jetson && clients.jetson.readyState === WebSocket.OPEN) {
          clients.jetson.send(message);
          console.log('Forwarded stop_capture to Jetson');
        } else {
          if (clients.laptop && clients.laptop.readyState === WebSocket.OPEN) {
            clients.laptop.send(JSON.stringify({
              type: 'error',
              message: 'Jetson Nano is not connected'
            }));
          }
          console.log('Failed to forward stop_capture - Jetson not connected');
        }
      } 
      // Handle capture started status from Jetson
      else if (data.type === 'capture_started') {
        if (clients.laptop && clients.laptop.readyState === WebSocket.OPEN) {
          clients.laptop.send(message);
          console.log(`Forwarded capture_started to laptop: ${data.folder_name}`);
        }
      } 
      // Handle file transfer messages from Jetson to laptop
      else if (data.type === 'file_transfer_start' || 
               data.type === 'file_chunk' || 
               data.type === 'file_transfer_complete') {
        if (clients.laptop && clients.laptop.readyState === WebSocket.OPEN) {
          clients.laptop.send(message);
          
          // Log appropriate message depending on the transfer stage
          if (data.type === 'file_transfer_start') {
            console.log(`Started file transfer: ${data.folder_name}, size: ${(data.file_size/1024/1024).toFixed(2)} MB`);
          } else if (data.type === 'file_transfer_complete') {
            console.log(`Completed file transfer: ${data.folder_name}`);
          } else if (data.type === 'file_chunk') {
            // Only log occasional chunks to avoid flooding console
            if (data.chunk_id % 10 === 0 || data.is_last) {
              console.log(`Forwarded chunk ${data.chunk_id} for ${data.folder_name}`);
            }
          }
        } else {
          console.log('Failed to forward file transfer data - Laptop not connected');
          // Notify Jetson that laptop is disconnected
          if (clients.jetson && clients.jetson.readyState === WebSocket.OPEN) {
            clients.jetson.send(JSON.stringify({
              type: 'error',
              message: 'Laptop client is not connected'
            }));
          }
        }
      }
      
    } catch (error) {
      console.error('Error handling message:', error);
    }
  });
  
  // Handle client disconnection
  ws.on('close', () => {
    console.log(`Client disconnected: ${clientId}`);
    
    // Remove client from our registry
    if (clients.jetson === ws) {
      clients.jetson = null;
      console.log('Jetson Nano disconnected');
      
      // Notify laptop that Jetson disconnected
      if (clients.laptop && clients.laptop.readyState === WebSocket.OPEN) {
        clients.laptop.send(JSON.stringify({
          type: 'notification',
          message: 'Jetson Nano disconnected'
        }));
      }
    }
    
    if (clients.laptop === ws) {
      clients.laptop = null;
      console.log('Laptop client disconnected');
      
      // Notify Jetson that laptop disconnected
      if (clients.jetson && clients.jetson.readyState === WebSocket.OPEN) {
        clients.jetson.send(JSON.stringify({
          type: 'notification',
          message: 'Laptop client disconnected'
        }));
      }
    }
  });
  
  // Send initial connection acknowledgement
  ws.send(JSON.stringify({
    type: 'connection_established',
    message: 'Connected to Jetson Camera Relay Server'
  }));
});

// Handle WebSocket server errors
wss.on('error', (error) => {
  console.error('WebSocket Server Error:', error);
});

// Start the server
const PORT = process.env.PORT || 3000;
server.listen(PORT, () => {
  console.log(`Server listening on port ${PORT}`);
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down...');
  
  // Close all WebSocket connections
  wss.clients.forEach((client) => {
    if (client.readyState === WebSocket.OPEN) {
      client.close(1000, 'Server shutting down');
    }
  });
  
  // Close the HTTP server
  server.close(() => {
    console.log('Server closed');
    process.exit(0);
  });
  
  // Force exit if graceful shutdown fails
  setTimeout(() => {
    console.error('Forced shutdown');
    process.exit(1);
  }, 10000);
});
