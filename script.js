const express = require('express');
const bodyParser = require('body-parser');
const app = express();
const PORT = process.env.PORT || 3000;

// Store latest position data
let latestPositionData = null;
let positionHistory = [];
const MAX_HISTORY = 100; // Store last 100 position updates

// Middleware
app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

// API endpoint to get the latest position
app.get('/api/position', (req, res) => {
    res.json(latestPositionData);
});

// API endpoint to get position history
app.get('/api/history', (req, res) => {
    res.json(positionHistory);
});

// Endpoint to receive data from ESP32
app.post('/robot-position', (req, res) => {
    try {
        // Extract position data from request body
        const positionData = req.body;
        
        // Validate the incoming data
        if (!positionData || Object.keys(positionData).length === 0) {
            return res.status(400).send('Position data is required');
        }
        
        // Add timestamp
        const timestampedData = {
            ...positionData,
            timestamp: new Date().toISOString()
        };
        
        // Update latest position and add to history
        latestPositionData = timestampedData;
        positionHistory.unshift(timestampedData);
        
        // Keep history at max length
        if (positionHistory.length > MAX_HISTORY) {
            positionHistory = positionHistory.slice(0, MAX_HISTORY);
        }
        
        console.log('Received position data:', timestampedData);
        
        // Respond to ESP32
        res.status(200).json({ 
            status: 'success', 
            message: 'Position data received'
        });
    } catch (error) {
        console.error('Error processing position data:', error);
        res.status(500).json({ 
            status: 'error', 
            message: 'Error processing position data'
        });
    }
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});