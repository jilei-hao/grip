# Setting Up the Slack Bot for GRIP

GRIP can post the daily digest in **threaded mode**, where each paper appears as
a separate thread reply. This lets team members react 👍 / 👎 on individual
papers, which feeds directly into GRIP's profile-update loop.

Threaded mode requires a **Slack Bot Token** and a **Channel ID**.  
If you only have an Incoming Webhook, GRIP falls back to a single non-threaded
post automatically.

---

## 1. Create a Slack App

1. Go to <https://api.slack.com/apps> and click **Create New App**.
2. Choose **From scratch**.
3. Give it a name (e.g. `GRIP`) and select your workspace.
4. Click **Create App**.

---

## 2. Add OAuth Scopes

1. In the left sidebar, go to **OAuth & Permissions**.
2. Scroll to **Bot Token Scopes** and add:

   | Scope | Why |
   |---|---|
   | `chat:write` | Post messages and thread replies |
   | `reactions:read` | Read 👍 / 👎 reactions for feedback (future use) |

3. Click **Save Changes**.

---

## 3. Install the App to Your Workspace

1. Scroll up to the top of **OAuth & Permissions**.
2. Click **Install to Workspace** and approve the permissions.
3. Copy the **Bot User OAuth Token** — it starts with `xoxb-`.

---

## 4. Find Your Channel ID

1. In Slack, open the channel you want GRIP to post to.
2. Click the channel name at the top to open channel details.
3. Scroll to the bottom of the **About** tab — the Channel ID looks like
   `C01234ABCDE`.

Alternatively, right-click the channel in the sidebar → **Copy link** — the ID
is the last path segment of the URL.

---

## 5. Invite the Bot to the Channel

In Slack, type the following in the target channel:

```
/invite @GRIP
```

Without this step the bot cannot post, even with correct credentials.

---

## 6. Set Environment Variables

Copy `.env.example` to `.env` (if you haven't already) and fill in the values:

```sh
cp .env.example .env
```

Then edit `.env`:

```dotenv
GRIP_SLACK_BOT_TOKEN=xoxb-your-token-here
GRIP_SLACK_CHANNEL_ID=C01234ABCDE
```

GRIP loads `.env` automatically via `python-dotenv` on every run — no shell
exports needed.

> **Tip:** If both variables are set, GRIP uses threaded mode automatically.
> If only `GRIP_SLACK_WEBHOOK` is set, GRIP falls back to a single webhook post.

---

## 7. Verify

Run GRIP manually to confirm the bot posts correctly:

```sh
grip
```

You should see a compact digest header in the channel and one thread reply per
paper. React 👍 or 👎 on any thread reply to record feedback.

---

## Environment Variable Reference

| Variable | Required for | Description |
|---|---|---|
| `GRIP_SLACK_BOT_TOKEN` | Threaded mode | Bot User OAuth Token (`xoxb-…`) |
| `GRIP_SLACK_CHANNEL_ID` | Threaded mode | Target channel ID (`C…`) |
| `GRIP_SLACK_WEBHOOK` | Webhook fallback | Incoming Webhook URL |

At least one of (token + channel) or webhook must be configured.
