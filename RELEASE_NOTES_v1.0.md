# eMonitor v1.0.0 - Official Release

We are excited to announce the first production release of **eMonitor**, a comprehensive emergency response and personal security monitoring application.

![Dashboard Preview](PLACEHOLDER_FOR_DASHBOARD_IMAGE_URL)
*(Upload your dashboard image to GitHub and paste the link here)*

## 🚨 Key Features

### 1. Advanced Emergency System
*   **Panic Button:** Trigger emergency mode instantly via `Ctrl+Alt+E` (customizable) or the Dashboard button.
*   **Offline Support:** Emergency alerts work even if the user is **logged out** (using fallback secure RPC).
*   **Live Data Streaming:** Captures and emails screenshots, webcam, location, and audio in real-time batches.
*   **Grace Period:** Configurable 5-second countdown to prevent accidental triggers.

### 2. Activity Monitoring
*   **Automated Tracking:** Periodically captures screenshots and active window telemetry.
*   **Smart Analytics:** "Typed Activity" analysis to detect intensity (without keylogging sensitive text).
*   **Stealth Operation:** Runs silently in the background with a System Tray icon.

### 3. Security & Privacy
*   **End-to-End Encryption:** Local files can be encrypted or ZIP-protected before sending.
*   **Data Sovereignty:** All data is sent directly to your configured email or admin panel; nothing is stored on third-party servers you don't control.
*   **Robust Auth:** Supabase-backed secure authentication with single-device enforcement.

## 🛠️ Installation

1.  Download `eMonitor.exe` from the Assets below.
2.  Run the executable.
3.  Log in with your **eCanTech eSolutions** account.
4.  Configure your "Recipient Email" in the Settings tab.

## 📸 Screenshots

| **Dashboard** | **Emergency Mode** |
| :---: | :---: |
| <img src="https://github.com/user-attachments/assets/9569b59a-e023-4afb-bd1e-1de6f1c568cd" width="400" alt="Dashboard" /> | <img src="https://github.com/user-attachments/assets/546af2ef-734c-4733-b3aa-dc16d906077e" width="400" alt="Emergency Logo" /> |

## 📋 Changelog
*   [New] Complete User Dashboard UI with Plan Status.
*   [New] "Stop Monitoring" now auto-flushes pending data.
*   [Fix] Solved "User not logged in" error for emergency alerts.
*   [Fix] Optimized startup performance and single-instance handling.

---
**eCanTech eSolutions** - *Your Safety, Our Priority.*
