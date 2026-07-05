"""
Multipage stub — Community Zone Efficiency Ranking
Delegates entirely to dashboard/community_ranking.py
"""
import sys
import os

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from dashboard.community_ranking import main
main()
