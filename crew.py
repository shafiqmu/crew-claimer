#!/data/data/com.termux/files/usr/bin/python3
# CREW auto-claimer — zero-dependency (Termux / Python 3.10+, stdlib only)
#
# Bikin 1 wallet Solana baru di HP kamu (private key disimpen lokal),
# lalu kirim claim airdrop CREW ke buildacrew.xyz. Tugas follow/like/rt/reply/bell
# gak diverifikasi server, jadi langsung dikirim sebagai "done".
#
# CARA PAKAI (Termux):
#   pkg install python          # sekali doang
#   python crew.py              # 1 akun
#   python crew.py 5            # 5 akun (baca catatan IP di bawah)
#
# CATATAN PENTING — 1 claim per IP:
#   Server nolak klaim kedua dari IP yang sama: "This network has already claimed".
#   Untuk akun kedua dst, ganti IP dulu: matikan internet, nyalakan lagi
#   (atau ganti WiFi/mobile data, atau pakai VPN). Script otomatis kasih tau kalau ketemu ini.

import urllib.request, json, random, sys, os, csv, time, hashlib, secrets

API = "https://buildacrew.xyz/api/airdrop"
STEPS = ["handle", "follow", "like", "rt", "comment", "bell", "wallet"]
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "crew_accounts.csv")

# ---------------- Solana keygen murni (validasi: RFC 8032 + cocok 300/300 vs nacl) ----------------
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

# ---------------- handle generator (kaya akun X beneran) ----------------
ADJ = ["lunar","amber","flux","onyx","velvet","crimson","hollow","ember","mint","cobalt",
       "frosted","bronze","willow","copper","slate","coral","jade","indigo","maple","pearl"]
NOUN = ["dev","builder","nomad","pilgrim","smith","warden","rider","arch","scribe","maker",
        "vessel","forger","engineer","researcher","observer","architect","operator","voyager"]
SUF = ["", "", "", "x", "_eth", "_sol", "io", "_dev", "_build"]
def handle():
    h = random.choice(ADJ)
    h += random.choice(["_", "", ""])        # separator: underscore atau langsung
    h += random.choice(NOUN)
    if random.random() < .6: h += str(random.randint(2, 99))
    if random.random() < .3: h += random.choice(SUF)
    return h[:15]

def valid_handle(h):
    import re
    return bool(re.fullmatch(r"[A-Za-z0-9_]{1,15}", h))

# ---------------- claim ----------------
def claim(h, addr, timeout=30):
    body = json.dumps({"handle": h, "wallet": addr, "steps": STEPS}).encode()
    req = urllib.request.Request(API, data=body, headers={
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36",
        "Origin": "https://buildacrew.xyz",
        "Referer": "https://buildacrew.xyz/",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try: msg = json.loads(e.read().decode()).get("error", str(e))
        except Exception: msg = str(e)
        return e.code, {"error": msg}

def save(row):
    ex = os.path.exists(OUT)
    with open(OUT, "a", newline="") as f:
        w = csv.writer(f)
        if not ex: w.writerow(["handle", "address", "seed_private_key", "queue_n"])
        w.writerow(row)

def one():
    pub, seed = keypair()
    addr, priv = b58e(pub), b58e(seed)
    h = handle()
    while not valid_handle(h): h = handle()
    code, resp = claim(h, addr)
    return h, addr, priv, code, resp

if __name__ == "__main__":
    n = 1
    if len(sys.argv) > 1:
        try: n = max(1, int(sys.argv[1]))
        except ValueError: n = 1
    print(f"CREW claimer — {n} akun\n")
    ok_count = 0
    for i in range(n):
        try:
            h, addr, priv, code, resp = one()
            if code == 200 and resp.get("ok"):
                ok_count += 1
                save([h, addr, priv, resp.get("n", "")])
                print(f"[{i+1}/{n}] OK  antrian #{resp.get('n')}  @{h}")
                print(f"         {addr}")
            elif code == 409 and "network" in resp.get("error", "").lower():
                print(f"[{i+1}/{n}] DITOLAK: IP ini sudah pernah claim.")
                print("         Ganti IP dulu (matiin internet, nyalain lagi / ganti WiFi / VPN),")
                print("         terus jalanin scriptnya lagi. Akun ini belum dipakai, aman.")
                if n > 1: print("         Sisanya juga pasti ditolak di IP ini. Stop di sini."); break
            else:
                print(f"[{i+1}/{n}] GAGAL {code}: {resp.get('error', resp)}")
        except Exception as e:
            print(f"[{i+1}/{n}] ERROR {type(e).__name__}: {e}")
        if i < n - 1: time.sleep(1.5)
    print(f"\nBerhasil {ok_count} akun. Disimpen di:\n{OUT}")
    print("JAGA BAIK-BAIK file itu — isinya private key wallet kamu.")
