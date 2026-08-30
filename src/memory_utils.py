"""Peak memory measurement for a single algorithm run.

Two mechanisms are supported and clearly distinguished:
  * tracemalloc  -> peak Python-level allocations during the call (bytes)
  * psutil RSS   -> process resident-set-size delta around the call (bytes),
                    optional, only used if psutil is installed.
"""

import gc
import tracemalloc

try:
    import psutil
    _HAS_PSUTIL = True
except ImportError:
    _HAS_PSUTIL = False


def measure_call(func, *args, **kwargs):
    """Run func(*args, **kwargs) and return (result, metrics_dict).

    metrics_dict contains:
        peak_tracemalloc_bytes : int
        rss_delta_bytes        : int or None (None if psutil unavailable)
    """
    gc.collect()
    proc = psutil.Process() if _HAS_PSUTIL else None
    rss_before = proc.memory_info().rss if proc is not None else None

    tracemalloc.start()
    result = func(*args, **kwargs)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    rss_after = proc.memory_info().rss if proc is not None else None
    rss_delta = (rss_after - rss_before) if proc is not None else None

    metrics = {
        "peak_tracemalloc_bytes": peak,
        "rss_delta_bytes": rss_delta,
    }
    return result, metrics
