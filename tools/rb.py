#!/usr/bin/env python3
"""
검토 보드(review-board) 프로젝트 관리 도구
------------------------------------------
PDF를 프로젝트 비밀번호로 암호화(AES-256-GCM, 키는 PBKDF2-SHA256)해 저장소에 넣습니다.
공개 저장소에 올라가도 비밀번호 없이는 이름·라운드·PDF를 볼 수 없습니다.

사용법
  python tools/rb.py new   --name "프로젝트 이름" --password 비번 [--id 원하는ID]
  python tools/rb.py round --id 프로젝트ID --password 비번 --pdf 파일.pdf --label "v3" [--note "변경 내용"]
  python tools/rb.py info  --id 프로젝트ID --password 비번
  python tools/rb.py drop  --id 프로젝트ID --password 비번 --round 1      (라운드 삭제)
  python tools/rb.py rekey --id 프로젝트ID --password 기존비번 --new-password 새비번
"""
import argparse, base64, json, os, secrets, string, sys
from datetime import datetime, timezone
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

ITER = 200_000
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'projects')
b64e = lambda b: base64.b64encode(b).decode()
b64d = lambda s: base64.b64decode(s)


def key_of(pw: str, salt: bytes) -> bytes:
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=ITER).derive(pw.encode('utf-8'))


def enc(key: bytes, data: bytes) -> bytes:
    iv = secrets.token_bytes(12)
    return iv + AESGCM(key).encrypt(iv, data, None)


def dec(key: bytes, blob: bytes) -> bytes:
    return AESGCM(key).decrypt(blob[:12], blob[12:], None)


def pdir(pid): return os.path.join(ROOT, pid)


def load(pid, pw):
    path = os.path.join(pdir(pid), 'project.json')
    if not os.path.exists(path): sys.exit(f'프로젝트 {pid} 가 없습니다.')
    pj = json.load(open(path, encoding='utf-8'))
    salt = b64d(pj['salt']); key = key_of(pw, salt)
    try:
        meta = json.loads(dec(key, b64d(pj['meta'])).decode('utf-8'))
    except Exception:
        sys.exit('비밀번호가 맞지 않습니다.')
    return pj, key, meta


def save(pid, pj, key, meta):
    pj['meta'] = b64e(enc(key, json.dumps(meta, ensure_ascii=False).encode('utf-8')))
    json.dump(pj, open(os.path.join(pdir(pid), 'project.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def cmd_new(a):
    pid = a.id or ''.join(secrets.choice(string.ascii_lowercase + string.digits) for _ in range(10))
    if os.path.exists(pdir(pid)): sys.exit(f'이미 있는 ID입니다: {pid}')
    if len(a.password) < 4: sys.exit('비밀번호는 4자 이상이어야 합니다.')
    os.makedirs(pdir(pid))
    salt = secrets.token_bytes(16)
    pj = {'v': 1, 'iter': ITER, 'salt': b64e(salt)}
    meta = {'name': a.name, 'board': secrets.token_hex(20), 'rounds': [],
            'created': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    save(pid, pj, key_of(a.password, salt), meta)
    print(json.dumps({'id': pid, 'name': a.name}, ensure_ascii=False))


def cmd_round(a):
    pj, key, meta = load(a.id, a.password)
    data = open(a.pdf, 'rb').read()
    if not data.startswith(b'%PDF'): sys.exit('PDF 파일이 아닙니다.')
    no = max([r['round'] for r in meta['rounds']] or [0]) + 1
    fname = f'r{no}.bin'
    open(os.path.join(pdir(a.id), fname), 'wb').write(enc(key, data))
    meta['rounds'].append({'round': no, 'label': a.label or f'라운드 {no}', 'note': a.note or '', 'file': fname,
                           'created': datetime.now(timezone.utc).isoformat(timespec='seconds'), 'bytes': len(data)})
    save(a.id, pj, key, meta)
    print(json.dumps({'id': a.id, 'round': no, 'file': fname, 'mb': round(len(data) / 1048576, 2)}, ensure_ascii=False))


def cmd_info(a):
    _, _, meta = load(a.id, a.password)
    print(json.dumps(meta, ensure_ascii=False, indent=1))


def cmd_drop(a):
    pj, key, meta = load(a.id, a.password)
    r = next((r for r in meta['rounds'] if r['round'] == a.round), None)
    if not r: sys.exit(f'R{a.round} 라운드가 없습니다.')
    meta['rounds'] = [x for x in meta['rounds'] if x['round'] != a.round]
    p = os.path.join(pdir(a.id), r['file'])
    if os.path.exists(p): os.remove(p)
    save(a.id, pj, key, meta)
    print(json.dumps({'id': a.id, 'dropped': a.round, 'rounds': [x['round'] for x in meta['rounds']]}, ensure_ascii=False))


def cmd_rekey(a):
    pj, key, meta = load(a.id, a.password)
    if len(a.new_password) < 4: sys.exit('새 비밀번호는 4자 이상이어야 합니다.')
    salt = secrets.token_bytes(16); nk = key_of(a.new_password, salt)
    for r in meta['rounds']:
        p = os.path.join(pdir(a.id), r['file'])
        open(p, 'wb').write(enc(nk, dec(key, open(p, 'rb').read())))
    pj['salt'] = b64e(salt)
    save(a.id, pj, nk, meta)
    print('비밀번호를 바꿨습니다. (메모는 그대로 유지됩니다)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description='검토 보드 프로젝트 관리')
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('new'); p.add_argument('--name', required=True); p.add_argument('--password', required=True); p.add_argument('--id')
    p = sp.add_parser('round'); p.add_argument('--id', required=True); p.add_argument('--password', required=True)
    p.add_argument('--pdf', required=True); p.add_argument('--label'); p.add_argument('--note')
    p = sp.add_parser('info'); p.add_argument('--id', required=True); p.add_argument('--password', required=True)
    p = sp.add_parser('drop'); p.add_argument('--id', required=True); p.add_argument('--password', required=True); p.add_argument('--round', type=int, required=True)
    p = sp.add_parser('rekey'); p.add_argument('--id', required=True); p.add_argument('--password', required=True); p.add_argument('--new-password', required=True)
    a = ap.parse_args()
    {'new': cmd_new, 'round': cmd_round, 'info': cmd_info, 'drop': cmd_drop, 'rekey': cmd_rekey}[a.cmd](a)
