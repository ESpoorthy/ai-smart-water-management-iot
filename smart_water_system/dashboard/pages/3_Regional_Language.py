"""
Multipage stub — Regional Language Toggle & SMS Bulletin
Delegates entirely to dashboard/regional_language_toggle.py
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from dashboard.regional_language_toggle import main
main()
