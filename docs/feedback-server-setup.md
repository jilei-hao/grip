# Setting Up the GRIP Feedback Server

GRIP can collect feedback in two ways:

| Mode | How it works | When to use |
|---|---|---|
| **Polling** *(default)* | `grip --update-profile` polls Slack for reactions + thread replies | No server needed; runs on the same machine as the digest cron |
| **Events API** *(this guide)* | Slack pushes `reaction_added`/`reaction_removed` events to your endpoint in real-time | When you want immediate logging or can't run polling cron |

Both modes write to the same JSONL feedback log and feed into the same profile update loop. You can run both simultaneously — polling will pick up anything the push server missed.

---

## Prerequisites

1. Complete [slack-bot-setup.md](slack-bot-setup.md) first — you need a bot token and channel ID.
2. Install the Flask dependency:
   ```sh
   pip install "grip[feedback-server]"
   # or, if using the editable install:
   pip install -e ".[feedback-server]"
   ```
3. Add your Slack **Signing Secret** to `.env`:
   ```dotenv
   GRIP_SLACK_SIGNING_SECRET=your-signing-secret-here
   ```
   Find it in the Slack app settings under **Basic Information → App Credentials**.

---

## Part 1 — Local Development (ngrok)

Use this when testing locally before deploying to a server.

### Step 1 — Start the feedback server

```sh
# In terminal 1
grip-feedback-server
# Server starts on http://0.0.0.0:5000
```

### Step 2 — Expose it with ngrok

```sh
# In terminal 2
ngrok http 5000
```

ngrok prints a public URL like `https://abc123.ngrok-free.app`. Copy it.

### Step 3 — Configure Slack Events API

1. Go to your Slack app → **Event Subscriptions**.
2. Toggle **Enable Events** to On.
3. Set **Request URL** to:
   ```
   https://abc123.ngrok-free.app/slack/events
   ```
4. Slack sends a verification challenge — the server handles it automatically.
5. Under **Subscribe to bot events**, add:
   - `reaction_added`
   - `reaction_removed`
6. Click **Save Changes**.

### Step 4 — Test

React 👍 or 👎 on a GRIP digest paper in Slack. You should see a log line:
```
[feedback] Logged positive reaction on 1741804801.234567
```
And a new entry in `data/feedback_log/YYYY-MM-DD.jsonl`.

---

## Part 2 — Production: Systemd Service (Linux)

Use this for a persistent deployment on a Linux server (VPS, lab server, etc.).

### Step 1 — Ensure the server is accessible

The machine must have a public IP or be behind a reverse proxy (nginx/caddy) with a domain name. Slack requires HTTPS.

### Step 2 — Install and start the service

```sh
bash scripts/setup_feedback_service.sh
```

This creates a **systemd user service** that:
- Starts automatically at boot (with linger enabled)
- Restarts on failure
- Logs to `logs/feedback_server.log`

Enable linger so the service survives logout:
```sh
loginctl enable-linger "$(whoami)"
```

### Step 3 — Set up HTTPS with a reverse proxy

If your server is behind nginx, add a location block:

```nginx
server {
    listen 443 ssl;
    server_name grip.yourdomain.com;

    # SSL config (Let's Encrypt / certbot)
    ssl_certificate     /etc/letsencrypt/live/grip.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/grip.yourdomain.com/privkey.pem;

    location /slack/events {
        proxy_pass         http://127.0.0.1:5000/slack/events;
        proxy_set_header   Host $host;
        proxy_set_header   X-Slack-Request-Timestamp $http_x_slack_request_timestamp;
        proxy_set_header   X-Slack-Signature         $http_x_slack_signature;
    }

    location /health {
        proxy_pass http://127.0.0.1:5000/health;
    }
}
```

> **Important:** Forward the `X-Slack-Request-Timestamp` and `X-Slack-Signature` headers — they're needed for signature verification.

### Step 4 — Configure Slack Events API

Same as local dev (Step 3 above), but use your production URL:
```
https://grip.yourdomain.com/slack/events
```

### Step 5 — Manage the service

```sh
systemctl --user status  grip-feedback     # check status
systemctl --user restart grip-feedback     # restart after config change
systemctl --user stop    grip-feedback     # stop
journalctl --user -u grip-feedback -f      # follow logs
bash scripts/setup_feedback_service.sh --remove  # uninstall
```

---

## Part 3 — Remove and Reinstall the Service

```sh
# Uninstall
bash scripts/setup_feedback_service.sh --remove

# Reinstall (after changing .env or updating code)
bash scripts/setup_feedback_service.sh
```

---

## Configuration Reference

| Variable | Required | Description |
|---|---|---|
| `GRIP_SLACK_SIGNING_SECRET` | Recommended | Signs Slack webhook payloads. Without it, any POST to `/slack/events` is accepted (unsafe for production). |
| `GRIP_SERVER_HOST` | No | Bind address (default: `0.0.0.0`) |
| `GRIP_SERVER_PORT` | No | Port (default: `5000`) |
| `GRIP_SERVER_DEBUG` | No | Enable Flask debug mode (default: `false`; never use in production) |

---

## How Feedback Flows

```
Slack user reacts 👍/👎 on a paper
         │
         ▼
Slack Events API  ──POST /slack/events──▶  grip-feedback-server (Flask)
                                                    │
                                            FeedbackCollector.handle_reaction()
                                                    │
                                            data/feedback_log/YYYY-MM-DD.jsonl
                                                    │
                              (weekly) grip --update-profile
                                                    │
                                            ProfileUpdater.run_update()
                                                    │
                                            Claude updates interest_profile.txt
```

Polling (`poll_feedback()`) runs as part of `grip --update-profile` to catch any reactions that arrived while the server was down or before it was deployed.

---

## Troubleshooting

**Slack shows "Your URL didn't respond with the value of the `challenge` parameter"**
→ The server isn't reachable from the internet. Check your ngrok URL or reverse proxy config.

**Signature verification failures (`403 Forbidden`)**
→ Ensure `GRIP_SLACK_SIGNING_SECRET` matches the value in Slack → Basic Information → App Credentials. Also check that your reverse proxy forwards `X-Slack-Signature` and `X-Slack-Request-Timestamp` headers.

**No entries in feedback_log after reacting**
→ Check that you subscribed to `reaction_added` and `reaction_removed` in Slack Event Subscriptions → Subscribe to bot events (not workspace events).

**Service doesn't start after reboot**
→ Run `loginctl enable-linger $(whoami)` to enable persistent user services.
