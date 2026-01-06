# Emergency Data Capture - File Format Summary

## Current File Types Being Captured

### Media Files (Keep as-is):
- **Screenshots**: `.png` or `.jpg` files
- **Screen Recording**: `.mp4` or `.avi` video files  
- **Camera**: `.mp4` video files
- **Microphone**: `.wav` or `.mp3` audio files

### Data Files (Currently JSON - User wants different format):
- **Activity**: `.json` files containing:
  - Active window title
  - Running applications list
  - Activity summary
  
- **Telemetry**: `.json` files containing:
  - GPS location
  - IP address
  - Network info
  - System stats

- **Typed Activity**: `.json` files containing:
  - Keystroke patterns
  - Typing intensity
  - Application usage

## User Request:
"dont shar ejons son formare share in pdf format"
- Don't share JSON files
- Convert to PDF or readable text format

## Recommended Solution:
Since PDF generation requires additional libraries (`reportlab`, `fpdf2`), and emergency mode should be lightweight and reliable, I recommend:

### Option 1: Convert JSON to TXT (Simple, No Dependencies)
- Activity.json → Activity.txt (human-readable format)
- Telemetry.json → Telemetry.txt
- Easy to read in email
- No extra dependencies

### Option 2: Embed JSON data in email body (No attachments)
- Include activity/telemetry data directly in the email text
- Only attach media files (screenshots, videos, audio)
- Cleaner email with fewer attachments

### Option 3: PDF Generation (Requires new library)
- Install `fpdf2` or `reportlab`
- Convert JSON data to formatted PDF
- Professional appearance
- Requires adding dependency to requirements.txt

## Current Implementation Status:
✅ Screenshots now being captured (added in previous fix)
✅ All media files attached correctly
⚠️ JSON files still being attached (needs conversion)

## Next Steps:
1. Choose format preference (TXT vs PDF vs Email body)
2. Implement conversion function
3. Update file processing to use new format
4. Test emergency email with new format
