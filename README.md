# CREW Airdrop Claimer

Auto-claim airdrop **CREW** (buildacrew.xyz) untuk Termux/Android. Zero-dependency — cuma butuh Python bawaan, no `pip install`.

## Apa yang dilakukan

1. Generate 1 wallet Solana baru **di lokal** (pure Python stdlib, no library).
2. Kirim claim ke `https://buildacrew.xyz/api/airdrop` — tugas follow/like/repost/reply/bell **tidak diverifikasi server-side**, langsung dikirim sebagai done.
3. Simpan handle + address + private key ke `crew_accounts.csv`.

## Cara pakai (Termux)

```bash
pkg install python
python crew.py          # 1 akun
python crew.py 5        # 5 akun (baca catatan IP!)
```

## Catatan penting

**1 claim per IP.** Claim kedua dari IP yang sama ditolak:
> "This network has already claimed the airdrop. One claim per person."

Untuk multi-akun: ganti IP tiap akun (matiin internet → nyalain lagi, ganti WiFi, atau VPN). Script otomatis kasih tau pas ketemu ini.

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
