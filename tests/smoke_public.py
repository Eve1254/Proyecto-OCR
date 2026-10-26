"""Run inside a 512 MB production container to verify the deployed HTTP contract."""
import io
import json
import time
import urllib.error
import urllib.request
import uuid
import zipfile


def request(path, *, cookie=None, body=None, content_type=None, method='GET'):
    headers = {'Host': 'pilot.example', 'Origin': 'https://pilot.example'}
    if cookie:
        headers['Cookie'] = cookie
    if content_type:
        headers['Content-Type'] = content_type
    req = urllib.request.Request('http://127.0.0.1:8000' + path, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, response.headers, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.headers, error.read()


def finished(cookie, job_id):
    for _ in range(600):
        status, _, body = request('/api/jobs/' + job_id, cookie=cookie)
        assert status == 200, body
        job = json.loads(body)
        if job['status'] not in {'queued', 'running'}:
            return job
        time.sleep(.2)
    raise AssertionError('El lote no finalizó.')


def main():
    for _ in range(60):
        try:
            status, _, raw = request('/api/health')
            if status == 200:
                break
        except (OSError, urllib.error.URLError):
            pass
        time.sleep(.5)
    health = json.loads(raw)
    assert not health['local'] and health['conversion_available'], health
    _, headers, _ = request('/api/session')
    cookie = headers['set-cookie'].split(';')[0]
    _, other_headers, _ = request('/api/session')
    other = other_headers['set-cookie'].split(';')[0]
    status, _, raw = request('/api/demo', cookie=cookie, method='POST')
    assert status == 200, raw
    job_id = json.loads(raw)['id']
    assert request('/api/jobs/' + job_id, cookie=other)[0] == 404
    assert request('/api/jobs/' + job_id + '/start', cookie=cookie, method='POST')[0] == 200
    demo = finished(cookie, job_id)
    assert demo['status'] == 'completed_with_errors', demo
    assert {group['state'] for group in demo['groups']} == {'match', 'no_match', 'review'}
    status, _, data = request('/api/jobs/' + job_id + '/download/zip', cookie=cookie)
    assert status == 200 and zipfile.ZipFile(io.BytesIO(data)).testzip() is None

    source = io.BytesIO()
    with zipfile.ZipFile(source, 'w') as archive:
        archive.writestr('[Content_Types].xml', '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>')
        archive.writestr('_rels/.rels', '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/></Relationships>')
        archive.writestr('word/document.xml', '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Prueba ficticia en servidor</w:t></w:r></w:p><w:sectPr/></w:body></w:document>')
    boundary = uuid.uuid4().hex
    parts = [f'--{boundary}\r\nContent-Disposition: form-data; name="options"\r\n\r\n'.encode(),
             json.dumps({'recognize': False, 'classify': False}).encode(),
             f'\r\n--{boundary}\r\nContent-Disposition: form-data; name="files"; filename="prueba.docx"\r\nContent-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document\r\n\r\n'.encode(),
             source.getvalue(), f'\r\n--{boundary}--\r\n'.encode()]
    status, _, raw = request('/api/jobs', cookie=cookie, method='POST', body=b''.join(parts),
                             content_type='multipart/form-data; boundary=' + boundary)
    assert status == 200, raw
    job_id = json.loads(raw)['id']
    assert request('/api/jobs/' + job_id + '/start', cookie=cookie, method='POST')[0] == 200
    converted = finished(cookie, job_id)
    assert converted['status'] == 'completed', converted
    assert any(file['kind'] == 'pdf' and not file['original'] for file in converted['files'])
    assert request('/api/jobs/' + job_id + '/download/zip', cookie=other)[0] == 404
    assert request('/api/jobs/' + job_id + '/download/excel', cookie=cookie)[0] == 200
    print('HTTP smoke passed: 512 MB container, demo, real DOCX conversion, ZIP, Excel, separate visitors.')


if __name__ == '__main__':
    main()
