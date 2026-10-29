"""Serve one immutable, hash-pinned image to the owned router for a finite interval."""
import argparse, hashlib, http.server, ipaddress, json, time
from pathlib import Path
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--bind',required=True);p.add_argument('--peer',default='192.168.1.1')
p.add_argument('--file',required=True);p.add_argument('--sha256',required=True);p.add_argument('--port',type=int,default=8000)
p.add_argument('--manifest', required=True)
p.add_argument('--receipt', required=True, help='OWN private verified backup receipt, never another device')
a=p.parse_args();ipaddress.IPv4Address(a.bind);ipaddress.IPv4Address(a.peer)
data=Path(a.file).read_bytes();assert hashlib.sha256(data).hexdigest()==a.sha256
manifest=Path(a.manifest).read_bytes(); parsed=json.loads(manifest)
assert parsed['files']['ubi']['sha256']==a.sha256 and parsed['files']['ubi']['bytes']==len(data)
receipt=Path(a.receipt).read_bytes(); assert json.loads(receipt)['format']=='TI04_BACKUP_V1'
files={'/install.ubi':data, '/manifest.json':manifest, '/own-backup-receipt.json':receipt}
class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.client_address[0]!=a.peer or self.path not in files:
            self.send_error(404);return
        payload=files[self.path]
        self.send_response(200);self.send_header('Content-Length',str(len(payload)));self.send_header('Content-Type','application/octet-stream');self.end_headers()
        try:self.wfile.write(payload)
        except (BrokenPipeError,ConnectionResetError):pass
    def log_message(self,fmt,*args):print(json.dumps({'peer':self.client_address[0],'message':fmt%args}),flush=True)
server=http.server.HTTPServer((a.bind,a.port),Handler);server.timeout=.5
print('READY: immutable install image/manifest/OWN receipt; peer restricted; expires in 20 minutes',flush=True)
end=time.monotonic()+1200
with server:
    while time.monotonic()<end:server.handle_request()
