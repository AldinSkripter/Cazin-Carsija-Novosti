# Cleanup helper: hard-delete FB-imported articles + their facebook media + versions, clear fb_ignored
import sys, asyncio
sys.path.insert(0, "/app/backend/tests")
from test_fb_categories import mongo, _cleanup_fb
print(mongo(_cleanup_fb))
