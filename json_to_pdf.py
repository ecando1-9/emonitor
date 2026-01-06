"""
JSON to PDF Converter for Emergency Data
Converts activity and telemetry JSON files to readable PDF format
"""
import json
import os
from fpdf import FPDF
from datetime import datetime
from logger_setup import log


class EmergencyDataPDF(FPDF):
    """Custom PDF class for emergency data reports"""
    
    def header(self):
        """PDF header with title"""
        self.set_font('Arial', 'B', 16)
        self.set_text_color(220, 20, 60)  # Crimson red for emergency
        self.cell(0, 10, 'EMERGENCY DATA REPORT', 0, 1, 'C')
        self.ln(5)
    
    def footer(self):
        """PDF footer with page number"""
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', 0, 0, 'C')


def json_to_pdf(json_file_path):
    """
    Converts a JSON file to a readable PDF format.
    
    Args:
        json_file_path: Path to the JSON file
    
    Returns:
        Path to the generated PDF file, or None if conversion failed
    """
    try:
        # Read JSON file
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Create PDF
        pdf = EmergencyDataPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        
        # Add metadata
        pdf.set_font('Arial', 'B', 12)
        pdf.set_text_color(0, 0, 0)
        
        # Get filename info
        filename = os.path.basename(json_file_path)
        pdf.cell(0, 10, f'Source File: {filename}', 0, 1)
        pdf.cell(0, 10, f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', 0, 1)
        pdf.ln(5)
        
        # Add JSON data in readable format
        pdf.set_font('Arial', '', 10)
        _add_json_content(pdf, data)
        
        # Generate output filename
        pdf_path = json_file_path.replace('.json', '.pdf')
        
        # Save PDF
        pdf.output(pdf_path)
        log.info(f"Converted JSON to PDF: {pdf_path}")
        
        return pdf_path
        
    except Exception as e:
        log.error(f"Failed to convert JSON to PDF: {e}")
        return None


def _add_json_content(pdf, data, indent=0):
    """
    Recursively adds JSON content to PDF with proper formatting.
    
    Args:
        pdf: FPDF object
        data: JSON data (dict, list, or primitive)
        indent: Current indentation level
    """
    left_margin = 15 + (indent * 8)  # Base margin + indent
    
    if isinstance(data, dict):
        for key, value in data.items():
            try:
                if isinstance(value, (dict, list)):
                    # Section header
                    pdf.set_font('Arial', 'B', 10)
                    pdf.set_left_margin(left_margin)
                    pdf.set_x(left_margin)
                    pdf.multi_cell(0, 6, f'{key}:', border=0)
                    pdf.set_font('Arial', '', 9)
                    _add_json_content(pdf, value, indent + 1)
                else:
                    # Key-value pair
                    pdf.set_font('Arial', '', 9)
                    pdf.set_left_margin(left_margin)
                    pdf.set_x(left_margin)
                    # Combine key and value in one multi_cell
                    text = f'{key}: {str(value)}'
                    pdf.multi_cell(0, 6, text, border=0)
            except Exception as e:
                log.warning(f"Error adding dict item to PDF: {e}")
                continue
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            try:
                if isinstance(item, (dict, list)):
                    pdf.set_font('Arial', 'B', 9)
                    pdf.set_left_margin(left_margin)
                    pdf.set_x(left_margin)
                    pdf.multi_cell(0, 6, f'Item {i}:', border=0)
                    pdf.set_font('Arial', '', 9)
                    _add_json_content(pdf, item, indent + 1)
                else:
                    pdf.set_font('Arial', '', 9)
                    pdf.set_left_margin(left_margin)
                    pdf.set_x(left_margin)
                    pdf.multi_cell(0, 6, f'- {str(item)}', border=0)
            except Exception as e:
                log.warning(f"Error adding list item to PDF: {e}")
                continue
    
    else:
        # Primitive value
        try:
            pdf.set_font('Arial', '', 9)
            pdf.set_left_margin(left_margin)
            pdf.set_x(left_margin)
            pdf.multi_cell(0, 6, str(data), border=0)
        except Exception as e:
            log.warning(f"Error adding primitive to PDF: {e}")
    
    # Reset margin
    pdf.set_left_margin(15)


def convert_emergency_json_files(file_list):
    """
    Converts a list of JSON files to PDF format.
    
    Args:
        file_list: List of file paths
    
    Returns:
        List of converted PDF file paths
    """
    pdf_files = []
    
    for file_path in file_list:
        if file_path.endswith('.json'):
            pdf_path = json_to_pdf(file_path)
            if pdf_path:
                pdf_files.append(pdf_path)
                # Delete original JSON file after conversion
                try:
                    os.remove(file_path)
                    log.info(f"Deleted original JSON file: {file_path}")
                except Exception as e:
                    log.warning(f"Could not delete JSON file: {e}")
        else:
            # Not a JSON file, keep as-is
            pdf_files.append(file_path)
    
    return pdf_files


if __name__ == "__main__":
    # Test conversion
    import sys
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        pdf_file = json_to_pdf(json_file)
        if pdf_file:
            print(f"✅ Converted: {pdf_file}")
        else:
            print("❌ Conversion failed")
    else:
        print("Usage: python json_to_pdf.py <json_file>")
