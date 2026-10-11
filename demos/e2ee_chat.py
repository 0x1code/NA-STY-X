"""Three-process local E2EE demonstration; experimental, no real secrets.

Relay has only packets. Endpoint processes hold keys. The trusted local controller
provisions a one-time invitation over private process pipes, simulating a separate
trusted pairing channel. This is not isolation against a local OS administrator.
"""
import argparse
import json
import hashlib
import os
import platform
import secrets
import subprocess
import sys
from collections import deque
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'research/reference_cipher'))
from session_v1 import Pairing, MAX_PLAINTEXT, HEADER

MAX_FRAME = (MAX_PLAINTEXT + HEADER + 44) * 2 + 1024


def emit(value):
    print(json.dumps(value, ensure_ascii=True), flush=True)


def relay():
    queues = {'alice': deque(), 'bob': deque()}
    audit = deque(maxlen=256)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def result(self, status, obj):
            data = json.dumps(obj).encode()
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            try:
                size = int(self.headers.get('Content-Length', '-1'))
                if self.path != '/queue' or not 0 <= size <= MAX_FRAME:
                    raise ValueError()
                frame = json.loads(self.rfile.read(size))
                if set(frame) != {'to', 'packet'} or frame['to'] not in queues:
                    raise ValueError()
                packet = bytes.fromhex(frame['packet'])
                if not 5 <= len(packet) <= MAX_PLAINTEXT + HEADER + 44:
                    raise ValueError()
                if packet[:4] not in (b'NXH1', b'NXS1'):
                    raise ValueError()
                queue = queues[frame['to']]
                if len(queue) >= 256:
                    self.result(429, {'error': 'queue full'})
                    return
                queue.append(packet.hex())
                audit.append({'to': frame['to'], 'packet': packet.hex(), 'bytes': len(packet)})
                self.result(200, {'queued': True})
            except (ValueError, KeyError, TypeError, UnicodeError):
                self.result(400, {'error': 'invalid frame'})

        def do_GET(self):
            target = self.path.removeprefix('/queue/')
            if self.path == '/audit':
                self.result(200, list(audit))
            elif self.path.startswith('/queue/') and target in queues:
                self.result(200, {'packet': queues[target].popleft() if queues[target] else None})
            else:
                self.result(404, {'error': 'not found'})

    server = HTTPServer(('127.0.0.1', 0), Handler)
    emit({'url': f'http://127.0.0.1:{server.server_port}', 'pid': os.getpid()})
    server.serve_forever()


def agent():
    pairing = pending = unverified = session = None
    emit({'ready': True, 'pid': os.getpid()})
    for line in sys.stdin:
        try:
            if len(line) > MAX_FRAME:
                raise ValueError('frame too large')
            request = json.loads(line)
            command = request['command']
            if command in ('provision', 'import'):
                if session:
                    session.close()
                session = pending = unverified = None
                if command == 'provision':
                    invitation = {'secret': secrets.token_bytes(32).hex(),
                                  'a': secrets.token_bytes(16).hex(),
                                  'b': secrets.token_bytes(16).hex()}
                else:
                    invitation = request['invitation']
                pairing = Pairing(*(bytes.fromhex(invitation[name]) for name in ('secret', 'a', 'b')))
                response = {'invitation': invitation} if command == 'provision' else {'imported': True}
                del invitation
            elif command == 'start':
                pending, packet = pairing.initiate(secrets.token_bytes(16), secrets.token_bytes(16))
                pairing = None
                response = {'packet': packet.hex()}
            elif command == 'respond':
                pending, packet = pairing.respond(bytes.fromhex(request['packet']), secrets.token_bytes(16))
                pairing = None
                response = {'packet': packet.hex()}
            elif command == 'finish':
                unverified, packet = pending.complete(bytes.fromhex(request['packet']))
                pending = None
                response = {'packet': packet.hex(), 'verification': unverified.verification.hex()}
            elif command == 'confirm':
                unverified = pending.complete(bytes.fromhex(request['packet']))
                pending = None
                response = {'verification': unverified.verification.hex()}
            elif command == 'verify':
                session = unverified.verify_peer(bytes.fromhex(request['code']))
                unverified = None
                response = {'verified': True, 'session': session.sid.hex()}
            elif command == 'send':
                if session is None:
                    raise ValueError('peer not verified')
                response = {'packet': session.seal(request['text'].encode('utf8')).hex()}
            elif command == 'receive':
                if session is None:
                    raise ValueError('peer not verified')
                response = {'text': session.open(bytes.fromhex(request['packet'])).decode('utf8')}
            elif command == 'close':
                if session:
                    session.close()
                session = pairing = pending = unverified = None
                response = {'closed': True}
            else:
                raise ValueError('unknown command')
            emit({'ok': True, **response})
        except (ValueError, KeyError, TypeError, AttributeError, UnicodeError):
            # Never include exception details, invitation, key or submitted plaintext.
            emit({'ok': False, 'error': 'operation rejected'})


class Child:
    def __init__(self, mode):
        self.process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), mode],
                                        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        text=True, encoding='utf8', bufsize=1)
        self.ready = json.loads(self.process.stdout.readline())

    def call(self, command, **data):
        self.process.stdin.write(json.dumps({'command': command, **data}) + '\n')
        self.process.stdin.flush()
        return json.loads(self.process.stdout.readline())

    def stop(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait()
        self.process.stdin.close()
        self.process.stdout.close()


class Demo:
    def __init__(self):
        self.children = []
        try:
            for mode in ('--relay', '--agent', '--agent'):
                self.children.append(Child(mode))
        except BaseException:
            self.stop()
            raise
        self.relay, self.alice, self.bob = self.children
        self.url = self.relay.ready['url']
        self.events = []
        self.last = None

    def http(self, path, data=None):
        request = Request(self.url + path, data=json.dumps(data).encode() if data is not None else None,
                          headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=5) as response:
            return json.load(response)

    def transport(self, destination, packet):
        self.http('/queue', {'to': destination, 'packet': packet})
        delivered = self.http('/queue/' + destination)['packet']
        if delivered != packet:
            raise RuntimeError('relay delivery failed')
        return delivered

    def event(self, name, details):
        self.events.append({'event': name, 'details': details})
        print(f'  [{name}] {details}', flush=True)

    @staticmethod
    def ok(result):
        if not result.get('ok'):
            raise RuntimeError('endpoint rejected operation')
        return result

    def pair(self):
        # Trusted LOCAL pipe provisioning, never an HTTP relay request.
        invitation = self.ok(self.alice.call('provision'))['invitation']
        self.ok(self.bob.call('import', invitation=invitation))
        del invitation
        offer = self.ok(self.alice.call('start'))['packet']
        reply = self.ok(self.bob.call('respond', packet=self.transport('bob', offer)))['packet']
        a = self.ok(self.alice.call('finish', packet=self.transport('alice', reply)))
        b = self.ok(self.bob.call('confirm', packet=self.transport('bob', a['packet'])))
        if a['verification'] != b['verification']:
            raise RuntimeError('peer verification mismatch')
        # Demo controller compares via trusted local pipes. A real product requires user confirmation.
        self.ok(self.alice.call('verify', code=b['verification']))
        session = self.ok(self.bob.call('verify', code=a['verification']))['session']
        self.event('СВЯЗЫВАНИЕ', 'Коды совпали: ' + a['verification'] + '; сеанс ' + session)

    def send(self, sender, text):
        destination = 'bob' if sender == 'alice' else 'alice'
        packet = self.ok(getattr(self, sender).call('send', text=text))['packet']
        delivered = self.transport(destination, packet)
        result = self.ok(getattr(self, destination).call('receive', packet=delivered))
        if result['text'] != text:
            raise RuntimeError('plaintext mismatch')
        self.last = (destination, packet)
        raw = bytes.fromhex(packet)
        self.event('СООБЩЕНИЕ', f'{sender} → {destination}: {result["text"]}')
        self.event('СЕРВЕР', f'{len(raw)} байт; шифротекст: {raw[96:-16].hex()[:80]}…')
        return packet

    def reject(self, destination, packet, label):
        delivered = self.transport(destination, packet)
        result = getattr(self, destination).call('receive', packet=delivered)
        if result.get('ok'):
            raise RuntimeError('unexpected accepted attack')
        self.event(label, 'Отклонено; открытый текст не выдан')

    def reorder(self):
        packets = [self.ok(self.alice.call('send', text=f'Порядок {n}'))['packet'] for n in range(3)]
        for n in (2, 0, 1):
            packet = self.transport('bob', packets[n])
            result = self.ok(self.bob.call('receive', packet=packet))
            self.event('ПЕРЕСТАНОВКА', f'Пришёл {n}: {result["text"]}')

    def restart(self):
        stale = self.ok(self.alice.call('send', text='До сбоя'))['packet']
        self.bob.stop()
        self.bob = Child('--agent')
        self.children[2] = self.bob
        self.reject('bob', stale, 'ПОСЛЕ СБОЯ БЕЗ КЛЮЧЕЙ')
        self.event('ПЕРЕЗАПУСК', f'Новый процесс Bob {self.bob.ready["pid"]}; требуется новое связывание')
        self.pair()
        self.reject('bob', stale, 'ПАКЕТ ДО СБОЯ')
        self.send('alice', 'Связь восстановлена новым сеансом после сбоя.')

    def scripted(self):
        print('NA&STY-X / NAXi — исследовательский E2EE-прототип\n'
              'Собственный шифр. Не применять для реальных секретов.\n'
              'Три локальных процесса; демонстрационный контроллер доверенный.\n')
        self.event('ПРОЦЕССЫ', f'Сервер {self.relay.ready["pid"]}; Alice {self.alice.ready["pid"]}; Bob {self.bob.ready["pid"]}')
        self.pair()
        old = self.send('alice', 'Привет, Bob! Сервер не получает этот текст.')
        self.send('bob', 'Привет, Alice! Сообщение расшифровано на моей стороне.')
        self.reject('bob', old, 'ПОВТОР')
        pending = self.ok(self.alice.call('send', text='Проверка целостности'))['packet']
        changed = bytearray.fromhex(pending)
        changed[-1] ^= 1
        self.reject('bob', changed.hex(), 'ПОДМЕНА')
        result = self.ok(self.bob.call('receive', packet=self.transport('bob', pending)))
        self.event('ПОСЛЕ ПОДМЕНЫ', result['text'])
        self.reorder()
        self.ok(self.alice.call('close'))
        self.ok(self.bob.call('close'))
        self.pair()  # Fresh OS-random secret, delivered outside the compromised session.
        self.reject('bob', old, 'СТАРЫЙ СЕАНС')
        self.send('alice', 'Новый сеанс после повторного связывания.')
        self.restart()
        self.event('ИТОГ', 'Доставка, ответы, повторы, подмена, перестановка, обновление и перезапуск проверены')

    def interactive(self):
        print('\nКоманды: alice текст | bob текст | replay | tamper | reorder | renew | restart | status | quit')
        while True:
            try:
                line = input('naxi> ').strip()
            except EOFError:
                return
            if line == 'quit':
                return
            if line.startswith(('alice ', 'bob ')):
                who, text = line.split(' ', 1)
                if len(text.encode('utf8')) > MAX_PLAINTEXT:
                    print('Сообщение слишком длинное: максимум 65 536 байт UTF-8')
                    continue
                self.send(who, text)
            elif line == 'replay' and self.last:
                self.reject(*self.last, 'ПОВТОР')
            elif line == 'tamper' and self.last:
                who, packet = self.last
                changed = bytearray.fromhex(packet)
                changed[-1] ^= 1
                self.reject(who, changed.hex(), 'ПОДМЕНА')
            elif line == 'reorder':
                self.reorder()
            elif line == 'renew':
                self.pair()
            elif line == 'restart':
                self.restart()
            elif line == 'status':
                self.event('СЕРВЕР', f'{len(self.http("/audit"))} публичных пакетов; URL {self.url}')
            else:
                print('Команда не распознана')

    def save(self, path):
        path.parent.mkdir(parents=True, exist_ok=True)
        sources = ['demos/e2ee_chat.py', 'research/reference_cipher/session_v1.py',
                   'research/reference_cipher/message_v3.py', 'research/reference_cipher/engine_v3.py']
        hashes = {name: hashlib.sha256((ROOT / name).read_text(encoding='utf8').replace('\r\n', '\n')
                                      .encode('utf8')).hexdigest() for name in sources}
        path.write_text(json.dumps({'scope': 'local three-process experimental demo; not security proof',
                                    'date': '2026-10-12', 'python': platform.python_version(),
                                    'platform': platform.platform(), 'source_sha256_utf8_lf': hashes,
                                    'events': self.events, 'relay_packets': self.http('/audit')},
                                   ensure_ascii=False, indent=2) + '\n', encoding='utf8')

    def stop(self):
        for child in reversed(self.children):
            child.stop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--relay', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--agent', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--interactive', action='store_true')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    if args.relay:
        relay()
    elif args.agent:
        agent()
    else:
        demo = Demo()
        try:
            demo.scripted()
            if args.interactive:
                demo.interactive()
            if args.report:
                demo.save(args.report)
        finally:
            demo.stop()
