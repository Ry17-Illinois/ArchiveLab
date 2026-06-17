import { useState, useEffect, useRef, useCallback } from 'react';
import Login from './Login';
import AdminDashboard from './AdminDashboard';

function App() {
  const [user, setUser] = useState(null);
  const [dataset, setDataset] = useState(null);
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [selectedOCR, setSelectedOCR] = useState('');
  const [baseModel, setBaseModel] = useState(''); // The model chosen as starting point
  const [transcription, setTranscription] = useState('');
  const [transcriptionEdited, setTranscriptionEdited] = useState(false);
  const [metadataValidations, setMetadataValidations] = useState({});
  const [entityValidations, setEntityValidations] = useState({});
  const [loading, setLoading] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  
  // Pan-zoom state
  const [scale, setScale] = useState(1);
  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const panStart = useRef({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const imageRef = useRef(null);

  const MIN_SCALE = 0.25;
  const MAX_SCALE = 5;
  const ZOOM_STEP = 0.1;

  // Reset pan-zoom when page changes
  const resetZoom = useCallback(() => {
    setScale(1);
    setPanX(0);
    setPanY(0);
  }, []);

  // Fit width: scale image to fill container width
  const fitWidth = useCallback(() => {
    if (!containerRef.current || !imageRef.current) return;
    const containerWidth = containerRef.current.clientWidth - 32; // account for padding
    const imageWidth = imageRef.current.naturalWidth;
    if (imageWidth > 0) {
      const newScale = containerWidth / imageWidth;
      setScale(Math.min(Math.max(newScale, MIN_SCALE), MAX_SCALE));
      setPanX(0);
      setPanY(0);
    }
  }, []);

  // Fit height: scale image to fill container height
  const fitHeight = useCallback(() => {
    if (!containerRef.current || !imageRef.current) return;
    const containerHeight = containerRef.current.clientHeight - 32;
    const imageHeight = imageRef.current.naturalHeight;
    if (imageHeight > 0) {
      const newScale = containerHeight / imageHeight;
      setScale(Math.min(Math.max(newScale, MIN_SCALE), MAX_SCALE));
      setPanX(0);
      setPanY(0);
    }
  }, []);

  // Wheel zoom centered on cursor
  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const container = containerRef.current;
    if (!container) return;

    const rect = container.getBoundingClientRect();
    // Cursor position relative to container
    const cursorX = e.clientX - rect.left;
    const cursorY = e.clientY - rect.top;

    // Point in image space under cursor before zoom
    const imgX = (cursorX - panX) / scale;
    const imgY = (cursorY - panY) / scale;

    // Calculate new scale
    const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP;
    const newScale = Math.min(Math.max(scale + delta * scale, MIN_SCALE), MAX_SCALE);

    // Adjust pan so the same image point stays under cursor
    const newPanX = cursorX - imgX * newScale;
    const newPanY = cursorY - imgY * newScale;

    setScale(newScale);
    setPanX(newPanX);
    setPanY(newPanY);
  }, [scale, panX, panY]);

  // Double-click to zoom in (or reset if already zoomed)
  const handleDoubleClick = useCallback((e) => {
    if (scale > 1.1) {
      resetZoom();
    } else {
      const container = containerRef.current;
      if (!container) return;

      const rect = container.getBoundingClientRect();
      const cursorX = e.clientX - rect.left;
      const cursorY = e.clientY - rect.top;

      const imgX = (cursorX - panX) / scale;
      const imgY = (cursorY - panY) / scale;

      const newScale = 2.5;
      const newPanX = cursorX - imgX * newScale;
      const newPanY = cursorY - imgY * newScale;

      setScale(newScale);
      setPanX(newPanX);
      setPanY(newPanY);
    }
  }, [scale, panX, panY, resetZoom]);

  // Drag to pan
  const handleMouseDown = useCallback((e) => {
    if (e.button !== 0) return; // left click only
    setIsDragging(true);
    dragStart.current = { x: e.clientX, y: e.clientY };
    panStart.current = { x: panX, y: panY };
    e.preventDefault();
  }, [panX, panY]);

  const handleMouseMove = useCallback((e) => {
    if (!isDragging) return;
    const dx = e.clientX - dragStart.current.x;
    const dy = e.clientY - dragStart.current.y;
    setPanX(panStart.current.x + dx);
    setPanY(panStart.current.y + dy);
  }, [isDragging]);

  const handleMouseUp = useCallback(() => {
    setIsDragging(false);
  }, []);

  // Attach wheel listener with passive: false to allow preventDefault
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.addEventListener('wheel', handleWheel, { passive: false });
    return () => container.removeEventListener('wheel', handleWheel);
  }, [handleWheel]);

  // Global mouse up/move for drag (in case mouse leaves container)
  useEffect(() => {
    if (isDragging) {
      window.addEventListener('mousemove', handleMouseMove);
      window.addEventListener('mouseup', handleMouseUp);
      return () => {
        window.removeEventListener('mousemove', handleMouseMove);
        window.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, handleMouseMove, handleMouseUp]);

  // Check for existing session
  useEffect(() => {
    const sessionId = localStorage.getItem('sessionId');
    const username = localStorage.getItem('username');
    const assigned_pages = localStorage.getItem('assigned_pages');
    const is_admin = localStorage.getItem('is_admin') === 'true';
    
    if (sessionId && username) {
      setUser({
        sessionId,
        username,
        assigned_pages: assigned_pages ? JSON.parse(assigned_pages) : null,
        is_admin
      });
    } else {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!user || user.is_admin) return;
    
    // Load dataset from database API
    fetch('/api/dataset', {
      headers: {
        'X-Session-Id': user.sessionId
      }
    })
      .then(res => {
        if (res.status === 401) {
          // Session invalid, clear and reload
          localStorage.clear();
          window.location.reload();
          return null;
        }
        return res.json();
      })
      .then(data => {
        if (!data) return; // Session was invalid
        
        setDataset(data);
        setLoading(false);
        
        if (data.pages && data.pages.length > 0) {
          const firstOCR = Object.keys(data.pages[0].ocr_versions)[0];
          setSelectedOCR(firstOCR);
          setTranscription(data.pages[0].ocr_versions[firstOCR] || '');
        }
      })
      .catch(err => {
        console.error('Failed to load dataset:', err);
        setLoading(false);
      });
  }, [user]);

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('sessionId');
    localStorage.removeItem('username');
    localStorage.removeItem('assigned_pages');
    localStorage.removeItem('is_admin');
    setUser(null);
    setDataset(null);
  };

  if (!user) {
    return <Login onLogin={handleLogin} />;
  }

  // Show admin dashboard for admin users
  if (user.is_admin) {
    return <AdminDashboard user={user} onLogout={handleLogout} />;
  }

  if (loading) {
    return <div style={{padding: '2rem'}}>Loading dataset...</div>;
  }

  if (!dataset || !dataset.pages || dataset.pages.length === 0) {
    return <div style={{padding: '2rem'}}>No pages found in dataset.</div>;
  }

  // Pages are already filtered by server to user's assignment
  const assignedPages = dataset.pages;

  if (assignedPages.length === 0) {
    return <div style={{padding: '2rem'}}>No pages assigned to you.</div>;
  }

  const currentPage = assignedPages[currentPageIndex];
  const ocrVersions = Object.keys(currentPage.ocr_versions);
  
  // Add Human-Reviewed to the list if user is editing or has edited
  const displayOCRVersions = [...ocrVersions];
  if (baseModel && !displayOCRVersions.includes('Human-Reviewed')) {
    displayOCRVersions.push('Human-Reviewed');
  }

  const handlePrevious = () => {
    if (currentPageIndex > 0) {
      const newIndex = currentPageIndex - 1;
      setCurrentPageIndex(newIndex);
      loadPageData(assignedPages[newIndex]);
    }
  };

  const handleNext = () => {
    if (currentPageIndex < assignedPages.length - 1) {
      const newIndex = currentPageIndex + 1;
      setCurrentPageIndex(newIndex);
      loadPageData(assignedPages[newIndex]);
    }
  };

  const loadPageData = (page) => {
    // Reset zoom when changing pages
    resetZoom();
    
    // Check if there's a human-reviewed version
    if (page.ocr_versions['Human-Reviewed']) {
      // Load the human-reviewed version
      setSelectedOCR('Human-Reviewed');
      setBaseModel(page.saved_state?.ocr_selected || '');
      setTranscription(page.ocr_versions['Human-Reviewed'] || '');
      setTranscriptionEdited(true);
      setMetadataValidations(page.saved_state?.metadata_validations || {});
      setEntityValidations(page.saved_state?.entity_validations || {});
    } else if (page.saved_state) {
      // Load saved state (base model selected but not yet edited)
      setSelectedOCR(page.saved_state.ocr_selected);
      setBaseModel(page.saved_state.ocr_selected);
      setTranscription(page.ocr_versions[page.saved_state.ocr_selected] || '');
      setTranscriptionEdited(false);
      setMetadataValidations(page.saved_state.metadata_validations || {});
      setEntityValidations(page.saved_state.entity_validations || {});
    } else {
      // Load fresh page with defaults
      const firstOCR = Object.keys(page.ocr_versions).filter(k => k !== 'Human-Reviewed')[0];
      setSelectedOCR(firstOCR);
      setBaseModel('');
      setTranscription(page.ocr_versions[firstOCR] || '');
      setTranscriptionEdited(false);
      setMetadataValidations({});
      setEntityValidations({});
    }
  };

  const handleOCRChange = (version) => {
    if (version === 'Human-Reviewed') {
      // Switch to Human-Reviewed view (shows current edits)
      setSelectedOCR('Human-Reviewed');
      // Keep the transcription as-is (it's already the edited version)
    } else {
      setSelectedOCR(version);
      setTranscription(currentPage.ocr_versions[version] || '');
      // If switching away from Human-Reviewed, clear the base model lock
      if (selectedOCR === 'Human-Reviewed') {
        setBaseModel('');
        setTranscriptionEdited(false);
      }
    }
  };

  const handleSetBaseModel = () => {
    if (selectedOCR && selectedOCR !== 'Human-Reviewed') {
      setBaseModel(selectedOCR);
      setTranscription(currentPage.ocr_versions[selectedOCR] || '');
      setTranscriptionEdited(false);
      // Automatically switch to Human-Reviewed view
      setSelectedOCR('Human-Reviewed');
    }
  };

  const handleUnlockBaseModel = () => {
    setBaseModel('');
    setTranscriptionEdited(false);
  };

  const handleTranscriptionChange = (e) => {
    setTranscription(e.target.value);
    setTranscriptionEdited(true);
  };

  const handleMetadataValidation = (field, status) => {
    setMetadataValidations(prev => ({
      ...prev,
      [field]: status
    }));
  };

  const handleEntityValidation = (entityId, status) => {
    setEntityValidations(prev => ({
      ...prev,
      [entityId]: status
    }));
  };

  const handleSave = async () => {
    const metadata_validations_array = Object.entries(metadataValidations).map(([field, status]) => ({
      field_name: field,
      original_value: currentPage.metadata?.dublin_core?.[field] || '',
      status: status,
      notes: null
    }));

    const entity_validations_array = Object.entries(entityValidations).map(([entityId, status]) => ({
      entity_id: parseInt(entityId),
      status: status,
      corrected_name: null,
      corrected_type: null,
      notes: null
    }));

    const editData = {
      page_id: currentPage.page_id,
      page_number: currentPage.page_number,
      base_model: baseModel || selectedOCR,
      transcription: transcription,
      transcription_edited: transcriptionEdited,
      metadata_validations: metadata_validations_array,
      entity_validations: entity_validations_array
    };

    try {
      const response = await fetch('/api/save', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Session-Id': user.sessionId
        },
        body: JSON.stringify(editData)
      });
      
      const result = await response.json();
      if (result.success) {
        alert('Saved successfully!');
        
        // Reload the dataset to get the updated Human-Reviewed version
        const datasetResponse = await fetch('/api/dataset', {
          headers: {
            'X-Session-Id': user.sessionId
          }
        });
        const data = await datasetResponse.json();
        setDataset(data);
        
        handleNext();
      } else {
        alert('Failed to save: ' + result.message);
      }
    } catch (err) {
      alert('Failed to save: ' + err.message);
    }
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-main">
          <h1>
            {currentPage.metadata?.dublin_core?.date && (
              <span className="header-date">{currentPage.metadata.dublin_core.date} | </span>
            )}
            {dataset.document?.filename || 'Archive Editathon'}
          </h1>
          {currentPage.metadata?.archival_context && (
            <div className="archival-context">
              {currentPage.metadata.archival_context.collection && (
                <span className="context-item">{currentPage.metadata.archival_context.collection}</span>
              )}
              {currentPage.metadata.archival_context.box && (
                <span className="context-item">{currentPage.metadata.archival_context.box}</span>
              )}
              {currentPage.metadata.archival_context.folder && (
                <span className="context-item">{currentPage.metadata.archival_context.folder}</span>
              )}
            </div>
          )}
        </div>
        <div className="header-info">
          <span className="user-info">
            {user.username} | Pages {user.assigned_pages.start}-{user.assigned_pages.end}
          </span>
          <button onClick={handleLogout} className="btn-logout">
            Logout
          </button>
        </div>
      </header>

      <div className="workspace">
        {/* Left Sidebar - Page List */}
        <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
          <div className="sidebar-header">
            <h2>Pages</h2>
            <button 
              className="btn-collapse"
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              title={sidebarCollapsed ? 'Expand' : 'Collapse'}
            >
              {sidebarCollapsed ? '→' : '←'}
            </button>
          </div>
          {!sidebarCollapsed && (
            <div className="page-list">
              {assignedPages.map((page, index) => (
                <div
                  key={page.page_id}
                  className={`page-item ${index === currentPageIndex ? 'active' : ''} ${page.completion_status || 'not_started'}`}
                  onClick={() => {
                    setCurrentPageIndex(index);
                    loadPageData(page);
                  }}
                >
                  <div className="page-number">Page {page.page_number}</div>
                  <div className="page-status">
                    {page.completion_status === 'completed' && '✓'}
                    {page.completion_status === 'in_progress' && '⋯'}
                    {(!page.completion_status || page.completion_status === 'not_started') && '○'}
                  </div>
                </div>
              ))}
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <main className="main-area">
          {/* Metadata Validation Bar */}
          <section className="validation-bar">
            <div className="validation-bar-header">
              <h3>Metadata Validation</h3>
            </div>
            <div className="validation-bar-content">
              {currentPage.metadata?.dublin_core && (
                <>
                  {Object.entries(currentPage.metadata.dublin_core).map(([field, value]) => (
                    value && (
                      <div key={field} className="validation-bar-item">
                        <div className="validation-bar-label">
                          <strong>{field}:</strong> {value}
                        </div>
                        <div className="validation-bar-actions">
                          <button
                            onClick={() => handleMetadataValidation(field, 'approved')}
                            className={`btn-validate-compact ${metadataValidations[field] === 'approved' ? 'approved' : ''}`}
                            title="Approve"
                          >
                            ✓
                          </button>
                          <button
                            onClick={() => handleMetadataValidation(field, 'rejected')}
                            className={`btn-validate-compact ${metadataValidations[field] === 'rejected' ? 'rejected' : ''}`}
                            title="Reject"
                          >
                            ✗
                          </button>
                          <button
                            onClick={() => handleMetadataValidation(field, 'removed')}
                            className={`btn-validate-compact ${metadataValidations[field] === 'removed' ? 'removed' : ''}`}
                            title="Remove"
                          >
                            ×
                          </button>
                        </div>
                      </div>
                    )
                  ))}
                </>
              )}
            </div>
          </section>

          {/* Entity Validation Bar */}
          {currentPage.entities && Object.keys(currentPage.entities).length > 0 && (
            <section className="validation-bar entity-validation-bar">
              <div className="validation-bar-header">
                <h3>Named Entity Validation</h3>
              </div>
              <div className="validation-bar-content entity-two-column">
                {Object.entries(currentPage.entities).map(([type, entities]) => (
                  entities.length > 0 && (
                    <div key={type} className="entity-type-group">
                      <span className="entity-type-label">{type}:</span>
                      <div className="entity-pill-list">
                        {entities.map((entity) => (
                          <div 
                            key={entity.id} 
                            className={`entity-pill ${entityValidations[entity.id] || 'pending'}`}
                          >
                            <span className="entity-pill-name">{entity.name}</span>
                            <div className="entity-pill-actions">
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleEntityValidation(entity.id, 'approved');
                                }}
                                className="btn-pill-action approve"
                                title="Approve"
                              >
                                ✓
                              </button>
                              <button
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleEntityValidation(entity.id, 'rejected');
                                }}
                                className="btn-pill-action reject"
                                title="Reject"
                              >
                                ✗
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )
                ))}
              </div>
            </section>
          )}

          {/* Main Work Area - Facsimile and Transcription */}
          <section className="work-area">
            {/* Left: Facsimile */}
            <div className="facsimile-panel">
              <div className="panel-header">
                <h3>Facsimile - Page {currentPage.page_number}</h3>
                <div className="zoom-controls">
                  <button 
                    onClick={() => {
                      const newScale = Math.max(MIN_SCALE, scale - 0.1 * scale);
                      setScale(newScale);
                    }}
                    className="zoom-btn"
                    title="Zoom Out"
                  >
                    −
                  </button>
                  <span className="zoom-level">{Math.round(scale * 100)}%</span>
                  <button 
                    onClick={() => {
                      const newScale = Math.min(MAX_SCALE, scale + 0.1 * scale);
                      setScale(newScale);
                    }}
                    className="zoom-btn"
                    title="Zoom In"
                  >
                    +
                  </button>
                  <button 
                    onClick={fitWidth}
                    className="zoom-btn zoom-preset"
                    title="Fit Width"
                  >
                    ↔
                  </button>
                  <button 
                    onClick={fitHeight}
                    className="zoom-btn zoom-preset"
                    title="Fit Height"
                  >
                    ↕
                  </button>
                  <button 
                    onClick={resetZoom}
                    className="zoom-btn zoom-reset"
                    title="Reset Zoom (1:1)"
                  >
                    1:1
                  </button>
                </div>
              </div>
              <div 
                className={`facsimile-container ${isDragging ? 'dragging' : ''}`}
                ref={containerRef}
                onMouseDown={handleMouseDown}
                onDoubleClick={handleDoubleClick}
              >
                <img 
                  src={`/data/images/${currentPage.page_id}.jpg`}
                  alt={`Page ${currentPage.page_number}`}
                  className="facsimile-image"
                  ref={imageRef}
                  onLoad={() => {
                    // Auto fit-width on first load if image is wider than container
                    if (containerRef.current && imageRef.current && scale === 1) {
                      const containerWidth = containerRef.current.clientWidth - 32;
                      const imageWidth = imageRef.current.naturalWidth;
                      if (imageWidth > containerWidth) {
                        fitWidth();
                      }
                    }
                  }}
                  style={{
                    transform: `translate(${panX}px, ${panY}px) scale(${scale})`,
                    transformOrigin: '0 0',
                  }}
                  draggable={false}
                />
              </div>
            </div>

            {/* Right: Transcription Panel */}
            <div className="transcription-panel">
              <div className="panel-header">
                <h3>Transcription</h3>
              </div>

              {/* OCR Version Selection */}
              <div className="ocr-selection">
                <label><strong>OCR Versions:</strong></label>
                <div className="ocr-tabs">
                  {displayOCRVersions.map(version => (
                    <button
                      key={version}
                      className={`tab ${selectedOCR === version ? 'active' : ''} ${version === 'Human-Reviewed' ? 'human-reviewed' : ''} ${baseModel === version ? 'base-model' : ''}`}
                      onClick={() => handleOCRChange(version)}
                      disabled={baseModel && baseModel !== version && version !== 'Human-Reviewed'}
                    >
                      {version}
                      {version === 'Human-Reviewed' && ' ✓'}
                      {baseModel === version && version !== 'Human-Reviewed' && ' (Base)'}
                    </button>
                  ))}
                </div>
                {!baseModel && selectedOCR && selectedOCR !== 'Human-Reviewed' && (
                  <button 
                    className="btn-set-ground-truth"
                    onClick={handleSetBaseModel}
                  >
                    Use as Base & Edit
                  </button>
                )}
                {baseModel && selectedOCR !== 'Human-Reviewed' && (
                  <div className="ground-truth-info">
                    <span>✓ Base Model: {baseModel}</span>
                    <button 
                      className="btn-unlock"
                      onClick={handleUnlockBaseModel}
                    >
                      Unlock
                    </button>
                  </div>
                )}
                {selectedOCR === 'Human-Reviewed' && (
                  <div className="human-reviewed-info">
                    <span>✓ Human-Reviewed Transcription (Based on: {baseModel || 'Unknown'})</span>
                  </div>
                )}
              </div>

              {/* Transcription Editor */}
              <div className="transcription-editor">
                <label htmlFor="transcription">
                  <strong>
                    {selectedOCR === 'Human-Reviewed' ? 'Human-Reviewed Transcription:' : 
                     baseModel ? 'Edit Transcription (Creating Human-Reviewed):' : 
                     'OCR Text (Read-Only):'}
                  </strong>
                </label>
                <textarea
                  id="transcription"
                  value={transcription}
                  onChange={handleTranscriptionChange}
                  readOnly={!baseModel && selectedOCR !== 'Human-Reviewed'}
                  className={baseModel || selectedOCR === 'Human-Reviewed' ? 'editable' : 'readonly'}
                  rows={20}
                />
                {transcriptionEdited && (
                  <div className="edit-indicator">
                    ✏️ Edited
                  </div>
                )}
                {!baseModel && selectedOCR !== 'Human-Reviewed' && (
                  <div className="readonly-notice">
                    Select an OCR version and click "Use as Base & Edit" to create your human-reviewed transcription
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Navigation Controls */}
          <section className="work-area-navigation">
            <div className="nav-left">
              <button 
                onClick={handlePrevious} 
                disabled={currentPageIndex === 0}
                className="btn-nav"
              >
                ← Previous
              </button>
              <span className={`page-status status-${currentPage.completion_status || 'not_started'}`}>
                {currentPage.completion_status === 'completed' && '✓ Completed'}
                {currentPage.completion_status === 'in_progress' && '⋯ In Progress'}
                {(!currentPage.completion_status || currentPage.completion_status === 'not_started') && '○ Not Started'}
              </span>
            </div>
            <span className="nav-info">
              Page {currentPageIndex + 1} of {assignedPages.length} (Document page {currentPage.page_number})
            </span>
            <div className="nav-actions">
              <button onClick={handleSave} className="btn-save">
                Save & Continue
              </button>
              <button 
                onClick={handleNext} 
                disabled={currentPageIndex === assignedPages.length - 1}
                className="btn-nav"
              >
                Next →
              </button>
            </div>
          </section>
        </main>
      </div>
    </div>
  );
}

export default App;
