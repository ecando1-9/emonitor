"""
Desktop shortcut management for emergency mode.
Creates/removes Windows desktop shortcut for emergency alert.
Supports custom icons through upload or predefined selections.
"""
import os
import sys
import traceback
from logger_setup import log

def get_predefined_icons():
    """
    Returns a dictionary of predefined icon options.
    These map to Windows system icons or custom generated icons.
    """
    return {
        "Emergency Red Alert": {
            "description": "Bright red circle with exclamation mark",
            "type": "generated",
            "generator": "create_emergency_icon"
        },
        "Warning Yellow": {
            "description": "Yellow warning icon",
            "type": "system",
            "path": "%SystemRoot%\\System32\\shell32.dll,28"  # Yellow warning
        },
        "Alert Blue": {
            "description": "Blue alert icon",
            "type": "system",
            "path": "%SystemRoot%\\System32\\shell32.dll,238"  # Blue alert
        },
        "Stop Sign Red": {
            "description": "Stop sign (red circle with stop symbol)",
            "type": "system",
            "path": "%SystemRoot%\\System32\\shell32.dll,302"  # Stop icon
        },
        "Windows Default": {
            "description": "Windows default application icon",
            "type": "system",
            "path": "%SystemRoot%\\System32\\shell32.dll,1"  # Default app icon
        }
    }

def validate_icon_file(file_path):
    """
    Validates that a file is a valid icon file.
    Supports .ico, .png, .jpg formats.
    
    Args:
        file_path: Path to the icon file
    
    Returns:
        Tuple (is_valid, error_message)
    """
    if not file_path or not os.path.exists(file_path):
        return False, "File does not exist"
    
    if not os.path.isfile(file_path):
        return False, "Path is not a file"
    
    # Check file size (max 10 MB)
    file_size = os.path.getsize(file_path)
    if file_size == 0:
        return False, "File is empty"
    if file_size > 10 * 1024 * 1024:
        return False, "File is too large (max 10 MB)"
    
    # Check file extension
    valid_extensions = {'.ico', '.png', '.jpg', '.jpeg', '.bmp', '.gif'}
    _, ext = os.path.splitext(file_path.lower())
    if ext not in valid_extensions:
        return False, f"Invalid file type. Supported: {', '.join(valid_extensions)}"
    
    # Try to open and validate the image
    try:
        from PIL import Image
        img = Image.open(file_path)
        img.verify()
        
        # Check minimum dimensions
        if img.width < 16 or img.height < 16:
            return False, "Image must be at least 16x16 pixels"
        
        # Check maximum dimensions (reasonable for icons)
        if img.width > 4096 or img.height > 4096:
            return False, "Image is too large (max 4096x4096)"
        
        log.info(f"Icon validation passed: {file_path} ({img.width}x{img.height})")
        return True, None
    except ImportError:
        log.warning("PIL not available for icon validation, allowing file anyway")
        return True, None
    except Exception:
        log.debug(traceback.format_exc())
        return False, "Invalid image file"

def copy_icon_to_app_directory(icon_path, custom_name="emergency_alert_custom"):
    """
    Copies a custom icon to the application directory.
    
    Args:
        icon_path: Path to the icon file
        custom_name: Base name for the copied icon
    
    Returns:
        Path to the copied icon in app directory, or None if failed
    """
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        _, ext = os.path.splitext(icon_path)
        dest_path = os.path.join(script_dir, f"{custom_name}{ext}")
        
        # Copy the file
        import shutil
        shutil.copy2(icon_path, dest_path)
        
        if os.path.exists(dest_path):
            log.info("Icon copied to app directory")
            return dest_path
        else:
            log.error("Failed to copy icon to app directory")
            log.debug(f"Destination path: {dest_path}")
            return None
    except Exception:
        log.error("Failed to copy icon file")
        log.debug(traceback.format_exc())
        return None

def create_emergency_icon():
    """Creates an emergency icon file (red circle with exclamation) for the shortcut."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(script_dir, "emergency_alert.ico")
        
        # Create multiple sizes for ICO file (Windows needs multiple sizes)
        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
        images = []
        
        for size in sizes:
            # Create image with transparent background
            img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # Draw red circle background (crimson red)
            margin = max(2, size // 20)  # Proportional margin
            circle_coords = [margin, margin, size - margin, size - margin]
            draw.ellipse(circle_coords, fill=(220, 20, 60), outline=(180, 0, 0), width=max(1, size // 50))
            
            # Draw white exclamation mark
            # Try to get a good font
            font_size = int(size * 0.6)  # Proportional font size
            font = None
            
            # Try different font paths
            font_paths = [
                "C:/Windows/Fonts/arial.ttf",
                "C:/Windows/Fonts/arialbd.ttf",  # Arial Bold
                "C:/Windows/Fonts/calibri.ttf",
                "C:/Windows/Fonts/calibrib.ttf",  # Calibri Bold
                "arial.ttf"
            ]
            
            for font_path in font_paths:
                try:
                    font = ImageFont.truetype(font_path, font_size)
                    break
                except:
                    continue
            
            if font is None:
                # Use default font
                try:
                    font = ImageFont.load_default()
                except:
                    pass
            
            # Draw exclamation mark "!"
            text = "!"
            try:
                # Get text bounding box
                if hasattr(draw, 'textbbox'):
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                else:
                    # Fallback for older PIL
                    text_width = size // 2
                    text_height = size // 2
            except:
                text_width = size // 2
                text_height = size // 2
            
            # Center the text
            x = (size - text_width) // 2
            y = (size - text_height) // 2 - int(size * 0.05)  # Slightly above center
            
            # Draw the exclamation mark
            try:
                # Try with anchor parameter (newer PIL)
                draw.text((x, y), text, fill=(255, 255, 255), font=font, anchor="mm")
            except:
                # Fallback for older PIL versions
                draw.text((x, y), text, fill=(255, 255, 255), font=font)
            
            # For larger sizes, also draw a dot below the exclamation mark
            if size >= 48:
                dot_size = max(2, size // 25)
                dot_y = y + text_height + int(size * 0.08)
                dot_x = size // 2
                draw.ellipse([dot_x - dot_size, dot_y - dot_size, dot_x + dot_size, dot_y + dot_size], 
                           fill=(255, 255, 255))
            
            images.append(img)
        
        # Save as ICO file with all sizes
        try:
            # Save the first image (largest) as ICO with all sizes
            # Pillow's ICO format expects sizes as a list of tuples
            ico_sizes = [(img.width, img.height) for img in images]
            images[0].save(icon_path, format="ICO", sizes=ico_sizes)
            log.info(f"Successfully created emergency icon with {len(images)} sizes: {icon_path}")
            
            # Verify the file was created and has content
            if os.path.exists(icon_path):
                file_size = os.path.getsize(icon_path)
                if file_size > 0:
                    log.info(f"Icon file created successfully ({file_size} bytes)")
                    return icon_path
                else:
                    log.warning("Icon file was created but appears to be empty")
            else:
                log.warning("Icon file was not created")
                return None
        except Exception as ico_error:
            log.warning("Failed to save as ICO, trying PNG fallback")
            log.debug(f"ICO save error: {ico_error}")
            # Fallback: Save as PNG (Windows can use PNG for icons too)
            png_path = icon_path.replace('.ico', '.png')
            try:
                images[0].save(png_path, format="PNG")
                if os.path.exists(png_path):
                    log.info(f"Created emergency icon as PNG: {png_path}")
                    return png_path
            except Exception as png_error:
                log.warning("Failed to save as PNG")
                log.debug(f"PNG save error: {png_error}")
                return None
        
    except ImportError:
        log.warning("PIL/Pillow not available. Icon creation requires Pillow: pip install Pillow")
        return None
    except Exception:
        log.error("Failed to create custom icon")
        log.debug(traceback.format_exc())
        return None

def get_desktop_path():
    """Get the Windows desktop path."""
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        )
        desktop = winreg.QueryValueEx(key, "Desktop")[0]
        winreg.CloseKey(key)
        return desktop
    except Exception as e:
        log.error("Failed to get desktop path")
        log.debug(traceback.format_exc())
        # Fallback to user's Desktop folder
        return os.path.join(os.path.expanduser("~"), "Desktop")

def create_emergency_shortcut(custom_icon_path=None, icon_type="generated"):
    """
    Creates a desktop shortcut for emergency alert.
    
    Args:
        custom_icon_path: Optional path to a custom icon file
        icon_type: Type of icon - "generated", "predefined", or "custom"
    
    Returns:
        True if successful, False otherwise
    """
    try:
        import win32com.client
    except ImportError:
        log.error("pywin32 not installed. Cannot create desktop shortcut.")
        log.error("Please install pywin32: pip install pywin32")
        return False
    
    try:
        desktop_path = get_desktop_path()
        shortcut_path = os.path.join(desktop_path, "Emergency Alert.lnk")
        
        # Get the script directory
        if getattr(sys, 'frozen', False):
             script_dir = os.path.dirname(sys.executable)
        else:
             script_dir = os.path.dirname(os.path.abspath(__file__))
        
        if getattr(sys, 'frozen', False):
            # APP IS FROZEN (EXE)
            # Create shortcut to the EXE itself with --emergency argument
            target_path = sys.executable
            arguments = "--emergency"
            log.info(f"Creating shortcut to EXE: {target_path} {arguments}")
        else:
            # APP IS RUNNING AS SCRIPT (DEV MODE)
            # Prefer VBScript wrapper (completely silent), fallback to batch file
            vbs_file = os.path.join(script_dir, "start_emergency_alert.vbs")
            bat_file = os.path.join(script_dir, "start_emergency_alert.bat")
            trigger_script = os.path.join(script_dir, "trigger_emergency.py")
            arguments = ""

            # Determine which file to use
            if os.path.exists(vbs_file):
                target_path = vbs_file
                log.info("Using VBScript wrapper for completely silent execution")
            elif os.path.exists(bat_file):
                target_path = bat_file
                log.info("Using batch file for emergency alert")
            else:
                log.error("Emergency alert script not found")
                log.debug(f"Checked paths for alert script: {vbs_file}, {bat_file}")
                return False
            
            if not os.path.exists(trigger_script):
                log.warning("trigger_emergency.py not found in application directory")
                log.debug(f"Checked trigger script path: {trigger_script}")
                # Continue anyway - the batch/vbs will handle the error
        
        # Determine icon path
        icon_path = None
        
        if icon_type == "custom" and custom_icon_path:
            # Validate custom icon
            is_valid, error_msg = validate_icon_file(custom_icon_path)
            if is_valid:
                # Copy icon to app directory
                icon_path = copy_icon_to_app_directory(custom_icon_path, "emergency_alert_custom")
            else:
                log.warning(f"Custom icon validation failed: {error_msg}. Using default.")
        
        if not icon_path:
            # --- Check for User Provided Logo ---
            user_logo_ico_name = "emergency_logo.ico"
            user_logo_png_name = "emergency_logo.png"
            
            # Paths to check (Bundle first, then script dir)
            paths_to_check = []
            if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                paths_to_check.append(sys._MEIPASS)
            paths_to_check.append(script_dir)
            
            for check_dir in paths_to_check:
                ico_path = os.path.join(check_dir, user_logo_ico_name)
                png_path = os.path.join(check_dir, user_logo_png_name)
                
                if os.path.exists(ico_path):
                    icon_path = ico_path
                    log.info(f"Using user-provided emergency logo (ico): {icon_path}")
                    break
                elif os.path.exists(png_path):
                    log.info(f"Found user-provided emergency logo (png): {png_path}. Converting to ICO...")
                    try:
                        from PIL import Image
                        img = Image.open(png_path)
                        # Save converted icon to app_data or temp, NOT Program Files (might be read-only)
                        # But wait, desktop shortcut needs a permanent path.
                        # If we are in _MEIPASS, we must extract it to a permanent place.
                        
                        target_ico_name = "emergency_logo_converted.ico"
                        if getattr(sys, 'frozen', False):
                             # Need a stable path: Config/App_Data dir
                             from config import DATA_DIR
                             icon_path = os.path.join(DATA_DIR, target_ico_name)
                        else:
                             icon_path = os.path.join(script_dir, target_ico_name)

                        img.save(icon_path, format="ICO", sizes=[(256,256), (128,128), (64,64), (48,48), (32,32), (16,16)])
                        log.info(f"Converted PNG to ICO: {icon_path}")
                        break
                    except Exception as e:
                        log.error(f"Failed to convert user PNG to ICO: {e}")
                        # Keep looking or fail
            
            # If we simply found an existing ICO in a temp folder (_MEIPASS), we should probably copy it out
            # because _MEIPASS is deleted when app closes, breaking the shortcut icon.
            if icon_path and hasattr(sys, '_MEIPASS') and sys._MEIPASS in icon_path:
                 try:
                     from config import DATA_DIR
                     if not os.path.exists(DATA_DIR): os.makedirs(DATA_DIR)
                     new_icon_path = os.path.join(DATA_DIR, os.path.basename(icon_path))
                     import shutil
                     shutil.copy2(icon_path, new_icon_path)
                     icon_path = new_icon_path
                     log.info(f"Copied temp icon to stable path: {icon_path}")
                 except Exception as copy_err:
                     log.warning(f"Failed to copy icon from temp bundle: {copy_err}")
                     # Shortcut will break on restart if we use temp path
            
            if not icon_path: 
            
            if not icon_path:
                # Try to create/use generated emergency icon
                icon_path = create_emergency_icon()
        
        if not icon_path or not os.path.exists(icon_path):
            log.warning("Custom icon not available, using Windows default alert icon")
            # Fallback to Windows system icon (shell32.dll icon index 238 is a warning/alert icon)
            icon_path = "%SystemRoot%\\System32\\shell32.dll,238"
        else:
            # Make sure the path is absolute for the shortcut
            if not os.path.isabs(icon_path):
                icon_path = os.path.abspath(icon_path)
            log.info(f"Using icon: {icon_path}")
        
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_path
        shortcut.Arguments = arguments
        shortcut.WorkingDirectory = script_dir
        shortcut.Description = "Emergency Alert - eMonitor - Completely silent execution"
        shortcut.IconLocation = icon_path
        # Run minimized/hidden to ensure no windows appear
        # 7 = Minimized (for batch files), VBScript runs hidden by default
        shortcut.WindowStyle = 7  # 7 = Minimized, 1 = Normal, 3 = Maximized
        shortcut.save()
        
        # Verify the icon was set
        if hasattr(shortcut, 'IconLocation') and shortcut.IconLocation:
            log.info(f"Shortcut icon set to: {shortcut.IconLocation}")
        else:
            log.warning("Icon location may not have been set correctly")
        
        log.info(f"Created emergency alert desktop shortcut: {shortcut_path}")
        return True
    except Exception:
        log.error("Failed to create desktop shortcut")
        log.debug(traceback.format_exc())
        return False

# removed empty duplicate `create_emergency_shortcut` definition (was causing syntax error)
def remove_emergency_shortcut():
    """Removes the desktop shortcut for emergency alert."""
    try:
        desktop_path = get_desktop_path()
        shortcut_path = os.path.join(desktop_path, "Emergency Alert.lnk")
        
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)
            log.info(f"Removed emergency alert desktop shortcut: {shortcut_path}")
            return True
        else:
            log.info("Emergency alert shortcut not found (already removed)")
            return True
    except Exception as e:
        log.error("Failed to remove desktop shortcut")
        log.debug(traceback.format_exc())
        return False

def check_shortcut_exists():
    """Checks if the emergency alert shortcut exists."""
    try:
        desktop_path = get_desktop_path()
        shortcut_path = os.path.join(desktop_path, "Emergency Alert.lnk")
        return os.path.exists(shortcut_path)
    except Exception as e:
        log.error("Failed to check shortcut existence")
        log.debug(traceback.format_exc())
        return False

