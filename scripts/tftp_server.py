"""Finite, single-transfer TFTP server. No service starts unless invoked explicitly."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import select
import socket
import struct
import tempfile
import threading
import time


def packet(op, block):
    return struct.pack('!HH', op, block)


class Server:
    def __init__(self, bind, peer, output, reads, port=69, seconds=1800, timeout=2, retries=8):
        self.bind, self.peer = str(ipaddress.IPv4Address(bind)), str(ipaddress.IPv4Address(peer))
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=False)
        self.reads = {name: Path(path).read_bytes() for name, path in reads.items()}
        self.deadline = time.monotonic() + min(seconds, 1800)
        self.timeout, self.retries = timeout, retries
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind((self.bind, port))
        self.port = self.sock.getsockname()[1]

    def receive(self, sock, peer, end):
        while time.monotonic() < min(end, self.deadline):
            sock.settimeout(max(.001, min(end, self.deadline) - time.monotonic()))
            data, addr = sock.recvfrom(2048)
            if addr == peer:
                if not self.first_datagram_seen:
                    self.first_datagram_seen = True
                    print(json.dumps(dict(event='first-transfer-datagram', bytes=len(data),
                                          opcode=int.from_bytes(data[:2], 'big'),
                                          block=int.from_bytes(data[2:4], 'big'))), flush=True)
                return data
            sock.sendto(packet(5, 5) + b'Unknown transfer ID\0', addr)
        raise socket.timeout()

    def exchange(self, sock, peer, outgoing, accept):
        for _ in range(self.retries):
            if time.monotonic() >= self.deadline:
                break
            sock.sendto(outgoing, peer)
            end = time.monotonic() + self.timeout
            while time.monotonic() < end:
                try:
                    data = self.receive(sock, peer, end)
                except socket.timeout:
                    break
                if len(data) >= 2 and data[:2] == b'\0\5':
                    raise ValueError('peer reported TFTP error')
                if accept(data):
                    return data
        raise TimeoutError('bounded transfer retry limit')

    def transfer(self, request, peer):
        parts = request[2:].split(b'\0')
        if len(parts) < 3 or parts[1].lower() != b'octet':
            raise ValueError('octet mode required')
        name = parts[0].decode('ascii')
        op = struct.unpack('!H', request[:2])[0]
        option_parts = parts[2:]
        if option_parts and option_parts[-1] == b'':
            option_parts.pop()
        if len(option_parts) % 2:
            raise ValueError('malformed options')
        options = {}
        for key, value in zip(option_parts[::2], option_parts[1::2]):
            key = key.lower()
            if key == b'blksize':
                requested = int(value)
                if not 8 <= requested <= 65464:
                    raise ValueError('invalid blksize')
                options['blksize'] = min(requested, 1468)
        blocksize = options.get('blksize', 512)
        oack = b'\0\6blksize\0' + str(blocksize).encode() + b'\0'
        self.first_datagram_seen = False
        print(json.dumps(dict(event='request', opcode=op, request_bytes=len(request),
                              requested_blksize=next((v.decode('ascii', errors='replace')[:8]
                                  for k, v in zip(option_parts[::2], option_parts[1::2])
                                  if k.lower() == b'blksize'), None),
                              negotiated_blksize=blocksize)), flush=True)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.bind((self.bind, 0))
            if op == 1:
                data = self.reads[name]  # Immutable startup snapshot, exact filename only.
                if options:
                    self.exchange(sock, peer, oack, lambda d: d == packet(4, 0))
                for i, start in enumerate(range(0, len(data) + 1, blocksize), 1):
                    payload = data[start:start + blocksize]
                    self.exchange(sock, peer, packet(3, i & 65535) + payload,
                                  lambda d, i=i: d == packet(4, i & 65535))
                return
            match = re.fullmatch(r'nand-(main|raw)-([0-9a-fA-F]{8})\.bin', name)
            if op != 2 or not match:
                raise ValueError('write filename denied')
            offset = int(match[2], 16)
            if offset >= 128 * 1024 * 1024 or offset % (1024 * 1024):
                raise ValueError('unaligned or out-of-range offset')
            expected = 1048576 if match[1] == 'main' else 1081344
            target = self.output / name
            partial = self.output / (name + '.part')
            if target.exists():
                raise FileExistsError('completed target exists')
            total, block, digest = 0, 1, hashlib.sha256()
            with partial.open('xb') as out:
                ack = oack if options else packet(4, 0)
                while True:
                    def accept(d):
                        if len(d) < 4 or len(d) > blocksize + 4 or d[:2] != b'\0\3':
                            return False
                        got = struct.unpack('!H', d[2:4])[0]
                        if got == ((block - 1) & 65535):
                            sock.sendto(ack, peer)
                        return got == (block & 65535)
                    data = self.exchange(sock, peer, ack, accept)
                    body = data[4:]
                    total += len(body)
                    if total > expected or (len(body) < blocksize and total != expected):
                        sock.sendto(packet(5, 0) + b'Incorrect backup size\0', peer)
                        raise ValueError('incorrect backup size')
                    out.write(body)
                    digest.update(body)
                    ack = packet(4, block & 65535)
                    if len(body) < blocksize:
                        out.flush()
                        os.fsync(out.fileno())
                        break
                    block += 1
            # hard-link creation refuses overwrite atomically, including on Windows.
            os.link(partial, target)
            partial.unlink()
            with (self.output / 'manifest.jsonl').open('a', encoding='utf-8') as manifest:
                manifest.write(json.dumps(dict(file=name, bytes=total, sha256=digest.hexdigest())) + '\n')
                manifest.flush()
                os.fsync(manifest.fileno())
            sock.sendto(ack, peer)
            # Bounded final-ACK dally: repeated final DATA never writes twice.
            end = time.monotonic() + self.timeout * 2
            while time.monotonic() < min(end, self.deadline):
                ready, _, _ = select.select([sock, self.sock], [], [],
                    max(0, min(end, self.deadline) - time.monotonic()))
                if self.sock in ready:
                    queued, address = self.sock.recvfrom(2048, socket.MSG_PEEK)
                    if address[0] == self.peer and queued[:2] in (b'\0\1', b'\0\2'):
                        # Keep the next request queued for run(); final ACK was received.
                        return
                    self.sock.recvfrom(2048)
                if sock not in ready:
                    continue
                try:
                    duplicate = self.receive(sock, peer, end)
                except socket.timeout:
                    break
                if duplicate == data:
                    sock.sendto(ack, peer)

    def run(self):
        # ponytail: serialized transfers are sufficient for one router.
        with self.sock:
            while time.monotonic() < self.deadline:
                self.sock.settimeout(min(.5, max(.001, self.deadline - time.monotonic())))
                try:
                    request, peer = self.sock.recvfrom(2048)
                except socket.timeout:
                    continue
                if peer[0] != self.peer:
                    continue
                try:
                    if len(request) < 4:
                        raise ValueError('short request')
                    self.transfer(request, peer)
                except (OSError, ValueError, KeyError, UnicodeError) as exc:
                    self.sock.sendto(packet(5, 0) + b'Request or transfer rejected\0', peer)
                    print(type(exc).__name__, str(exc), flush=True)


def selftest():
    with tempfile.TemporaryDirectory() as temp:
        source = Path(temp) / 'fit.bin'
        payload = bytes(range(256)) * 5
        source.write_bytes(payload)
        server = Server('127.0.0.1', '127.0.0.1', Path(temp) / 'out', {'ram.fit': source},
                        port=0, seconds=20, timeout=2, retries=8)
        source.write_bytes(b'changed after immutable snapshot')
        thread = threading.Thread(target=server.run)
        thread.start()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as client:
                client.settimeout(3)
                client.sendto(b'\0\1ram.fit\0octet\0', ('127.0.0.1', server.port))
                received = bytearray()
                while True:
                    data, transfer = client.recvfrom(2048)
                    assert data[:2] == b'\0\3'
                    received.extend(data[4:])
                    client.sendto(b'\0\4' + data[2:4], transfer)
                    if len(data) < 516:
                        break
                assert hashlib.sha256(received).digest() == hashlib.sha256(payload).digest()
                for kind, size, blocksize, offset in [('main', 1048576, 512, 0),
                        ('raw', 1081344, 512, 0), ('raw', 1081344, 1468, 0x100000)]:
                    name = f'nand-{kind}-{offset:08x}.bin'
                    option = b'blksize\0' + str(blocksize).encode() + b'\0' if blocksize != 512 else b''
                    requested_at = time.monotonic()
                    client.sendto(b'\0\2' + name.encode() + b'\0octet\0' + option,
                                  ('127.0.0.1', server.port))
                    ack, transfer = client.recvfrom(2048)
                    assert time.monotonic() - requested_at < 1, 'next WRQ blocked by final dally'
                    assert ack == (b'\0\6' + option if option else packet(4, 0))
                    body = b'x' * size
                    for block, start in enumerate(range(0, size + 1, blocksize), 1):
                        message = packet(3, block) + body[start:start + blocksize]
                        client.sendto(message, transfer)
                        assert client.recvfrom(2048)[0] == packet(4, block)
                    client.sendto(message, transfer)
                    assert client.recvfrom(2048)[0] == packet(4, block)
                    assert (server.output / name).read_bytes() == body
                assert len((server.output / 'manifest.jsonl').read_text().splitlines()) == 3
                client.sendto(b'\0\1ram.fit\0octet\0blksize\0' + b'1468\0', ('127.0.0.1', server.port))
                ack, transfer = client.recvfrom(2048)
                assert ack == b'\0\6blksize\0' + b'1468\0'
                client.sendto(packet(4, 0), transfer)
                data, transfer = client.recvfrom(2048)
                assert data == packet(3, 1) + payload
                client.sendto(packet(4, 1), transfer)
                client.sendto(b'\0\2nand-main-00100000.bin\0octet\0', ('127.0.0.1', server.port))
                ack, transfer = client.recvfrom(2048)
                assert ack == packet(4, 0)
                client.sendto(packet(3, 1) + b'too short', transfer)
                assert client.recvfrom(2048)[0][:2] == b'\0\5'
                time.sleep(.1)
                assert (server.output / 'nand-main-00100000.bin.part').exists()
                assert not (server.output / 'nand-main-00100000.bin').exists()
                print('PASS: immutable RRQ; 512/1468 RRQ+WRQ; duplicate final DATA; back-to-back WRQ under 1s with 4s dally; manifest; short WRQ .part')
        finally:
            server.deadline = time.monotonic()
            thread.join(3)
            assert not thread.is_alive()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--selftest', action='store_true')
    parser.add_argument('--bind')
    parser.add_argument('--peer')
    parser.add_argument('--output')
    parser.add_argument('--read', action='append', default=[], metavar='NAME=PATH')
    parser.add_argument('--port', type=int, default=69)
    parser.add_argument('--seconds', type=int, default=1800)
    args = parser.parse_args()
    if args.selftest:
        selftest()
    else:
        if not all((args.bind, args.peer, args.output)) or not 1 <= args.seconds <= 1800:
            parser.error('--bind, --peer, new --output and seconds 1..1800 required')
        mappings = dict(item.split('=', 1) for item in args.read)
        if any(not re.fullmatch(r'[A-Za-z0-9_.-]+', name) for name in mappings):
            parser.error('read names must be plain filenames')
        Server(args.bind, args.peer, args.output, mappings, args.port, args.seconds).run()
