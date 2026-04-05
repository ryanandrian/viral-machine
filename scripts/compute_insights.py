"""Compute channel insights dari video_analytics — self-learning engine."""
import sys
sys.path.insert(0, '/home/rad4vm/viral-machine')

from src.analytics.performance_analyzer import PerformanceAnalyzer

result = PerformanceAnalyzer('ryan_andrian').compute_and_store()
print(result)
