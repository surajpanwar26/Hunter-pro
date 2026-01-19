import time
from modules.dashboard import metrics


def test_append_and_average():
    metrics.reset_all()
    metrics.append_sample('t1', 1.0)
    metrics.append_sample('t1', 3.0)
    avg = metrics.get_average('t1')
    assert 1.9 < avg < 2.1


def test_inc_and_get():
    metrics.reset_all()
    metrics.inc('counter')
    metrics.inc('counter', 2)
    data = metrics.get_metrics()
    assert data['counter'] == 3


def test_estimate_eta():
    eta = metrics.estimate_eta(2.5, 4)
    assert eta == 10.0


def test_get_sample_stats_and_eta():
    metrics.reset_all()
    metrics.append_sample('job_time', 1.2)
    metrics.append_sample('job_time', 1.8)
    stats = metrics.get_sample_stats('job_time')
    assert stats['count'] == 2
    assert abs(stats['avg'] - 1.5) < 1e-6
    # avg = 1.5, jobs_processed=1, max_jobs=5 -> remaining 4 * 1.5 = 6.0
    eta = metrics.get_eta(1, 5)
    assert abs(eta - 6.0) < 1e-6
