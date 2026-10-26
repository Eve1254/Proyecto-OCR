import threading
import time

from ocr_app.app import create_app
from tests.test_public import public_app, session


def wait_done(client, job_id, timeout=25):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        job = client.get('/api/jobs/' + job_id).json()
        if job['status'] not in {'queued', 'running'}:
            return job
        time.sleep(.1)
    raise AssertionError('El trabajo no terminó dentro del límite de la prueba.')


def test_public_demo_uses_worker_and_produces_downloads(public_app):
    _, first, second = public_app
    session(first)
    session(second)
    job_id = first.post('/api/demo').json()['id']
    result = first.post('/api/jobs/' + job_id + '/start')
    assert result.status_code == 200
    assert result.json()['status'] in {'queued', 'running'}
    job = wait_done(first, job_id)
    assert job['status'] == 'completed_with_errors', job
    assert {g['state'] for g in job['groups']} == {'match', 'no_match', 'review'}
    assert first.get('/api/jobs/' + job_id + '/download/zip').content[:2] == b'PK'
    assert second.get('/api/jobs/' + job_id + '/download/zip').status_code == 404


def test_pending_job_can_be_cancelled_without_starting(public_app, monkeypatch):
    app, first, _ = public_app
    session(first)
    manager = app.state.manager
    entered, release = threading.Event(), threading.Event()
    original = manager._run
    def held(job_id):
        entered.set()
        release.wait(10)
        original(job_id)
    monkeypatch.setattr(manager, '_run', held)
    first_id = first.post('/api/demo').json()['id']
    second_id = first.post('/api/demo').json()['id']
    try:
        assert first.post('/api/jobs/' + first_id + '/start').status_code == 200
        assert entered.wait(3)
        assert first.post('/api/jobs/' + second_id + '/start').status_code == 200
        assert first.get('/api/jobs/' + second_id).json()['status'] == 'queued'
        assert first.post('/api/jobs/' + second_id + '/cancel').status_code == 200
        assert first.get('/api/jobs/' + second_id).json()['status'] == 'cancelled'
    finally:
        release.set()


def test_worker_timeout_releases_capacity(public_app):
    app, first, _ = public_app
    session(first)
    app.state.settings.job_seconds = .01
    job_id = first.post('/api/demo').json()['id']
    first.post('/api/jobs/' + job_id + '/start')
    job = wait_done(first, job_id)
    assert job['status'] == 'failed'
    assert job['artifacts'] == []
    assert 'tiempo' in job['errors'][-1]['message'].lower()
    assert app.state.manager.active is None


def test_worker_memory_limit_releases_capacity(public_app):
    app, first, _ = public_app
    session(first)
    app.state.settings.worker_memory_bytes = 1
    job_id = first.post('/api/demo').json()['id']
    first.post('/api/jobs/' + job_id + '/start')
    job = wait_done(first, job_id)
    assert job['status'] == 'failed'
    assert 'memoria' in job['errors'][-1]['message'].lower()


def test_disappearing_temporary_file_does_not_fail_job(public_app, monkeypatch):
    app, first, _ = public_app
    session(first)
    job_id = first.post('/api/demo').json()['id']
    target = app.state.store.directory(job_id) / 'vanishing.tmp'
    target.write_bytes(b'temporary')
    from pathlib import Path
    real_stat = Path.stat
    calls = 0
    def disappearing(path, *args, **kwargs):
        nonlocal calls
        if path == target:
            calls += 1
            if calls == 2:
                target.unlink()
                raise FileNotFoundError('The atomic writer removed its temporary file')
        return real_stat(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'stat', disappearing)
    first.post('/api/jobs/' + job_id + '/start')
    job = wait_done(first, job_id)
    assert job['status'] == 'completed_with_errors', job


def test_restarting_public_store_interrupts_queue(tmp_path):
    from ocr_app.storage import JobStore
    store = JobStore(tmp_path)
    job = store.create({}, status='queued', owner='example')
    restarted = JobStore(tmp_path)
    assert restarted.get(job['id'])['status'] == 'interrupted'
