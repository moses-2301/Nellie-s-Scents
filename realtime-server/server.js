const express = require('express');
const http = require('http');
const { Server } = require('socket.io');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

const server = http.createServer(app);
const io = new Server(server, {
    cors: {
        origin: '*',
        methods: ['GET', 'POST']
    }
});

io.on('connection', (socket) => {
    console.log(`Realtime client connected: ${socket.id}`);
    socket.on('disconnect', () => {
        console.log(`Realtime client disconnected: ${socket.id}`);
    });
});

app.post('/event', (req, res) => {
    const { type, payload } = req.body;
    if (!type) {
        return res.status(400).json({ error: 'Missing event type' });
    }
    io.emit('analyticsUpdate', { type, payload });
    return res.json({ success: true });
});

const port = process.env.PORT || 3001;
server.listen(port, () => {
    console.log(`Realtime analytics server running on http://localhost:${port}`);
});
