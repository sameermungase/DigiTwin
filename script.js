const express = require('express');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 3000;

// Middleware to parse JSON data
app.use(bodyParser.json());

// Root route to handle GET requests
app.get('/', (req, res) => {
    res.send('Server is running and ready to receive data.');
});

// Endpoint to receive data from ESP32
app.post('/robot-position', (req, res) => {
    const { position } = req.body;

    if (!position) {
        return res.status(400).send('Position data is required');
    }

    console.log('Received position data:', position);

    // Respond to ESP32
    res.status(200).send('Position data received');
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});