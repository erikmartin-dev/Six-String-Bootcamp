# Hosting the Six-String Bootcamp web app

The phone apps are just a shell — the real app runs here, on a server.
Any cheap VPS works. This guide uses Hetzner (~$5/mo, pay with card).

## 1. Create the server

1. Sign up at hetzner.com/cloud (account + payment method).
2. New project → Add Server:
   - Location: Ashburn, VA (closest to Alabama)
   - Image: Ubuntu 24.04
   - Type: CX22 (2 vCPU, 4 GB RAM) — plenty for Streamlit
   - Networking: IPv4 checked
3. Note the server's IPv4 address.

## 2. Point your domain at it

At your domain registrar (Namecheap, Cloudflare, etc.), add:

- `A` record: `sixstringbootcamp.com` → your server IP
- `A` record: `www.sixstringbootcamp.com` → your server IP

(Use your real domain if different — then update `mobile/capacitor.config.ts`.)

## 3. Set up the server

SSH in as root and run the bundled script:

```
git clone https://github.com/erikmartin-dev/Six-String-Bootcamp.git
cd Six-String-Bootcamp/mobile
bash server-setup.sh sixstringbootcamp.com
```

The script installs Python, nginx, and certbot; installs the app's
requirements; creates a systemd service so Streamlit restarts on reboot;
and gets a free HTTPS certificate. Takes ~5 minutes.

## 4. Verify

Open `https://sixstringbootcamp.com` in your phone browser — the full app
should load. Then the wrapper's `server.url` already points there, so the
next Actions build produces an APK that just works.

## Updating the app later

```
cd ~/Six-String-Bootcamp && git pull && sudo systemctl restart sixstring
```

(Tip: add a tiny deploy webhook or cron later — for now, SSH + pull is fine.)
