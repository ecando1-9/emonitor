# 🎨 Custom Icons Guide

I have updated the application to support custom icons for both the main app and the emergency shortcut.

## 1. Main Application Icon
The application now properly sets the Taskbar Icon and Window Icon using `icon.png` found in the application directory.

*   **Requirement**: Ensure a file named `icon.png` exists in the install folder.

## 2. Emergency Shortcut Logo
You can now use your own custom logo for the Emergency Desktop Shortcut!

**How to use:**
1.  Place your logo file in the application folder (`.../projects/emoniter/`).
2.  Name it exactly: `emergency_logo.png` OR `emergency_logo.ico`.
3.  Open the App -> **Settings**.
4.  Navigate to **Emergency Alert Settings**.
5.  Click **Remove Desktop Shortcut** (if one exists).
6.  Click **Create Desktop Shortcut**.

The new shortcut on your desktop will now use your custom logo!

**Note:**
*   Use a square image (e.g., 256x256) for best results.
*   If you provide a `.png`, the app automatically converts it to `.ico` for Windows compatibility.
