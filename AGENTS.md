# AudioMass server-file browser — guide for agents

A read-only web audio editor ([AudioMass](https://github.com/pkalogiros/AudioMass))
that can open audio files that live on this server. The human listens in their local
browser through an SSH port forward; the server itself has no sound output.

## Linking to a file (the main thing you need)

Build a URL of the form:

    http://localhost:8765/?path=<RELATIVE_PATH>

- `<RELATIVE_PATH>` is relative to the server's **audio root** (default `~/workspace`,
  i.e. `/mnt/efs/home/colm`), URL-encoded. No leading slash, no `..`.
- Path is an audio file → AudioMass opens and loads it.
  `http://localhost:8765/?path=tr_zh%2Fout%2Fclip%2001.wav`
- Path is a folder → the "Server files" panel opens in that folder.
  `http://localhost:8765/?path=tr_zh%2Fout`

Encode with e.g. `python3 -c 'import urllib.parse,sys;print(urllib.parse.quote(sys.argv[1],safe=""))' "dir/my file.wav"`.
To get the relative path from an absolute one, strip the root prefix
(`realpath --relative-to=/mnt/efs/home/colm /abs/file.wav`). Files outside the root
cannot be linked; either copy them under the root or ask the user to restart with a different `--root`.

The link only works if the user has the tunnel up:
`ssh -L 8765:127.0.0.1:8765 colm@<server>` — mention this when handing over a link.

## What is served

- Extensions: wav mp3 flac ogg oga opus m4a aac aif aiff wma webm amss. Anything else is 404.
- Hidden files/folders (dot-prefixed) are never listed or served.
- Paths that resolve (including via symlink) outside the root are 404.
- Read-only; nothing can be written or deleted through this server.

## HTTP API

| Endpoint | Returns |
|---|---|
| `GET /api/list?path=REL` | `{"path","dirs":[...],"files":[...]}` (audio files only); 404 `{}` if bad |
| `GET /media/REL` | raw audio bytes (no Range support; whole file) |
| `GET /?path=REL` | AudioMass UI, deep-linked as above |

Quick existence check before giving a link:
`curl -s -o /dev/null -w '%{http_code}' 'http://127.0.0.1:8765/media/REL'` → `200`.

## Running / restarting

    ./run.sh [ROOT_DIR] [PORT]        # defaults: ~/workspace, 8765

Binds to 127.0.0.1 only. Check it's up: `ss -ltnp | grep 8765`.
To restart, kill by PID from `ss` — do **not** `pkill -f` a pattern that appears in your own
command line, it will kill your shell. Logs: run with `nohup ./run.sh >/tmp/audiomass.log 2>&1 &`.
Port 8080 is used by something else on this host; don't use it.

## Layout

- `server.py` — the whole server (stdlib Python 3, no dependencies). The file-browser panel
  and deep-link JS are the `PANEL` string; they are injected into `app/index.html` at serve time.
- `app/` — unmodified AudioMass static files (MIT; see `LICENSE-AudioMass`, `THIRD_PARTY_NOTICES.md`).
- AudioMass loads URLs via `PKAudioEditor.engine.LoadURL(url)` (same-origin).
