# EditathonSimple - Quick Start Guide

## Interface Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Archive Editathon          user123 | Pages 1-50      [Logout]  │
├──────────┬──────────────────────────────────────────────────────┤
│          │  Document Metadata              Page Info            │
│  Pages   │  Title: ...  Creator: ...       Page: 17  Status: ✓  │
│  ──────  ├──────────────────────────────────────────────────────┤
│  ○ Pg 1  │                    │                                  │
│  ⋯ Pg 2  │   Facsimile        │   Transcription Panel           │
│  ✓ Pg 3  │   ─────────        │   ───────────────────           │
│  ○ Pg 4  │                    │   OCR Versions: [Tesseract]     │
│  ○ Pg 5  │   [Page Image]     │   [Set as Ground Truth]         │
│  ...     │                    │                                  │
│          │                    │   Human-Reviewed Transcription: │
│  [←]     │                    │   ┌─────────────────────────┐   │
│          │                    │   │ Editable text area...   │   │
│          │                    │   │                         │   │
│          │                    │   └─────────────────────────┘   │
│          │                    │                                  │
│          │                    │   Metadata Validation           │
│          │                    │   Entity Validation             │
├──────────┴──────────────────────────────────────────────────────┤
│  [← Previous]    Page 17 of 50 (Document page 17)  [Save] [→]  │
└─────────────────────────────────────────────────────────────────┘
```

## Step-by-Step Workflow

### 1. Login
- Enter your username and password
- You'll be assigned a specific range of pages

### 2. Navigate to a Page
- Use the left sidebar to see all your assigned pages
- Click any page to jump to it
- Or use Previous/Next buttons at the bottom

### 3. Review the Facsimile
- The original page image is on the left
- Zoom in/out using your browser (Ctrl/Cmd + +/-)
- Scroll to see the full page

### 4. Select Ground Truth OCR

**Important: This is the key new feature!**

a. Click through the OCR version tabs to compare outputs:
   - `tesseract` - Tesseract OCR engine
   - `openai_ocr` - OpenAI Vision OCR
   - Other versions as available

b. Choose the best/most accurate version

c. Click **"Set as Ground Truth & Edit"**
   - The selected version is now locked (green with ★)
   - The text area becomes editable (green background)
   - You can now create your human-reviewed transcription

### 5. Edit the Transcription

**Only possible after setting ground truth!**

- Make corrections to the OCR text
- Fix spelling errors, formatting, etc.
- Create the definitive "human-reviewed" version
- An "✏️ Edited" indicator appears when you make changes

**To unlock and choose a different base:**
- Click the "Unlock" button in the green info box
- Select a different OCR version
- Click "Set as Ground Truth & Edit" again

### 6. Validate Metadata

For each metadata field (title, creator, date, etc.):

- **✓ Approve** - The metadata is correct
- **✗ Reject** - The metadata is incorrect
- **× Remove** - The metadata should be removed

Click the appropriate button for each field.

### 7. Validate Named Entities

Entities are organized by type (PERSON, ORG, GPE, etc.):

- **✓ Approve** - The entity is correctly identified
- **✗ Reject** - The entity is incorrect or not an entity

Click the appropriate button for each entity.

### 8. Save Your Work

Click **"Save & Continue"** to:
- Save all your edits and validations
- Automatically advance to the next page

Or click **"Save"** to save without advancing.

## Status Indicators

### Page List Status
- **○** Not Started (gray) - No work done yet
- **⋯** In Progress (yellow) - Some work saved
- **✓** Completed (green) - Fully reviewed and saved

### OCR Version Status
- **Blue background** - Currently viewing this version
- **Green background with ★** - This is your ground truth (locked for editing)
- **Gray/disabled** - Other versions (when ground truth is locked)

### Transcription Status
- **Green border** - Editable (ground truth selected)
- **Gray background** - Read-only (no ground truth selected)
- **✏️ Edited** - You've made changes to the transcription

## Tips & Best Practices

### Choosing Ground Truth
1. Compare all available OCR versions
2. Look for the one with:
   - Fewest obvious errors
   - Best formatting preservation
   - Most complete text
3. Don't worry about minor errors - you'll fix them in editing

### Editing Transcription
- Fix obvious OCR errors (e.g., "tbe" → "the")
- Preserve original spelling and punctuation
- Don't modernize or "improve" the text
- Keep formatting as close to original as possible

### Validating Metadata
- Approve if it matches the document
- Reject if it's clearly wrong
- Remove if it's not applicable or redundant

### Validating Entities
- Approve if correctly identified and typed
- Reject if it's not actually an entity or wrong type
- When in doubt, approve (better to have false positives)

### Saving
- Save frequently (every page or two)
- "Save & Continue" is fastest for sequential work
- Your progress is tracked automatically

## Keyboard Shortcuts

Currently available browser shortcuts:
- **Ctrl/Cmd + +/-** - Zoom in/out
- **Ctrl/Cmd + 0** - Reset zoom
- **Tab** - Navigate between fields
- **Enter** - Submit forms

## Troubleshooting

### Can't Edit Transcription
- Make sure you've clicked "Set as Ground Truth & Edit"
- The text area should have a green background when editable

### Lost My Work
- Work is only saved when you click Save
- Use "Save & Continue" frequently
- Check the page status in the sidebar

### Image Not Loading
- Check your internet connection
- Try refreshing the page (F5)
- Contact administrator if problem persists

### Wrong Page Range
- You're assigned specific pages (shown in header)
- Contact administrator to change assignment

## Getting Help

If you encounter issues:
1. Check this guide first
2. Try refreshing the page
3. Contact the editathon administrator
4. Report technical issues with:
   - Your username
   - Page number
   - Description of the problem
   - Screenshot if possible

## Progress Tracking

Your progress is automatically tracked:
- Pages completed vs. assigned
- Time spent per page
- Validation decisions
- All saved in the database

Administrators can view overall progress and export results.
