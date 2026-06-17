import { useState, useEffect, useRef, useCallback } from 'react';
import Login from './Login';
import AdminDashboard from './AdminDashboard';

function App() {
  const [user, setUser] = useState(null);
  const [allPages, setAllPages] = useState([]); // Lightweight list of all pages
  const [assignedRange, setAssignedRange] = useState(null); // { start, end }
  const [currentPage, setCurrentPage] = useState(null); // Full page data for current selection
  const [currentPageIndex, setCurrentPageIndex] = useState(0);
  const [pageLoading, setPageLoading] = useState(false);
  const [selectedOCR, setSelectedOCR] = useState('');
  const [baseModel, setBaseModel] = useState(''); // The model chosen as starting point
  const [transcription, setTranscription] = useState('');
  const [transcriptionEdited, setTranscriptionEdited] = useState(false);
  const [metadataValidations, setMetadataValidations] = useState({});
  const [entityValidations, setEntityValidations] = useState({});
  const [loading, setLoading] = useState(true);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [inlineAddType, setInlineAddType] = useState(null); // which type group has inline add open
  const [inlineAddValue, setInlineAddValue] = useState('');
  const [showAddEntityForm, setShowAddEntityForm] = useState(false);
  const [newEntityType, setNewEntityType] = useState('');
  const [newEntityName, setNewEntityName] = useState('');
  
  // Document groups state
  const [documentGroups, setDocumentGroups] = useState([]);
  const [showGroupPanel, setShowGroupPanel] = useState(false);
  const [editingGroupMetadata, setEditingGroupMetadata] = useState(null); // group id being edited

  const DUBLIN_CORE_FIELDS = ['title', 'creator', 'date', 'subject', 'description', 'type', 'format', 'source', 'language', 'coverage', 'rights'];
  
  // Pan-zoom state
  const [scale, setScale] = useState(1);
  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const dragStart = useRef({ x: 0, y: 0 });
  const panStart = useRef({ x: 0, y: 0 });
  const containerRef = useRef(null);
  const imageRef = useRef(null);
  const firstAssignedRef = useRef(null);

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
    
    // Load lightweight page list (all pages)
    fetch('/api/pages-list', {
      headers: {
        'X-Session-Id': user.sessionId
      }
    })
      .then(res => {
        if (res.status === 401) {
          localStorage.clear();
          window.location.reload();
          return null;
        }
        return res.json();
      })
      .then(data => {
        if (!data) return;
        
        setAllPages(data.pages);
        setAssignedRange(data.assigned_range);
        setLoading(false);
        
        // Auto-select the first assigned page
        if (data.pages.length > 0) {
          const firstAssignedIndex = data.pages.findIndex(
            p => p.page_number >= data.assigned_range.start
          );
          const startIndex = firstAssignedIndex >= 0 ? firstAssignedIndex : 0;
          setCurrentPageIndex(startIndex);
          fetchPageDetail(data.pages[startIndex].page_id);
        }
      })
      .catch(err => {
        console.error('Failed to load pages list:', err);
        setLoading(false);
      });
    
    // Also load document groups
    fetch('/api/document-groups', {
      headers: { 'X-Session-Id': user.sessionId }
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setDocumentGroups(data.groups);
        }
      })
      .catch(err => console.error('Failed to load document groups:', err));
  }, [user]);

  // Scroll sidebar to first assigned page when page list loads
  useEffect(() => {
    if (firstAssignedRef.current) {
      firstAssignedRef.current.scrollIntoView({ block: 'start', behavior: 'smooth' });
    }
  }, [allPages]);

  // Fetch full page data on-demand
  const fetchPageDetail = async (pageId) => {
    setPageLoading(true);
    try {
      const res = await fetch(`/api/page/${pageId}`, {
        headers: { 'X-Session-Id': user.sessionId }
      });
      if (res.status === 401) {
        localStorage.clear();
        window.location.reload();
        return;
      }
      const pageData = await res.json();
      setCurrentPage(pageData);
      
      // Load editor state from page data
      if (pageData.ocr_versions && Object.keys(pageData.ocr_versions).length > 0) {
        if (pageData.ocr_versions['Human-Reviewed']) {
          setSelectedOCR('Human-Reviewed');
          setBaseModel(pageData.saved_state?.ocr_selected || '');
          setTranscription(pageData.ocr_versions['Human-Reviewed'] || '');
          setTranscriptionEdited(true);
          setMetadataValidations(pageData.saved_state?.metadata_validations || {});
          setEntityValidations(pageData.saved_state?.entity_validations || {});
        } else if (pageData.saved_state) {
          setSelectedOCR(pageData.saved_state.ocr_selected);
          setBaseModel(pageData.saved_state.ocr_selected);
          setTranscription(pageData.ocr_versions[pageData.saved_state.ocr_selected] || '');
          setTranscriptionEdited(false);
          setMetadataValidations(pageData.saved_state.metadata_validations || {});
          setEntityValidations(pageData.saved_state.entity_validations || {});
        } else {
          const firstOCR = Object.keys(pageData.ocr_versions).filter(k => k !== 'Human-Reviewed')[0];
          setSelectedOCR(firstOCR || '');
          setBaseModel('');
          setTranscription(pageData.ocr_versions[firstOCR] || '');
          setTranscriptionEdited(false);
          setMetadataValidations({});
          setEntityValidations({});
        }
      }
    } catch (err) {
      console.error('Failed to load page:', err);
    } finally {
      setPageLoading(false);
    }
  };

  // Helper: is the current page within the user's assignment?
  const isCurrentPageAssigned = currentPage?.is_assigned ?? false;

  const handleLogin = (userData) => {
    setUser(userData);
  };

  const handleLogout = () => {
    localStorage.removeItem('sessionId');
    localStorage.removeItem('username');
    localStorage.removeItem('assigned_pages');
    localStorage.removeItem('is_admin');
    setUser(null);
    setAllPages([]);
    setCurrentPage(null);
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

  if (allPages.length === 0) {
    return <div style={{padding: '2rem'}}>No pages found in dataset.</div>;
  }

  const ocrVersions = currentPage ? Object.keys(currentPage.ocr_versions) : [];
  
  // Add Human-Reviewed to the list if user is editing or has edited
  const displayOCRVersions = [...ocrVersions];
  if (baseModel && !displayOCRVersions.includes('Human-Reviewed')) {
    displayOCRVersions.push('Human-Reviewed');
  }

  // Find which document group the current page belongs to
  const currentGroup = currentPage 
    ? documentGroups.find(g => currentPage.page_number >= g.start_page && currentPage.page_number <= g.end_page)
    : null;

  // Check if current page has pre-existing metadata from the database
  const hasPreExistingMetadata = currentPage?.metadata?.dublin_core && 
    Object.values(currentPage.metadata.dublin_core).some(v => v);

  // Create a new document group starting at current page
  const handleCreateGroup = async (startPage, endPage) => {
    try {
      const response = await fetch('/api/document-groups', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Id': user.sessionId
        },
        body: JSON.stringify({
          start_page: startPage,
          end_page: endPage,
          continues_before: false,
          continues_after: false,
          dublin_core: {}
        })
      });
      const result = await response.json();
      if (result.success) {
        setDocumentGroups(prev => [...prev, result.group].sort((a, b) => a.start_page - b.start_page));
      } else {
        alert('Failed to create group: ' + result.message);
      }
    } catch (err) {
      alert('Failed to create group: ' + err.message);
    }
  };

  // Update a document group
  const handleUpdateGroup = async (groupId, updates) => {
    try {
      const response = await fetch(`/api/document-groups/${groupId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Id': user.sessionId
        },
        body: JSON.stringify(updates)
      });
      const result = await response.json();
      if (result.success) {
        setDocumentGroups(prev => prev.map(g => g.id === groupId ? result.group : g));
      } else {
        alert('Failed to update group: ' + result.message);
      }
    } catch (err) {
      alert('Failed to update group: ' + err.message);
    }
  };

  // Delete a document group
  const handleDeleteGroup = async (groupId) => {
    if (!confirm('Delete this document group? The metadata will be lost.')) return;
    try {
      const response = await fetch(`/api/document-groups/${groupId}`, {
        method: 'DELETE',
        headers: { 'X-Session-Id': user.sessionId }
      });
      const result = await response.json();
      if (result.success) {
        setDocumentGroups(prev => prev.filter(g => g.id !== groupId));
      } else {
        alert('Failed to delete group: ' + result.message);
      }
    } catch (err) {
      alert('Failed to delete group: ' + err.message);
    }
  };

  // Update a Dublin Core field on the current group
  const handleGroupMetadataChange = (field, value) => {
    if (!currentGroup) return;
    const updatedDC = { ...(currentGroup.dublin_core || {}), [field]: value };
    // Update locally immediately for responsiveness
    setDocumentGroups(prev => prev.map(g => 
      g.id === currentGroup.id ? { ...g, dublin_core: updatedDC } : g
    ));
  };

  // Save group metadata to server (debounced save on blur)
  const handleGroupMetadataSave = async () => {
    if (!currentGroup) return;
    const group = documentGroups.find(g => g.id === currentGroup.id);
    if (group) {
      await handleUpdateGroup(group.id, { dublin_core: group.dublin_core });
    }
  };

  const handlePrevious = () => {
    if (currentPageIndex > 0) {
      const newIndex = currentPageIndex - 1;
      setCurrentPageIndex(newIndex);
      fetchPageDetail(allPages[newIndex].page_id);
      resetZoom();
    }
  };

  const handleNext = () => {
    if (currentPageIndex < allPages.length - 1) {
      const newIndex = currentPageIndex + 1;
      setCurrentPageIndex(newIndex);
      fetchPageDetail(allPages[newIndex].page_id);
      resetZoom();
    }
  };

  const handlePageSelect = (index) => {
    setCurrentPageIndex(index);
    fetchPageDetail(allPages[index].page_id);
    resetZoom();
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

  // Add a new entity to the current page
  const handleAddEntity = async (entityType, entityName) => {
    if (!entityName.trim() || !entityType.trim() || !currentPage) return;

    try {
      const response = await fetch('/api/add-entity', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Session-Id': user.sessionId
        },
        body: JSON.stringify({
          page_id: currentPage.page_id,
          entity_type: entityType,
          entity_name: entityName.trim()
        })
      });

      const result = await response.json();
      if (result.success) {
        // Add the new entity to local state
        const newEntity = result.entity;
        const updatedEntities = { ...currentPage.entities };
        const typeKey = newEntity.entity_type;
        if (!updatedEntities[typeKey]) {
          updatedEntities[typeKey] = [];
        }
        updatedEntities[typeKey].push({
          id: newEntity.id,
          name: newEntity.entity_name
        });
        setCurrentPage(prev => ({ ...prev, entities: updatedEntities }));

        // Auto-approve the entity the user just added
        setEntityValidations(prev => ({
          ...prev,
          [newEntity.id]: 'approved'
        }));

        // Clear inputs
        setInlineAddValue('');
        setInlineAddType(null);
        setNewEntityType('');
        setNewEntityName('');
        setShowAddEntityForm(false);
      } else {
        alert('Failed to add entity: ' + result.message);
      }
    } catch (err) {
      alert('Failed to add entity: ' + err.message);
    }
  };

  const handleSave = async () => {
    if (!isCurrentPageAssigned || !currentPage) return;

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
        
        // Update the page list status locally
        setAllPages(prev => prev.map(p => 
          p.page_id === currentPage.page_id 
            ? { ...p, completion_status: 'completed' }
            : p
        ));
        
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
            {currentPage?.metadata?.dublin_core?.date && (
              <span className="header-date">{currentPage.metadata.dublin_core.date} | </span>
            )}
            Archive Editathon
          </h1>
          {currentPage?.metadata?.archival_context && (
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
            {user.username} | Assigned: Pages {user.assigned_pages.start}-{user.assigned_pages.end}
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
              {allPages.map((page, index) => {
                const isAssigned = assignedRange && 
                  page.page_number >= assignedRange.start && 
                  page.page_number <= assignedRange.end;
                const isFirstAssigned = assignedRange && page.page_number === assignedRange.start;
                const isLastAssigned = assignedRange && page.page_number === assignedRange.end;
                
                return (
                  <div key={page.page_id} ref={isFirstAssigned ? firstAssignedRef : null}>
                    {isFirstAssigned && (
                      <div className="sidebar-section-label assigned-start-label">
                        Your Assignment ↓
                      </div>
                    )}
                    <div
                      className={`page-item ${index === currentPageIndex ? 'active' : ''} ${isAssigned ? 'assigned-page ' + (page.completion_status || 'not_started') : 'context-page'}`}
                      onClick={() => handlePageSelect(index)}
                    >
                      <div className="page-number">Page {page.page_number}</div>
                      <div className="page-status">
                        {isAssigned && page.completion_status === 'completed' && '✓'}
                        {isAssigned && page.completion_status === 'in_progress' && '⋯'}
                        {isAssigned && (!page.completion_status || page.completion_status === 'not_started') && '○'}
                        {!isAssigned && '👁'}
                      </div>
                    </div>
                    {isLastAssigned && (
                      <div className="sidebar-section-label assigned-end-label">
                        ↑ End of Assignment
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </aside>

        {/* Main Content Area */}
        <main className="main-area">
          {pageLoading && (
            <div className="page-loading-overlay">Loading page...</div>
          )}

          {!currentPage && !pageLoading && (
            <div style={{padding: '2rem', color: '#6b7280'}}>Select a page from the sidebar.</div>
          )}

          {currentPage && (
            <>
              {/* Read-only banner for context pages */}
              {!isCurrentPageAssigned && (
                <div className="readonly-banner">
                  Viewing for context only — this page is outside your assignment (Pages {user.assigned_pages.start}-{user.assigned_pages.end})
                </div>
              )}

              {/* Metadata Validation Bar */}
              <section className="validation-bar">
                <div className="validation-bar-header">
                  <h3>Metadata</h3>
                  {isCurrentPageAssigned && (
                    <button
                      className="btn-add-entity-toggle"
                      onClick={() => setShowGroupPanel(!showGroupPanel)}
                    >
                      {showGroupPanel ? 'Hide' : 'Document Groups'}
                    </button>
                  )}
                </div>

                {/* Pre-existing metadata: validation mode */}
                {hasPreExistingMetadata && (
                  <div className="validation-bar-content">
                    {Object.entries(currentPage.metadata.dublin_core).map(([field, value]) => (
                      value && (
                        <div key={field} className="validation-bar-item">
                          <div className="validation-bar-label">
                            <strong>{field}:</strong> {value}
                          </div>
                          {isCurrentPageAssigned && (
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
                          )}
                        </div>
                      )
                    ))}
                  </div>
                )}

                {/* Document Group metadata: authoring mode */}
                {!hasPreExistingMetadata && currentGroup && (
                  <div className="group-metadata-display">
                    <div className="group-metadata-header">
                      <span className="group-badge">
                        Document: Pages {currentGroup.start_page}–{currentGroup.end_page}
                        {currentGroup.continues_before && ' (continues from previous)'}
                        {currentGroup.continues_after && ' (continues after)'}
                      </span>
                    </div>
                    <div className="group-metadata-fields">
                      {DUBLIN_CORE_FIELDS.map(field => (
                        <div key={field} className="group-field">
                          <label className="group-field-label">{field}:</label>
                          <input
                            type="text"
                            value={(currentGroup.dublin_core || {})[field] || ''}
                            onChange={(e) => handleGroupMetadataChange(field, e.target.value)}
                            onBlur={handleGroupMetadataSave}
                            placeholder={`Enter ${field}...`}
                            className="group-field-input"
                            readOnly={!isCurrentPageAssigned}
                          />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* No metadata and no group defined yet */}
                {!hasPreExistingMetadata && !currentGroup && isCurrentPageAssigned && (
                  <div className="no-group-notice">
                    No document group defined for this page. Use "Document Groups" to define document boundaries and add metadata.
                  </div>
                )}

                {/* Document Groups Panel */}
                {isCurrentPageAssigned && showGroupPanel && (
                  <div className="document-groups-panel">
                    <div className="groups-panel-header">
                      <h4>Your Document Groups</h4>
                      <button
                        className="btn-add-entity"
                        onClick={() => {
                          const pageNum = currentPage.page_number;
                          handleCreateGroup(pageNum, pageNum);
                        }}
                      >
                        + Start Group at Page {currentPage?.page_number}
                      </button>
                    </div>

                    {documentGroups.length === 0 && (
                      <p className="groups-empty">No groups defined yet. Create one to define a document boundary.</p>
                    )}

                    <div className="groups-list">
                      {documentGroups.map(group => (
                        <div key={group.id} className={`group-card ${currentGroup?.id === group.id ? 'active' : ''}`}>
                          <div className="group-card-header">
                            <span className="group-card-range">
                              Pages {group.start_page}–{group.end_page}
                              {group.dublin_core?.title && `: ${group.dublin_core.title}`}
                            </span>
                            <button
                              className="btn-pill-action reject"
                              onClick={() => handleDeleteGroup(group.id)}
                              title="Delete group"
                            >
                              ✗
                            </button>
                          </div>
                          <div className="group-card-controls">
                            <label className="group-range-label">
                              Start:
                              <input
                                type="number"
                                value={group.start_page}
                                min={user.assigned_pages.start}
                                max={group.end_page}
                                onChange={(e) => handleUpdateGroup(group.id, { start_page: parseInt(e.target.value) })}
                                className="group-range-input"
                              />
                            </label>
                            <label className="group-range-label">
                              End:
                              <input
                                type="number"
                                value={group.end_page}
                                min={group.start_page}
                                max={user.assigned_pages.end}
                                onChange={(e) => handleUpdateGroup(group.id, { end_page: parseInt(e.target.value) })}
                                className="group-range-input"
                              />
                            </label>
                            <label className="group-checkbox">
                              <input
                                type="checkbox"
                                checked={group.continues_before || false}
                                onChange={(e) => handleUpdateGroup(group.id, { continues_before: e.target.checked })}
                              />
                              Continues from before
                            </label>
                            <label className="group-checkbox">
                              <input
                                type="checkbox"
                                checked={group.continues_after || false}
                                onChange={(e) => handleUpdateGroup(group.id, { continues_after: e.target.checked })}
                              />
                              Continues after
                            </label>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </section>

              {/* Entity Validation Bar */}
              {((currentPage.entities && Object.keys(currentPage.entities).length > 0) || isCurrentPageAssigned) && (
                <section className="validation-bar entity-validation-bar">
                  <div className="validation-bar-header">
                    <h3>Named Entity Validation</h3>
                    {isCurrentPageAssigned && (
                      <button
                        className="btn-add-entity-toggle"
                        onClick={() => setShowAddEntityForm(!showAddEntityForm)}
                        title="Add entity with new category"
                      >
                        + New Category
                      </button>
                    )}
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
                                {isCurrentPageAssigned && (
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
                                )}
                              </div>
                            ))}
                            {/* Inline add for this type */}
                            {isCurrentPageAssigned && (
                              <>
                                {inlineAddType === type ? (
                                  <div className="entity-inline-add">
                                    <input
                                      type="text"
                                      value={inlineAddValue}
                                      onChange={(e) => setInlineAddValue(e.target.value)}
                                      onKeyDown={(e) => {
                                        if (e.key === 'Enter' && inlineAddValue.trim()) {
                                          handleAddEntity(type, inlineAddValue);
                                        } else if (e.key === 'Escape') {
                                          setInlineAddType(null);
                                          setInlineAddValue('');
                                        }
                                      }}
                                      placeholder={`Add ${type.toLowerCase()}...`}
                                      autoFocus
                                      className="entity-inline-input"
                                    />
                                    <button
                                      onClick={() => {
                                        if (inlineAddValue.trim()) {
                                          handleAddEntity(type, inlineAddValue);
                                        }
                                      }}
                                      className="btn-pill-action approve"
                                      title="Add"
                                    >
                                      ✓
                                    </button>
                                    <button
                                      onClick={() => {
                                        setInlineAddType(null);
                                        setInlineAddValue('');
                                      }}
                                      className="btn-pill-action reject"
                                      title="Cancel"
                                    >
                                      ✗
                                    </button>
                                  </div>
                                ) : (
                                  <button
                                    className="btn-inline-add"
                                    onClick={() => {
                                      setInlineAddType(type);
                                      setInlineAddValue('');
                                    }}
                                    title={`Add ${type.toLowerCase()}`}
                                  >
                                    +
                                  </button>
                                )}
                              </>
                            )}
                          </div>
                        </div>
                      )
                    ))}
                  </div>
                  {/* General Add Entity form for new categories */}
                  {isCurrentPageAssigned && showAddEntityForm && (
                    <div className="add-entity-form">
                      <select
                        value={newEntityType}
                        onChange={(e) => setNewEntityType(e.target.value)}
                        className="add-entity-select"
                      >
                        <option value="">Select category...</option>
                        <option value="PERSON">PERSON</option>
                        <option value="LOCATION">LOCATION</option>
                        <option value="ORGANIZATION">ORGANIZATION</option>
                        <option value="DATE">DATE</option>
                        <option value="EVENT">EVENT</option>
                        <option value="WORK">WORK</option>
                        <option value="OBJECT">OBJECT</option>
                        <option value="LANGUAGE">LANGUAGE</option>
                        <option value="QUANTITY">QUANTITY</option>
                        <option value="OTHER">OTHER</option>
                      </select>
                      <input
                        type="text"
                        value={newEntityName}
                        onChange={(e) => setNewEntityName(e.target.value)}
                        placeholder="Entity name"
                        className="add-entity-input"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' && newEntityType.trim() && newEntityName.trim()) {
                            handleAddEntity(newEntityType, newEntityName);
                          }
                        }}
                      />
                      <button
                        onClick={() => {
                          if (newEntityType.trim() && newEntityName.trim()) {
                            handleAddEntity(newEntityType, newEntityName);
                          }
                        }}
                        className="btn-add-entity"
                        disabled={!newEntityType.trim() || !newEntityName.trim()}
                      >
                        Add
                      </button>
                      <button
                        onClick={() => {
                          setShowAddEntityForm(false);
                          setNewEntityType('');
                          setNewEntityName('');
                        }}
                        className="btn-cancel-entity"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
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
                <h3>Transcription{!isCurrentPageAssigned && ' (Read-Only)'}</h3>
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
                {isCurrentPageAssigned && !baseModel && selectedOCR && selectedOCR !== 'Human-Reviewed' && (
                  <button 
                    className="btn-set-ground-truth"
                    onClick={handleSetBaseModel}
                  >
                    Use as Base & Edit
                  </button>
                )}
                {isCurrentPageAssigned && baseModel && selectedOCR !== 'Human-Reviewed' && (
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
                    {!isCurrentPageAssigned ? 'OCR Text (Context Page - Read-Only):' :
                     selectedOCR === 'Human-Reviewed' ? 'Human-Reviewed Transcription:' : 
                     baseModel ? 'Edit Transcription (Creating Human-Reviewed):' : 
                     'OCR Text (Read-Only):'}
                  </strong>
                </label>
                <textarea
                  id="transcription"
                  value={transcription}
                  onChange={handleTranscriptionChange}
                  readOnly={!isCurrentPageAssigned || (!baseModel && selectedOCR !== 'Human-Reviewed')}
                  className={isCurrentPageAssigned && (baseModel || selectedOCR === 'Human-Reviewed') ? 'editable' : 'readonly'}
                  rows={20}
                />
                {isCurrentPageAssigned && transcriptionEdited && (
                  <div className="edit-indicator">
                    ✏️ Edited
                  </div>
                )}
                {isCurrentPageAssigned && !baseModel && selectedOCR !== 'Human-Reviewed' && (
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
              <span className={`page-status status-${isCurrentPageAssigned ? (currentPage.completion_status || 'not_started') : 'context'}`}>
                {!isCurrentPageAssigned && '👁 Context Page'}
                {isCurrentPageAssigned && currentPage.completion_status === 'completed' && '✓ Completed'}
                {isCurrentPageAssigned && currentPage.completion_status === 'in_progress' && '⋯ In Progress'}
                {isCurrentPageAssigned && (!currentPage.completion_status || currentPage.completion_status === 'not_started') && '○ Not Started'}
              </span>
            </div>
            <span className="nav-info">
              Page {currentPageIndex + 1} of {allPages.length} (Document page {currentPage.page_number})
            </span>
            <div className="nav-actions">
              {isCurrentPageAssigned && (
                <button onClick={handleSave} className="btn-save">
                  Save & Continue
                </button>
              )}
              <button 
                onClick={handleNext} 
                disabled={currentPageIndex === allPages.length - 1}
                className="btn-nav"
              >
                Next →
              </button>
            </div>
          </section>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
