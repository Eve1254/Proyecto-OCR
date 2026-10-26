import io
import json
import threading
import time
import zipfile

import pytest
from fastapi.testclient import TestClient

from ocr_app.app import create_app
from ocr_app.config import LIMITS
from tests.factories import pdf, picture


@pytest.fixture
def client(tmp_path):
    app = create_app(tmp_path / 'jobs')
    with TestClient(app, base_url='http://127.0.0.1', headers={'Origin': 'http://127.0.0.1'}) as c:
        yield c


def test_blocks_external_host_origin_and_missing_origin(client):
    assert client.post('/api/demo', headers={'Origin': 'https://example.com'}).status_code == 403
    assert client.get('/api/health', headers={'Host': 'example.com'}).status_code == 403
    assert client.post('/api/demo', headers={'Origin': 'null'}).status_code == 403


def test_local_interface_and_assets_are_available(client):
    assert client.get('/').status_code == 200
    assert client.get('/styles.css').headers['content-type'].startswith('text/css')
    assert client.get('/app.js').status_code == 200


def test_upload_groups_and_collision_handling(client, tmp_path):
    data = pdf(tmp_path / 'a.pdf', picture()).read_bytes()
    response = client.post('/api/jobs', data={'paths': json.dumps(['Alba/a.pdf', 'Alba/a.pdf']),
        'options': json.dumps({'recognize': False, 'classify': False})},
        files=[('files', ('a.pdf', data, 'application/pdf')), ('files', ('a.pdf', data, 'application/pdf'))])
    assert response.status_code == 200, response.text
    job = response.json()
    assert len({f['relative'] for f in job['files']}) == 2
    assert {f['group'] for f in job['files']} == {'Alba'}


@pytest.mark.parametrize('relative', ['../escape.pdf', 'C:/escape.pdf', 'a/CON.pdf'])
def test_upload_path_rejected(client, relative):
    response = client.post('/api/jobs', data={'paths': json.dumps([relative]),
        'options': json.dumps({'recognize': False, 'classify': False})},
        files={'files': ('a.pdf', b'bad', 'application/pdf')})
    assert response.status_code == 400
    assert client.get('/api/jobs').json() == []


def test_upload_limit_enforced(client, monkeypatch):
    monkeypatch.setattr(LIMITS, 'file_bytes', 8)
    response = client.post('/api/jobs', data={'options': json.dumps({'recognize': False, 'classify': False})},
        files={'files': ('a.pdf', b'0123456789', 'application/pdf')})
    assert response.status_code == 413
    assert client.get('/api/jobs').json() == []


def test_demo_real_processing_downloads_and_deletion(client):
    response = client.post('/api/demo')
    assert response.status_code == 200, response.text
    job_id = response.json()['id']
    assert client.get(f'/api/jobs/{job_id}/download/zip').status_code == 404
    assert client.post(f'/api/jobs/{job_id}/start').status_code == 200
    deadline = time.monotonic() + 45
    while time.monotonic() < deadline:
        job = client.get(f'/api/jobs/{job_id}').json()
        if job['status'] not in {'ready', 'running'}:
            break
        time.sleep(.1)
    assert job['status'] == 'completed_with_errors', job
    assert {g['state'] for g in job['groups']} == {'match', 'no_match', 'review'}
    response = client.get(f'/api/jobs/{job_id}/download/zip')
    assert zipfile.ZipFile(io.BytesIO(response.content)).testzip() is None
    assert client.get(f'/api/jobs/{job_id}/download/excel').content[:2] == b'PK'
    assert client.post(f'/api/jobs/{job_id}/start').status_code == 409
    assert client.delete(f'/api/jobs/{job_id}').status_code == 200


def test_one_job_at_a_time_and_no_deletion_while_running(client, monkeypatch):
    import ocr_app.jobs as jobs_module
    entered, release = threading.Event(), threading.Event()
    def slow(store, job_id, cancelled):
        entered.set()
        release.wait(10)
    monkeypatch.setattr(jobs_module, 'run_pipeline', slow)
    first = client.post('/api/demo').json()['id']
    second = client.post('/api/demo').json()['id']
    try:
        assert client.post(f'/api/jobs/{first}/start').status_code == 200
        assert entered.wait(5)
        assert client.post(f'/api/jobs/{second}/start').status_code == 409
        assert client.delete(f'/api/jobs/{first}').status_code == 409
        assert client.post(f'/api/jobs/{first}/cancel').status_code == 200
    finally:
        release.set()
