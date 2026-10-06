#!/usr/bin/env python3
# CREW auto-claimer + auto-rotate WARP — jalan di VPS.
# Setiap akun: ganti IP WARP -> generate wallet -> claim -> simpan.
#
# Cara pakai:  python3 crew_farm.py 20
#
# Butuh: warp-cli sudah connect & mode proxy (socks5 127.0.0.1:40000).
# Private key disimpen di crew_accounts.csv (di .gitignore, jangan di-commit).

import subprocess, socket, time, json, os, sys, csv, hashlib, secrets
import urllib.request, urllib.parse, ssl
import random, re

ORIG_SOCKET = socket.socket   # socket murni untuk koneksi WARP manual

API = "https://buildacrew.xyz/api/airdrop"
STEPS = ["handle", "follow", "like", "rt", "comment", "bell", "wallet"]
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crew_accounts.csv")
SOCKS_HOST, SOCKS_PORT = "127.0.0.1", 40000
ROTATE_RETRIES = 5          # retry ganti IP sampe dapet IP baru
ROTATE_WAIT = 3             # detik tunggu setelah reconnect

# ---------------- WARP IP rotation ----------------
def warp(cmd):
    return subprocess.run(["warp-cli", "--accept-tos", cmd],
                          stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def current_ip():
    """Baca IP exit WARP (socks5) lewat socket murni, tanpa library.
    Harus pakai ORIG_SOCKET — socket global sudah di-patch socks."""
    s = ORIG_SOCKET()
    s.settimeout(12)
    try:
        s.connect((SOCKS_HOST, SOCKS_PORT))
        s.sendall(b"\x05\x01\x00")
        if s.recv(2) != b"\x05\x00": return None
        host = b"ifconfig.me"
        s.sendall(b"\x05\x01\x00\x03" + bytes([len(host)]) + host + b"\x00\x50")
        r = s.recv(10)
        if r[0] != 5 or r[1] != 0: return None
        s.sendall(b"GET / HTTP/1.0\r\nHost: ifconfig.me\r\nAccept: text/plain\r\nUser-Agent: curl/8\r\n\r\n")
        data = b""
        while True:
            chunk = s.recv(4096)
            if not chunk: break
            data += chunk
        body = data.split(b"\r\n\r\n", 1)[-1].strip()
        return body.decode(errors="replace").splitlines()[0].strip()
    except Exception:
        return None
    finally:
        try: s.close()
        except Exception: pass

def rotate_ip(old_ip):
    """Reconnect WARP, balikin IP baru (atau None kalau gagal)."""
    warp("disconnect")
    time.sleep(1)
    warp("connect")
    for _ in range(ROTATE_RETRIES):
        time.sleep(ROTATE_WAIT)
        ip = current_ip()
        if ip and ip != old_ip:
            return ip
    return current_ip()  # usaha terakhir, walaupun sama

# ---------------- Solana keygen (validasi: RFC 8032 + 300/300 vs nacl) ----------------
q = 2**255 - 19
def inv(x): return pow(x, q - 2, q)
d = (-121665 * inv(121666)) % q

def point_add(P, Q):
    x1, y1 = P; x2, y2 = Q
    x = ((x1*y2 + y1*x2) * inv(1 + d*x1*y1*x2*y2)) % q
    y = ((y1*y2 + x1*x2) * inv(1 - d*x1*y1*x2*y2)) % q
    return (x, y)

def scalarmult(P, e):
    R = (0, 1)
    while e:
        if e & 1: R = point_add(R, P)
        P = point_add(P, P)
        e >>= 1
    return R

def recover_x(y, sign):
    x2 = ((y*y - 1) * inv(d*y*y + 1)) % q
    x = pow(x2, (q + 3) // 8, q)
    if (x*x - x2) % q != 0: x = (x * pow(2, (q - 1) // 4, q)) % q
    if x % 2 != sign: x = q - x
    return x

By = (4 * inv(5)) % q
B = (recover_x(By, 0), By)

def keypair(seed=None):
    if seed is None: seed = secrets.token_bytes(32)
    a = int.from_bytes(hashlib.sha512(seed).digest()[:32], "little")
    a &= (1 << 254) - 8
    a |= (1 << 254)
    x, y = scalarmult(B, a)
    return (y | ((x & 1) << 255)).to_bytes(32, "little"), seed

ALPH = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
def b58e(raw):
    n = int.from_bytes(raw, "big"); out = ""
    while n: n, r = divmod(n, 58); out = ALPH[r] + out
    return "1" * (len(raw) - len(raw.lstrip(b"\x00"))) + out

# ---------------- handle generator ----------------
ADJ = ["lunar","amber","flux","onyx","velvet","crimson","hollow","ember","mint","cobalt",
       "frosted","bronze","willow","copper","slate","coral","jade","indigo","maple","pearl"]
NOUN = ["dev","builder","nomad","pilgrim","smith","warden","rider","arch","scribe","maker",
        "vessel","forger","engineer","researcher","observer","architect","operator","voyager"]
SUF = ["", "", "", "x", "_eth", "_sol", "io", "_dev", "_build"]
def handle():
    h = random.choice(ADJ) + random.choice(["_", "", ""]) + random.choice(NOUN)
    if random.random() < .6: h += str(random.randint(2, 99))
    if random.random() < .3: h += random.choice(SUF)
    return h[:15]

# ---------------- claim (semua lewat WARP) ----------------
def _warp_post(url, payload, timeout=30):
    """POST JSON lewat WARP socks5, tanpa library proxy.
    Pakai ORIG_SOCKET + handshake socks5 manual, jadi gak ganggu socket global."""
    body = json.dumps(payload).encode()
    host = urllib.parse.urlparse(url).hostname
    path = urllib.parse.urlparse(url).path
    s = ORIG_SOCKET()
    s.settimeout(timeout)
    try:
        s.connect((SOCKS_HOST, SOCKS_PORT))
        s.sendall(b"\x05\x01\x00")
        if s.recv(2) != b"\x05\x00":
            raise RuntimeError("socks5 handshake gagal")
        hb = host.encode()
        s.sendall(b"\x05\x01\x00\x03" + bytes([len(hb)]) + hb + b"\x01\xbb")
        r = s.recv(10)
        if r[0] != 5 or r[1] != 0:
            raise RuntimeError("socks5 connect ditolak")
        ctx = ssl.create_default_context()
        ss = ctx.wrap_socket(s, server_hostname=host)
        req = (b"POST " + path.encode() + b" HTTP/1.1\r\n"
               + b"Host: " + hb + b"\r\n"
               + b"Content-Type: application/json\r\n"
               + b"Content-Length: " + str(len(body)).encode() + b"\r\n"
               + b"Origin: https://buildacrew.xyz\r\n"
               + b"Referer: https://buildacrew.xyz/\r\n"
               + b"User-Agent: Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36\r\n"
               + b"Connection: close\r\n\r\n" + body)
        ss.sendall(req)
        data = b""
        while True:
            chunk = ss.recv(65536)
            if not chunk:
                break
            data += chunk
        ss.close()
        head, _, resp_body = data.partition(b"\r\n\r\n")
        status = int(head.split(b" ")[1])
        try:
            return status, json.loads(resp_body.decode())
        except Exception:
            return status, {"raw": resp_body.decode(errors="replace")[:200]}
    finally:
        try:
            s.close()
        except Exception:
            pass

def claim(h, addr, timeout=30):
    return _warp_post(API, {"handle": h, "wallet": addr, "steps": STEPS}, timeout=timeout)

def save(row):
    ex = os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if not ex: w.writerow(["handle", "address", "seed_private_key", "queue_n", "ip"])
        w.writerow(row)

def one(ip_tag=""):
    pub, seed = keypair()
    h = handle()
    while not re.fullmatch(r"[A-Za-z0-9_]{1,15}", h): h = handle()
    code, resp = claim(h, b58e(pub))
    return h, b58e(pub), b58e(seed), code, resp

if __name__ == "__main__":
    n = 1
    if len(sys.argv) > 1:
        try: n = max(1, int(sys.argv[1]))
        except ValueError: pass
    print(f"CREW farm + WARP auto-rotate — {n} akun\n")
    ok = 0
    ip = current_ip()
    print(f"IP sekarang: {ip}\n")
    for i in range(n):
        # 1) ganti IP
        new_ip = rotate_ip(ip)
        if not new_ip:
            print(f"[{i+1}/{n}] GAGAL ganti IP (WARP bermasalah?). Stop."); break
        ip = new_ip
        # 2) claim
        try:
            h, addr, priv, code, resp = one()
            if code == 200 and resp.get("ok"):
                ok += 1
                save([h, addr, priv, resp.get("n", ""), ip])
                print(f"[{i+1}/{n}] OK  #{resp.get('n')}  @{h}  (ip {ip})")
            elif code == 409 and "network" in resp.get("error", "").lower():
                print(f"[{i+1}/{n}] IP {ip} udah kepakai. Rotate ulang...")
                # coba sekali lagi dengan IP baru
                ip2 = rotate_ip(ip)
                if ip2 and ip2 != ip:
                    ip = ip2
                    h, addr, priv, code, resp = one()
                    if code == 200 and resp.get("ok"):
                        ok += 1
                        save([h, addr, priv, resp.get("n", ""), ip])
                        print(f"[{i+1}/{n}] OK  #{resp.get('n')}  @{h}  (ip {ip})")
                    else:
                        print(f"[{i+1}/{n}] masih gagal: {resp}")
                else:
                    print(f"[{i+1}/{n}] gak dapet IP baru. Lanjut akun berikut.")
            else:
                print(f"[{i+1}/{n}] GAGAL {code}: {resp.get('error', resp)}")
        except Exception as e:
            print(f"[{i+1}/{n}] ERROR {type(e).__name__}: {e}")
    print(f"\nBerhasil {ok}/{n} akun. Simpan di:\n{OUT}")
    print("JAGA BAIK-BAIK file itu — isinya private key wallet.")
