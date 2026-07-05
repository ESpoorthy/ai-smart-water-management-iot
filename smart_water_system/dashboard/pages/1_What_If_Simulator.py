"""
Multipage stub — What-If Demand & Savings Simulator
Delegates entirely to dashboard/what_if_simulator.py
"""
import sys
import os

# Ensure smart_water_system root is on path and is the working directory
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from dashboard.what_if_simulator import main
main()
