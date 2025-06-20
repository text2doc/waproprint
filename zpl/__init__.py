"""
ZPL (Zebra Programming Language) utilities for generating and processing ZPL code.

This package provides tools for working with ZPL, including conversion from HTML to ZPL,
ZPL to PDF, and direct printing to Zebra label printers.
"""

__version__ = "0.1.0"

# Import key functions and classes to make them available at the package level
from .zpl_printer import print_zpl_to_network_printer, list_zpl_files
from .html_to_zpl import html_to_zpl
from .zpl_to_pdf import zpl_to_pdf

__all__ = [
    'print_zpl_to_network_printer',
    'list_zpl_files',
    'html_to_zpl',
    'zpl_to_pdf',
]
