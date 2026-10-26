import threading

from ocr_app.demo import create_demo
from ocr_app.processing import run_pipeline
from ocr_app.storage import JobStore


def test_demo_uses_real_engine_and_has_three_distinct_outcomes(tmp_path):
    store = JobStore(tmp_path)
    job = store.create(dict(convert=False, extract=False, recognize=True, classify=True, report=True, evidence=True), demo=True)
    job['files'], job['reference'] = create_demo(store.directory(job['id']))
    store.save(job)
    run_pipeline(store, job['id'], threading.Event())
    result = store.get(job['id'])
    assert {g['state'] for g in result['groups']} == {'match', 'no_match', 'review'}
    assert result['artifacts'] == ['excel', 'zip']
