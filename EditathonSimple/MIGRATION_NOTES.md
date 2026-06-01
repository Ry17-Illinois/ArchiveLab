# Migration Notes - UI Update

## For Administrators

### What Changed
The EditathonSimple interface has been completely redesigned with a new layout and workflow. The core functionality remains the same, but the user experience is significantly improved.

### Database Compatibility
✅ **Fully backward compatible** - No database schema changes required for this UI update.

The interface works with:
- Existing `edits` table structure
- Current `metadata_validations` table
- Current `entity_validations` table
- Migration 001 (completion tracking) if applied

### Deployment Steps

1. **Backup Current Version**
   ```bash
   cp -r EditathonSimple EditathonSimple.backup
   ```

2. **Update Files**
   - Replace `src/App.jsx` with new version
   - Replace `src/index.css` with new version
   - Add new documentation files (optional)

3. **Rebuild Application**
   ```bash
   cd EditathonSimple
   npm run build
   ```

4. **Test Locally**
   ```bash
   npm run dev
   ```
   - Login with test account
   - Navigate through pages
   - Test ground truth workflow
   - Test validation buttons
   - Verify save functionality

5. **Deploy to Production**
   - Upload new `dist/` folder
   - Restart Node.js application
   - Test with real user account

### User Communication

**Recommended announcement to users:**

---

**EditathonSimple Interface Update**

We've updated the editathon interface with several improvements:

**New Features:**
- Page list sidebar for easier navigation
- Ground truth workflow for transcription editing
- Improved metadata and entity validation interface
- Better visual organization

**What You Need to Know:**
1. The workflow is now more explicit - you must select a "ground truth" OCR version before editing
2. All your previous work is preserved
3. The new interface is more intuitive and requires less scrolling
4. Please review the Quick Start Guide for details

**Action Required:**
- None! Just login and start working with the new interface
- Your assigned pages and progress are unchanged

---

### Rollback Plan

If issues arise:

1. **Stop the application**
2. **Restore backup**
   ```bash
   rm -rf EditathonSimple/dist
   cp -r EditathonSimple.backup/dist EditathonSimple/
   ```
3. **Restart application**

No database changes needed for rollback.

## For Users

### What's Different

#### Old Interface
- Two-panel layout (image left, editor right)
- All OCR versions editable immediately
- Metadata and entities at bottom
- Linear navigation only

#### New Interface
- Three-section layout (sidebar, image, editor)
- Must select ground truth before editing
- Metadata at top, validations in editor panel
- Click any page in sidebar to jump

### Your Data is Safe

✅ All your previous work is preserved:
- Completed pages remain completed
- Saved transcriptions are unchanged
- Validation decisions are retained
- Progress tracking continues

### Learning the New Interface

**5-Minute Orientation:**

1. **Left Sidebar** - Click any page to jump to it
2. **Top Bar** - Quick reference for metadata
3. **Left Panel** - View the page image
4. **Right Panel** - Do your work here
5. **Bottom Bar** - Navigate and save

**Key New Concept: Ground Truth**

Before you can edit a transcription:
1. Compare OCR versions by clicking the tabs
2. Choose the best one
3. Click "Set as Ground Truth & Edit"
4. Now you can edit the text

This ensures we track which OCR version you started from.

### Common Questions

**Q: Why can't I edit the transcription?**
A: You need to select a ground truth OCR version first. Click an OCR tab, then click "Set as Ground Truth & Edit".

**Q: What if I pick the wrong OCR version?**
A: Click "Unlock" in the green box, then select a different version and set it as ground truth.

**Q: Where did the page list go?**
A: It's now in the left sidebar. Click the arrow to collapse/expand it.

**Q: Can I still use Previous/Next buttons?**
A: Yes! They're at the bottom of the screen.

**Q: Will this change my assigned pages?**
A: No, your page assignment is unchanged.

**Q: Do I need to redo completed pages?**
A: No, completed pages remain completed.

## Technical Notes

### State Management Changes

New state variables:
```javascript
const [groundTruthOCR, setGroundTruthOCR] = useState('');
const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
```

### API Compatibility

The save endpoint receives the same data structure:
```javascript
{
  page_id: string,
  page_number: number,
  ocr_selected: string,  // Now the ground truth version
  transcription: string,
  transcription_edited: boolean,
  metadata_validations: array,
  entity_validations: array
}
```

The `ocr_selected` field now specifically indicates which OCR version was used as the ground truth for the human-reviewed transcription.

### CSS Architecture

The new CSS uses:
- Flexbox for layout
- CSS Grid for metadata display
- CSS custom properties could be added for theming
- Responsive design principles
- Accessibility-friendly focus states

### Browser Requirements

Minimum browser versions:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

Uses standard CSS and JavaScript - no special polyfills needed.

## Performance Considerations

### Improvements
- Sidebar navigation reduces full page reloads
- Metadata bar reduces scrolling
- Validation buttons are more compact

### Potential Issues
- Large page lists (100+ pages) may slow sidebar rendering
- Very long transcriptions may impact textarea performance

### Optimization Tips
- Keep page assignments reasonable (50-100 pages per user)
- Consider pagination for very large datasets
- Monitor browser memory usage with large images

## Accessibility

The new interface includes:
- Semantic HTML structure
- Keyboard navigation support
- Focus indicators
- ARIA labels (could be enhanced)
- Color contrast compliance

Future improvements could include:
- Screen reader optimization
- Keyboard shortcuts
- High contrast mode
- Font size controls

## Future Enhancements

Potential additions that would require code changes:
- Auto-save functionality
- Undo/redo for transcription
- Entity correction interface
- Metadata editing (not just validation)
- Keyboard shortcuts
- Progress dashboard
- Export functionality
- Collaborative features

These would require additional state management and API endpoints.

## Support

For technical issues:
- Check browser console for errors
- Verify API endpoints are responding
- Check database connectivity
- Review server logs

For user issues:
- Refer to Quick Start Guide
- Provide training session
- Create video tutorial
- Set up help desk

## Version History

- **v2.0** (Current) - Complete UI redesign with ground truth workflow
- **v1.0** - Original two-panel interface

## License & Credits

This interface update maintains compatibility with the original EditathonSimple architecture while providing a significantly improved user experience.
