import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request


class ImageServer(unittest.TestCase):
    def test_exact_routes_immutable_data_and_peer_filter(self):
        script = Path(__file__).resolve().parents[1] / 'scripts/serve_image.py'
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            data = b'PUBLIC_TEST_IMAGE'
            image = temp/'image.ubi'; image.write_bytes(data)
            digest = hashlib.sha256(data).hexdigest()
            manifest = temp/'manifest.json'
            manifest.write_text(json.dumps({'files': {'ubi': {'sha256': digest, 'bytes': len(data)}}}))
            receipt = temp/'receipt.json'; receipt.write_text('{"format":"TI04_BACKUP_V1"}')
            with socket.socket() as reserve:
                reserve.bind(('127.0.0.1', 0)); port = reserve.getsockname()[1]
            process = subprocess.Popen([sys.executable, str(script), '--bind', '127.0.0.1', '--peer', '127.0.0.1',
                                       '--port', str(port), '--file', str(image), '--sha256', digest,
                                       '--manifest', str(manifest), '--receipt', str(receipt)], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            try:
                base = f'http://127.0.0.1:{port}'
                for _ in range(30):
                    try:
                        with urllib.request.urlopen(base+'/install.ubi', timeout=.2) as r:
                            self.assertEqual(r.read(), data)
                        break
                    except urllib.error.URLError: time.sleep(.05)
                else: self.fail('HTTP server did not start')
                image.write_bytes(b'changed after server snapshot')
                with urllib.request.urlopen(base+'/install.ubi', timeout=1) as r: self.assertEqual(r.read(), data)
                for route in ('/manifest.json', '/own-backup-receipt.json'):
                    with urllib.request.urlopen(base+route, timeout=1) as r: self.assertEqual(r.status, 200)
                try:
                    urllib.request.urlopen(base+'/../receipt.json', timeout=1)
                    self.fail('Unexpected route was accepted')
                except urllib.error.HTTPError as error:
                    self.assertEqual(error.code, 404)
                    error.close()
                import http.client
                client = http.client.HTTPConnection('127.0.0.1', port, timeout=1, source_address=('127.0.0.2', 0))
                try:
                    client.request('GET', '/install.ubi'); self.assertEqual(client.getresponse().status, 404)
                finally: client.close()
            finally:
                process.terminate(); process.wait(timeout=3)
                process.stdout.close()


if __name__ == '__main__': unittest.main()
