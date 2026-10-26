import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from ocr_app.app import create_app


@pytest.fixture
def public_app(tmp_path, monkeypatch):
    monkeypatch.setenv('OCR_MODE', 'public')
    monkeypatch.setenv('OCR_PUBLIC_ORIGIN', 'https://pilot.example')
    monkeypatch.setenv('OCR_SESSION_SECRET', 'a-test-secret-with-more-than-32-characters')
    app = create_app(tmp_path / 'public-jobs')
    with TestClient(app, base_url='https://pilot.example', headers={'Origin': 'https://pilot.example'}) as first:
        second = TestClient(app, base_url='https://pilot.example', headers={'Origin': 'https://pilot.example'})
        yield app, first, second
        second.close()


def session(client):
    result = client.get('/api/session')
    assert result.status_code == 200, result.text
    return result


def test_public_cookie_and_health(public_app):
    _, first, _ = public_app
    health = first.get('/api/health')
    assert health.status_code == 200
    assert health.json()['local'] is False
    assert health.json()['limits']['files'] == 20
    response = session(first)
    cookie = response.headers['set-cookie'].lower()
    assert 'httponly' in cookie and 'secure' in cookie and 'samesite=strict' in cookie
    assert 'domain=' not in cookie
    assert response.json()['retention_seconds'] == 3600


def test_all_job_routes_are_private_to_the_browser(public_app):
    _, first, second = public_app
    session(first)
    session(second)
    response = first.post('/api/demo')
    assert response.status_code == 200, response.text
    job = response.json()
    assert 'owner' not in job
    assert len(first.get('/api/jobs').json()) == 1
    assert second.get('/api/jobs').json() == []
    for method, suffix in [('get', ''), ('post', '/start'), ('post', '/cancel'),
                           ('delete', ''), ('get', '/download/zip'), ('get', '/download/excel'),
                           ('get', '/evidence/123/image.png')]:
        response = getattr(second, method)('/api/jobs/' + job['id'] + suffix)
        assert response.status_code == 404, (method, suffix, response.text)
    assert first.get('/api/jobs/' + job['id']).status_code == 200


def test_forged_or_missing_cookie_does_not_grant_access(public_app):
    _, first, second = public_app
    session(first)
    job_id = first.post('/api/demo').json()['id']
    assert second.get('/api/jobs/' + job_id).status_code == 401
    cookie = next(iter(first.cookies.values()))
    second.headers['Cookie'] = '__Host-ocr_session=' + cookie[:-1] + ('a' if cookie[-1] != 'a' else 'b')
    assert second.get('/api/jobs/' + job_id).status_code == 401


def test_public_rejects_foreign_host_origin_and_cross_site_fetch(public_app):
    _, first, _ = public_app
    session(first)
    assert first.get('/api/health', headers={'Host': 'evil.example'}).status_code == 403
    for origin in ['https://evil.example', 'null', 'http://pilot.example']:
        assert first.post('/api/demo', headers={'Origin': origin}).status_code == 403
    assert first.get('/api/jobs', headers={'Sec-Fetch-Site': 'cross-site'}).status_code == 403
    assert first.post('/api/demo', headers={'Content-Length': str(40 * 1024**2)}).status_code == 413


def test_expired_jobs_are_inaccessible_and_removed(public_app):
    app, first, _ = public_app
    session(first)
    job_id = first.post('/api/demo').json()['id']
    job = app.state.store.get(job_id)
    job['created'] = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    app.state.store.save(job)
    assert first.get('/api/jobs/' + job_id).status_code == 404
    assert first.get('/api/jobs').json() == []
    app.state.access.cleanup(app.state.manager)
    assert not app.state.store.directory(job_id).exists()


def test_legacy_jobs_without_owner_are_never_visible(public_app):
    app, first, _ = public_app
    legacy = app.state.store.create({})
    session(first)
    assert first.get('/api/jobs').json() == []
    assert first.get('/api/jobs/' + legacy['id']).status_code == 404


def test_browser_job_quota_is_enforced(public_app):
    _, first, second = public_app
    session(first)
    session(second)
    for _ in range(3):
        assert first.post('/api/demo').status_code == 200
    assert first.post('/api/demo').status_code == 429
    assert second.post('/api/demo').status_code == 200


def test_public_upload_limits_apply_before_creating_job(public_app):
    _, first, _ = public_app
    session(first)
    response = first.post('/api/jobs', data={'options': json.dumps({'recognize': False, 'classify': False})},
                          files={'files': ('test.pdf', b'x' * (10 * 1024**2 + 1), 'application/pdf')})
    assert response.status_code == 413
    assert first.get('/api/jobs').json() == []


@pytest.mark.parametrize('changes', [
    {'OCR_SESSION_SECRET': ''}, {'OCR_PUBLIC_ORIGIN': 'http://example.com'},
    {'OCR_PUBLIC_ORIGIN': 'https://example.com/a'}, {'OCR_PUBLIC_ORIGIN': ''},
])
def test_public_misconfiguration_fails_closed(tmp_path, monkeypatch, changes):
    monkeypatch.setenv('OCR_MODE', 'public')
    monkeypatch.setenv('OCR_PUBLIC_ORIGIN', 'https://pilot.example')
    monkeypatch.delenv('RENDER_EXTERNAL_HOSTNAME', raising=False)
    monkeypatch.setenv('OCR_SESSION_SECRET', 'a-valid-long-secret-for-testing-32-characters')
    for key, value in changes.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError):
        create_app(tmp_path / 'jobs')
