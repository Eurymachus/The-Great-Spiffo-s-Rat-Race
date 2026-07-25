# Live Notifications

## Contract

The database remains the authority for participant notifications. Live delivery
does not carry or persist notification records:

1. The ASGI application holds a Server-Sent Events (SSE) connection to the
   signed-in browser.
2. The stream emits `notifications-changed` when the participant's notification
   state changes.
3. The browser immediately fetches the authenticated notification-summary JSON.
4. That response replaces the bell count and dropdown contents without a page
   refresh.
5. When the participant dashboard is open, the same invalidation fetches a
   server-rendered dashboard fragment. Personal Best, Active Runs, Past Runs,
   Awaiting Review, and run-detail dialogs update in place without resetting the
   page or scroll position.

The toast presents only the notification title:

- One new item: **New notification received**, followed by its title.
- Several new items: **N new notifications received**, followed by a prompt to
  open notifications.

The initial page load never produces a toast.

## Failure behaviour

Live notification delivery is an enhancement, not a prerequisite for normal use.
If SSE cannot connect, the browser checks the same JSON summary every 60 seconds
while the tab is visible. Opening pages and the complete notification history
continue to work normally.

The SSE endpoint deliberately returns `503` under WSGI. This prevents a
long-lived request from occupying a WSGI worker; the browser then uses its polling
fallback. Run the website through `config.asgi:application` to enable SSE.

## Local development

From the repository root:

```powershell
.\.venv\Scripts\python -m uvicorn config.asgi:application `
  --app-dir .\apps\website --reload
```

Django's WSGI application remains available for compatibility and emergency
rollback, but it does not provide the live stream.

When Django debug mode is enabled, the ASGI entry point wraps the application in
Django's development static-file handler. Production must serve collected static
files through its normal deployment static-file layer.

## Production boundary

The current stream checks the database periodically and is suitable for local
development and a small single-process deployment. Before running multiple web
workers or scaling participant traffic, replace that check with a shared event
bus such as Redis and configure the reverse proxy not to buffer SSE responses.
The JSON summary and database notification records remain authoritative after
that change.
