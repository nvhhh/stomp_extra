"""HTTP boundary checks without opening MIDI or changing a pedal."""
import http.client
import sys
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from editor.server import Handler, ThreadingHTTPServer, APP


class PagesBridgeTests(unittest.TestCase):
    def setUp(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        self.worker = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.worker.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join()

    def request(self, method, path, origin=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        headers = {'Origin': origin} if origin else {}
        conn.request(method, path, body='{}' if method == 'POST' else None, headers=headers)
        response = conn.getresponse()
        result = response.status, dict(response.getheaders()), response.read()
        conn.close()
        return result

    def test_hosted_origin_requires_opt_in(self):
        self.assertEqual(self.request('GET', '/api/catalog', 'https://nvhhh.github.io')[0], 403)
        self.server.pages_origin = 'https://nvhhh.github.io'
        status, headers, body = self.request('GET', '/api/catalog', self.server.pages_origin)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Access-Control-Allow-Origin'], self.server.pages_origin)
        self.assertIn(b'modules', body)

    def test_foreign_writes_never_reach_app(self):
        self.server.pages_origin = 'https://nvhhh.github.io'
        with patch.object(APP, 'cc') as cc:
            self.assertEqual(self.request('POST', '/api/cc', 'https://example.com')[0], 403)
            cc.assert_not_called()

    def test_preflight_and_local_editor(self):
        self.server.pages_origin = 'https://nvhhh.github.io'
        status, headers, _ = self.request('OPTIONS', '/api/nam', self.server.pages_origin)
        self.assertEqual(status, 200)
        self.assertEqual(headers['Access-Control-Allow-Private-Network'], 'true')
        self.assertIn('POST', headers['Access-Control-Allow-Methods'])
        self.assertEqual(self.request('GET', '/api/catalog')[0], 200)
        self.assertEqual(self.request('GET', '/api/catalog', f'http://127.0.0.1:{self.server.server_port}')[0], 200)


if __name__ == '__main__':
    unittest.main()
