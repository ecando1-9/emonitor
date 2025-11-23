"""
Desktop shortcut management for emergency mode.
Creates/removes Windows desktop shortcut for emergency alert.
"""
import os
import sys
from logger_setup import log

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
            log.warning(f"Failed to save as ICO: {ico_error}. Trying PNG fallback...")
            # Fallback: Save as PNG (Windows can use PNG for icons too)
            png_path = icon_path.replace('.ico', '.png')
            try:
                images[0].save(png_path, format="PNG")
                if os.path.exists(png_path):
                    log.info(f"Created emergency icon as PNG: {png_path}")
                    return png_path
            except Exception as png_error:
                log.warning(f"Failed to save as PNG: {png_error}")
                return None
        
    except ImportError:
        log.warning("PIL/Pillow not available. Icon creation requires Pillow: pip install Pillow")
        return None
    except Exception as e:
        log.error(f"Failed to create custom icon: {e}")
        import traceback
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
        log.error(f"Failed to get desktop path: {e}")
        # Fallback to user's Desktop folder
        return os.path.join(os.path.expanduser("~"), "Desktop")

def create_emergency_shortcut():
    """Creates a desktop shortcut for emergency alert."""
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
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Prefer VBScript wrapper (completely silent), fallback to batch file
        vbs_file = os.path.join(script_dir, "start_emergency_alert.vbs")
        bat_file = os.path.join(script_dir, "start_emergency_alert.bat")
        trigger_script = os.path.join(script_dir, "trigger_emergency.py")
        
        # Determine which file to use
        if os.path.exists(vbs_file):
            target_file = vbs_file
            log.info("Using VBScript wrapper for completely silent execution")
        elif os.path.exists(bat_file):
            target_file = bat_file
            log.info("Using batch file for emergency alert")
        else:
            log.error(f"Emergency alert script not found. Checked: {vbs_file}, {bat_file}")
            return False
        
        if not os.path.exists(trigger_script):
            log.warning(f"trigger_emergency.py not found: {trigger_script}")
            # Continue anyway - the batch/vbs will handle the error
        
        # Try to create/use emergency icon
        icon_path = create_emergency_icon()
        if not icon_path or not os.path.exists(icon_path):
            log.warning("Custom icon not available, using Windows default alert icon")
            # Fallback to Windows system icon (shell32.dll icon index 238 is a warning/alert icon)
            # Also try index 27 (exclamation mark) or 241 (warning sign)
            icon_path = "%SystemRoot%\\System32\\shell32.dll,238"
        else:
            # Make sure the path is absolute for the shortcut
            if not os.path.isabs(icon_path):
                icon_path = os.path.abspath(icon_path)
            log.info(f"Using icon: {icon_path}")
        
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.Targetpath = target_file
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
    except Exception as e:
        log.error(f"Failed to create desktop shortcut: {e}")
        return False

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
        log.error(f"Failed to remove desktop shortcut: {e}")
        return False

def check_shortcut_exists():
    """Checks if the emergency alert shortcut exists."""
    try:
        desktop_path = get_desktop_path()
        shortcut_path = os.path.join(desktop_path, "Emergency Alert.lnk")
        return os.path.exists(shortcut_path)
    except Exception as e:
        log.error(f"Failed to check shortcut existence: {e}")
        return False

