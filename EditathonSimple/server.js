const express = require('express');
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');
const app = express();

app.use(express.static(path.join(__dirname, 'dist')));
app.use(express.json());

// Serve data files
app.use('/data', express.static(path.join(__dirname, 'data')));

// Simple session storage (in-memory)
const sessions = {};

// Hash password for comparison
function hashPassword(password) {
  return crypto.createHash('sha256').update(password).digest('hex');
}

// Login endpoint
app.post('/api/login', (req, res) => {
  const { username, password } = req.body;
  
  try {
    const usersFile = path.join(__dirname, 'users.json');
    const users = JSON.parse(fs.readFileSync(usersFile, 'utf8'));
    
    if (users[username] && users[username].password === hashPassword(password)) {
      const sessionId = crypto.randomBytes(32).toString('hex');
      sessions[sessionId] = {
        username,
        assigned_pages: users[username].assigned_pages
      };
      
      res.json({
        success: true,
        sessionId,
        username,
        assigned_pages: users[username].assigned_pages
      });
    } else {
      res.status(401).json({ success: false, message: 'Invalid credentials' });
    }
  } catch (err) {
    res.status(500).json({ success: false, message: 'Server error' });
  }
});

// Verify session middleware
function verifySession(req, res, next) {
  const sessionId = req.headers['x-session-id'];
  if (sessionId && sessions[sessionId]) {
    req.session = sessions[sessionId];
    next();
  } else {
    res.status(401).json({ success: false, message: 'Unauthorized' });
  }
}

// API endpoint to save edits (with session check)
app.post('/api/save', verifySession, (req, res) => {
  const editsDir = path.join(__dirname, 'edits');
  
  if (!fs.existsSync(editsDir)) {
    fs.mkdirSync(editsDir, { recursive: true });
  }
  
  const { page_id, data } = req.body;
  const username = req.session.username;
  const filename = `${username}_${page_id}.json`;
  
  fs.writeFileSync(
    path.join(editsDir, filename),
    JSON.stringify({ ...data, username, timestamp: new Date().toISOString() }, null, 2)
  );
  
  res.json({ success: true });
});

app.get('*', (req, res) => {
  res.sendFile(path.join(__dirname, 'dist', 'index.html'));
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
