# eMonitor

**Version:** v1.0.0
**Status:** Production Release

## Description
eMonitor is a comprehensive personal security and emergency response application designed for Windows Desktop. It seamlessly integrates real-time monitoring, emergency alerting, and secure data logging to ensure personal safety and accountability.

Unlike cloud-only solutions, eMonitor prioritizes data sovereignty—your logs and emergency data remain under your control, sent directly to your configured email or secured local storage, with optional cloud sync for enterprise management.

## Languages & Technologies

*   **Core Logic:** Python 3.12
*   **GUI Framework:** Tkinter (Custom UI)
*   **Backend & Auth:** Supabase (PostgreSQL)
*   **Computer Vision:** OpenCV (cv2) & Pillow (PIL)
*   **System Integration:** Win32 API, Pystray (System Tray)
*   **Security:** AES-256 Encryption & Standard Zip Protection

## Features

### 🚨 Emergency Response System
*   **Instant Panic Button:** Trigger via Hotkey (`Ctrl+Alt+E`) or UI.
*   **Works Offline:** Sends alerts even if you're logged out.
*   **Live Evidence:** Instantly captures location, audio, and screenshots.

### 🛡️ Activity & Camera Monitoring
*   **Auto-Logging:** Tracks active windows and typing usage silently.
*   **📷 Visual Proof:** Captures webcam photos & screenshots at intervals.
*   **Stealth Mode:** Runs primarily in the system background.

### 🔐 Security & Privacy
*   **Data Control:** Logs are sent to *your* email, not a third cloud.
*   **Encryption:** Files can be zipped & password-protected.
*   **Secure Access:** Enforces single-device login security.

## ⚡ Core Capabilities
*   📸 **Screenshots:** Automates screen capture at set intervals.
*   🎥 **Webcam:** Captures photos/video to monitor surroundings.
*   📍 **Location:** Tracks device coordinates (GPS/IP-based).
*   🎙️ **Audio:** Records microphone audio for ambient monitoring.
*   🖥️ **Screen Recording:** Continuous video recording of desktop usage.
*   ⌨️ **Activity:** Logs active app usage and typing intensity metrics.

## Download

[**Download Latest Release (v1.0.0)**](https://github.com/YOUR_USERNAME/emonitor-releases/releases/latest)
*(Replace `YOUR_USERNAME` with your actual GitHub username)*

## Screenshots

| **Dashboard** | **Emergency System** |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/9569b59a-e023-4afb-bd1e-1de6f1c568cd" width="400" alt="Dashboard" /> | <img src="https://github.com/user-attachments/assets/546af2ef-734c-4733-b3aa-dc16d906077e" width="400" alt="Emergency Logo" /> |

---
© 2026 **eCanTech eSolutions**. All Rights Reserved.
