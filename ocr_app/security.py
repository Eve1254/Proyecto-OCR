from urllib.parse import urlsplit

from starlette.responses import JSONResponse

from .config import LIMITS


class BodyTooLarge(Exception):
    pass


class LocalOnlyMiddleware:
    """Block DNS rebinding/cross-site writes and bound multipart before parsing."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http':
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope['headers']}
        host = headers.get('host', '')
        try:
            parsed_host = urlsplit('http://' + host)
            allowed = parsed_host.hostname in {'127.0.0.1', 'localhost'} and parsed_host.netloc == host and not parsed_host.username
            # Force parsing of the port to reject malformed values.
            _ = parsed_host.port
        except ValueError:
            allowed = False
        if not allowed:
            return await JSONResponse({'detail': 'Acceso permitido solo desde este computador.'}, 403)(scope, receive, send)
        if scope['method'] not in {'GET', 'HEAD', 'OPTIONS'}:
            if headers.get('origin') != 'http://' + host:
                return await JSONResponse({'detail': 'Origen no autorizado. Abre la aplicación en su dirección local.'}, 403)(scope, receive, send)
        if scope['path'].startswith('/api/') and headers.get('sec-fetch-site') == 'cross-site':
            return await JSONResponse({'detail': 'Acceso externo no permitido.'}, 403)(scope, receive, send)
        maximum = LIMITS.job_bytes + LIMITS.reference_bytes + 5 * 1024 * 1024
        try:
            if int(headers.get('content-length', '0')) > maximum:
                return await JSONResponse({'detail': 'El lote supera el tamaño máximo permitido.'}, 413)(scope, receive, send)
        except ValueError:
            return await JSONResponse({'detail': 'Tamaño de petición no válido.'}, 400)(scope, receive, send)
        received = 0
        started = False

        async def bounded_receive():
            nonlocal received
            event = await receive()
            if event['type'] == 'http.request':
                received += len(event.get('body', b''))
                if received > maximum:
                    raise BodyTooLarge()
            return event

        async def safe_send(event):
            nonlocal started
            if event['type'] == 'http.response.start':
                started = True
                event.setdefault('headers', []).extend([
                    (b'x-content-type-options', b'nosniff'),
                    (b'referrer-policy', b'no-referrer'),
                    (b'content-security-policy', b"default-src 'self'; img-src 'self' blob:; style-src 'self'; script-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'"),
                    (b'cache-control', b'no-store'),
                ])
            await send(event)
        try:
            await self.app(scope, bounded_receive, safe_send)
        except BodyTooLarge:
            if not started:
                await JSONResponse({'detail': 'El lote supera el tamaño máximo permitido.'}, 413)(scope, receive, send)
