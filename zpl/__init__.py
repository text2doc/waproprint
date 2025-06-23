"""
ZPL (Zebra Programming Language) utilities for generating and processing ZPL code.

This package provides tools for working with ZPL, including conversion from HTML to ZPL,
ZPL to PDF, and direct printing to Zebra label printers.
"""

__version__ = "0.1.0"

# Import key functions and classes to make them available at the package level
from .network_printer import print_zpl_to_network_printer, list_zpl_files
from .zpl_printer import print_zpl, save_zpl_to_file, print_html_from_file
from .html_to_zpl import HtmlToZplConverter
from .zpl_to_pdf import (
    convert_zpl_to_image,
    image_to_pdf,
    convert_zpl_file_to_pdf,
    convert_zpl_string_to_pdf,
    print_pdf,
    create_label_pdf_direct
)

# For backward compatibility, create a default converter instance
_html_to_zpl_converter = None


def html_to_zpl(html_content, **kwargs):
    """
    Convert HTML to ZPL using default converter settings.
    This is a convenience function that creates a temporary HtmlToZplConverter instance.
    """
    global _html_to_zpl_converter
    if _html_to_zpl_converter is None:
        _html_to_zpl_converter = HtmlToZplConverter(**kwargs)
    return _html_to_zpl_converter.convert(html_content)


__all__ = [
    'print_zpl_to_network_printer',
    'list_zpl_files',
    'print_zpl',
    'save_zpl_to_file',
    'print_html_from_file',
    'html_to_zpl',
    'HtmlToZplConverter',
    'zpl_to_pdf',
]
