# CREW Airdrop Claimer

Auto-claim airdrop **CREW** (buildacrew.xyz). Zero-dependency — cuma butuh Python bawaan, no `pip install`.

## Apa yang dilakukan

1. Generate 1 wallet Solana baru **di lokal** (pure Python stdlib, no library).
2. Kirim claim ke `https://buildacrew.xyz/api/airdrop` — tugas follow/like/repost/reply/bell **tidak diverifikasi server-side**, langsung dikirim sebagai done.
3. Simpan handle + address + private key ke `crew_accounts.csv`.

## 2 versi

| File | Untuk | Cara ganti IP |
|------|-------|---------------|
| `crew.py` | HP / Termux | manual (mode pesawat / VPN / ganti WiFi) |
| `crew_farm.py` | VPS (WARP) | otomatis — rotate WARP tiap akun |

### crew.py — Termux / HP

```bash
pkg install python
python crew.py          # 1 akun
python crew.py 5        # 5 akun (baca catatan IP!)
```

### crew_farm.py — VPS + WARP

Butuh `warp-cli` connect + mode proxy (socks5 `127.0.0.1:40000`).

```bash
python3 crew_farm.py 20
```

Script otomatis: rotate WARP (disconnect/connect) tiap akun → tunggu IP baru → claim. Sekitar 4 detik per akun. Semua request lewat socks5 manual (`ORIG_SOCKET` + TLS), jadi gak ada request yang bocor ke IP VPS.

## Catatan penting

**1 claim per IP.** Claim kedua dari IP yang sama ditolak:
> "This network has already claimed the airdrop. One claim per person."

- `crew.py`: ganti IP tiap akun (matiin internet → nyalain lagi, ganti WiFi, atau VPN). Script otomatis kasih tau pas ketemu ini.
- `crew_farm.py`: otomatis via WARP. Kalau dapet IP yang udah kepakai, script rotate ulang sendiri (maks 5x).

**Wallet harus baru tiap claim.** Claim dengan wallet yang sudah dipakai ditolak:
> "This wallet is already on the list with another X handle."

**Rate limit global.** Terlalu banyak request cepat-cepatan → `429 Too many tries`. Kalau ini terjadi, tunggu ~1 jam.

## Keamanan

- `crew_accounts.csv` **sudah di-`.gitignore`** — gak akan pernah ke-commit.
- Private key = 32-byte seed ed25519 dalam base58 (bisa di-import ke Phantom).
- **Jangan share file CSV-nya ke siapa pun.**
- Repo ini sebaiknya tetap **PRIVATE**.

## Verifikasi generator keypair

Generator keypair-nya sudah divalidasi:
- ✅ RFC 8032 test vector 1 (pubkey `d75a9801…`)
- ✅ 300/300 sample cocok dengan output `nacl.SigningKey`

Wallet yang dihasilkan adalah wallet Solana asli. Pastikan address valid sebelum dipercaya untuk terima token — cek di explorer solscan.io.
