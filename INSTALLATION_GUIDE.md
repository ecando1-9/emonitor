# eMonitor Installation Guide

## 1. Prerequisites
- **Python**: You must have Python installed on the target machine. [Download Python](https://www.python.org/downloads/).
  - **IMPORTANT**: Check "Add Python to PATH" during installation.

## 2. Installation on New Laptop
1.  **Copy Files**: Copy the entire `emoniter` project folder to the new computer.
2.  **Open Folder**: Navigate to the folder.
3.  **Run Setup**: Double-click `setup_wizard.py` (or run `python setup_wizard.py` in cmd/terminal).
4.  **Wizard**: 
    - Check "Install Dependencies" (Required for first run).
    - Check "Create 'Emergency Alert' Desktop Shortcut".
    - Click "Start Installation".
5.  **Finish**: Once complete, closes the wizard.

## 3. Features
- **Emergency Shortcut**: A shortcut "Emergency Alert" is created on the Desktop.
  - One-click activation.
  - Works even if the app is closed (auto-launches app).
- **Auto-Login**: If you select "Remember my credentials" on the login screen, the app will auto-login during emergency triggers.

## 4. Uninstallation
- Simply delete the project folder and the Desktop shortcut.
- Data is stored in `app_data` inside the project folder.
