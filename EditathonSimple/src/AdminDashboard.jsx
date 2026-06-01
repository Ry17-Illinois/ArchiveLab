import { useState, useEffect } from 'react';

function AdminDashboard({ user, onLogout }) {
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddUser, setShowAddUser] = useState(false);
  const [activeTab, setActiveTab] = useState('users'); // 'users' or 'export'
  const [newUser, setNewUser] = useState({
    username: '',
    password: '',
    name: '',
    assigned_start: '',
    assigned_end: ''
  });
  const [editingUser, setEditingUser] = useState(null);
  const [message, setMessage] = useState('');
  const [totalPages, setTotalPages] = useState(504);

  useEffect(() => {
    loadUsers();
  }, []);

  const loadUsers = async () => {
    try {
      const response = await fetch('/api/admin/users', {
        headers: {
          'X-Session-Id': user.sessionId
        }
      });
      const data = await response.json();
      if (data.success) {
        setUsers(data.users);
      }
      setLoading(false);
    } catch (err) {
      console.error('Failed to load users:', err);
      setLoading(false);
    }
  };

  const handleAddUser = async (e) => {
    e.preventDefault();
    try {
      const response = await fetch('/api/admin/users', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Id': user.sessionId
        },
        body: JSON.stringify(newUser)
      });
      const data = await response.json();
      if (data.success) {
        setMessage('User added successfully!');
        setShowAddUser(false);
        setNewUser({ username: '', password: '', name: '', assigned_start: '', assigned_end: '' });
        loadUsers();
        setTimeout(() => setMessage(''), 3000);
      } else {
        setMessage('Error: ' + data.message);
      }
    } catch (err) {
      setMessage('Error: ' + err.message);
    }
  };

  const handleUpdateUser = async (userId, updates) => {
    try {
      const response = await fetch(`/api/admin/users/${userId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Id': user.sessionId
        },
        body: JSON.stringify(updates)
      });
      const data = await response.json();
      if (data.success) {
        setMessage('User updated successfully!');
        setEditingUser(null);
        loadUsers();
        setTimeout(() => setMessage(''), 3000);
      } else {
        setMessage('Error: ' + data.message);
      }
    } catch (err) {
      setMessage('Error: ' + err.message);
    }
  };

  const handleDeleteUser = async (userId, username) => {
    if (!confirm(`Are you sure you want to delete user "${username}"?`)) {
      return;
    }
    try {
      const response = await fetch(`/api/admin/users/${userId}`, {
        method: 'DELETE',
        headers: {
          'X-Session-Id': user.sessionId
        }
      });
      const data = await response.json();
      if (data.success) {
        setMessage('User deleted successfully!');
        loadUsers();
        setTimeout(() => setMessage(''), 3000);
      } else {
        setMessage('Error: ' + data.message);
      }
    } catch (err) {
      setMessage('Error: ' + err.message);
    }
  };

  const handleAutoDistribute = async () => {
    const nonAdminUsers = users.filter(u => !u.is_admin);
    if (nonAdminUsers.length === 0) {
      setMessage('Error: No non-admin users to distribute pages to');
      return;
    }

    const pagesPerUser = Math.floor(totalPages / nonAdminUsers.length);
    
    if (pagesPerUser < 5) {
      if (!confirm(`Warning: Each user would get ${pagesPerUser} pages (less than 5). Continue anyway?`)) {
        return;
      }
    }

    if (!confirm(`This will redistribute all pages evenly among ${nonAdminUsers.length} users. Continue?`)) {
      return;
    }

    try {
      const response = await fetch('/api/admin/auto-distribute', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Id': user.sessionId
        },
        body: JSON.stringify({})
      });
      const data = await response.json();
      if (data.success) {
        setMessage(`${data.message} (${data.pagesPerUser} pages per user)`);
        loadUsers();
        setTimeout(() => setMessage(''), 5000);
      } else {
        setMessage('Error: ' + data.message);
      }
    } catch (err) {
      setMessage('Error: ' + err.message);
    }
  };

  const handleExport = async (format) => {
    try {
      const response = await fetch(`/api/admin/export?format=${format}`, {
        headers: {
          'X-Session-Id': user.sessionId
        }
      });
      
      if (format === 'json') {
        const data = await response.json();
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `editathon-export-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
        setMessage('JSON export downloaded successfully!');
      } else if (format === 'csv') {
        const text = await response.text();
        const blob = new Blob([text], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `editathon-export-${new Date().toISOString().split('T')[0]}.csv`;
        a.click();
        URL.revokeObjectURL(url);
        setMessage('CSV export downloaded successfully!');
      }
      
      setTimeout(() => setMessage(''), 3000);
    } catch (err) {
      setMessage('Error: ' + err.message);
    }
  };

  if (loading) {
    return <div className="admin-loading">Loading admin panel...</div>;
  }

  return (
    <div className="admin-dashboard">
      <header className="admin-header">
        <div>
          <h1>Admin Dashboard</h1>
          <p>Logged in as: {user.username}</p>
        </div>
        <button onClick={onLogout} className="btn-logout">
          Logout
        </button>
      </header>

      {message && (
        <div className="admin-message">
          {message}
        </div>
      )}

      <div className="admin-tabs">
        <button 
          className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
        >
          User Management
        </button>
        <button 
          className={`tab-btn ${activeTab === 'export' ? 'active' : ''}`}
          onClick={() => setActiveTab('export')}
        >
          Export Data
        </button>
      </div>

      <div className="admin-content">
        {activeTab === 'users' && (
          <>
            <div className="admin-actions">
              <button 
                onClick={() => setShowAddUser(!showAddUser)}
                className="btn-primary"
              >
                {showAddUser ? 'Cancel' : '+ Add New User'}
              </button>
              <button 
                onClick={handleAutoDistribute}
                className="btn-secondary"
              >
                🔄 Auto-Distribute Pages
              </button>
            </div>

        {showAddUser && (
          <div className="add-user-form">
            <h2>Add New User</h2>
            <form onSubmit={handleAddUser}>
              <div className="form-row">
                <div className="form-group">
                  <label>Username:</label>
                  <input
                    type="text"
                    value={newUser.username}
                    onChange={(e) => setNewUser({...newUser, username: e.target.value})}
                    required
                  />
                </div>
                <div className="form-group">
                  <label>Password:</label>
                  <input
                    type="password"
                    value={newUser.password}
                    onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                    required
                  />
                </div>
              </div>
              <div className="form-group">
                <label>Full Name:</label>
                <input
                  type="text"
                  value={newUser.name}
                  onChange={(e) => setNewUser({...newUser, name: e.target.value})}
                />
              </div>
              <div className="form-row">
                <div className="form-group">
                  <label>Assigned Start Page:</label>
                  <input
                    type="number"
                    value={newUser.assigned_start}
                    onChange={(e) => setNewUser({...newUser, assigned_start: e.target.value})}
                    required
                    min="1"
                  />
                </div>
                <div className="form-group">
                  <label>Assigned End Page:</label>
                  <input
                    type="number"
                    value={newUser.assigned_end}
                    onChange={(e) => setNewUser({...newUser, assigned_end: e.target.value})}
                    required
                    min="1"
                  />
                </div>
              </div>
              <button type="submit" className="btn-primary">Add User</button>
            </form>
          </div>
        )}

        <div className="users-table">
          <h2>Users ({users.length})</h2>
          <table>
            <thead>
              <tr>
                <th>Username</th>
                <th>Name</th>
                <th>Assigned Pages</th>
                <th>Progress</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(u => (
                <tr key={u.id} className={u.is_admin ? 'admin-row' : ''}>
                  <td>
                    {u.username}
                    {u.is_admin && <span className="admin-badge">ADMIN</span>}
                  </td>
                  <td>{u.name || '-'}</td>
                  <td>
                    {editingUser === u.id ? (
                      <div className="inline-edit">
                        <input
                          type="number"
                          defaultValue={u.assigned_start}
                          id={`start-${u.id}`}
                          style={{width: '60px'}}
                        />
                        {' - '}
                        <input
                          type="number"
                          defaultValue={u.assigned_end}
                          id={`end-${u.id}`}
                          style={{width: '60px'}}
                        />
                      </div>
                    ) : (
                      `${u.assigned_start} - ${u.assigned_end} (${u.assigned_end - u.assigned_start + 1} pages)`
                    )}
                  </td>
                  <td>
                    {u.completed || 0} / {u.total || 0}
                    {u.total > 0 && ` (${Math.round((u.completed / u.total) * 100)}%)`}
                  </td>
                  <td>{u.last_login ? new Date(u.last_login).toLocaleString() : 'Never'}</td>
                  <td>
                    {editingUser === u.id ? (
                      <>
                        <button
                          onClick={() => {
                            const start = parseInt(document.getElementById(`start-${u.id}`).value);
                            const end = parseInt(document.getElementById(`end-${u.id}`).value);
                            handleUpdateUser(u.id, { assigned_start: start, assigned_end: end });
                          }}
                          className="btn-small btn-success"
                        >
                          Save
                        </button>
                        <button
                          onClick={() => setEditingUser(null)}
                          className="btn-small"
                        >
                          Cancel
                        </button>
                      </>
                    ) : (
                      <>
                        <button
                          onClick={() => setEditingUser(u.id)}
                          className="btn-small"
                        >
                          Edit
                        </button>
                        {!u.is_admin && (
                          <button
                            onClick={() => handleDeleteUser(u.id, u.username)}
                            className="btn-small btn-danger"
                          >
                            Delete
                          </button>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
          </>
        )}

        {activeTab === 'export' && (
          <div className="export-panel">
            <h2>Export Editathon Data</h2>
            <p className="export-description">
              Export all completed edits, transcriptions, and validations from the editathon.
            </p>

            <div className="export-options">
              <div className="export-option">
                <h3>JSON Export</h3>
                <p>Complete structured data with all edits, metadata validations, and entity validations. Best for programmatic processing.</p>
                <button 
                  onClick={() => handleExport('json')}
                  className="btn-export"
                >
                  📥 Download JSON
                </button>
              </div>

              <div className="export-option">
                <h3>CSV Export</h3>
                <p>Spreadsheet-friendly format with page-level transcriptions and validation summaries. Best for analysis in Excel or Google Sheets.</p>
                <button 
                  onClick={() => handleExport('csv')}
                  className="btn-export"
                >
                  📥 Download CSV
                </button>
              </div>
            </div>

            <div className="export-info">
              <h3>Export Contents</h3>
              <ul>
                <li>Human-reviewed transcriptions (ground truth selections)</li>
                <li>Metadata field validations (approved/rejected/removed)</li>
                <li>Named entity validations (approved/rejected)</li>
                <li>Editor information and timestamps</li>
                <li>Completion status for each page</li>
              </ul>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default AdminDashboard;
