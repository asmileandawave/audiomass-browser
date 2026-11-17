# AudioMass server-file browser

A read-only web audio editor built on [AudioMass](https://github.com/pkalogiros/AudioMass) that can open audio files stored on the server it runs on. The server has no sound output, so you listen in your local browser through an SSH port forward.

## Quick start

```sh
./run.sh [ROOT_DIR] [PORT]    # defaults: ~/workspace, 8765
```

The server binds to `127.0.0.1` only. From your local machine, forward the port:

```sh
ssh -L 8765:127.0.0.1:8765 user@server
```

Then open <http://localhost:8765/>. A "Server files" panel lets you browse the audio root and load a file into the editor.

It needs Python 3 and nothing else, since it uses only the standard library.

## Deep links

```
http://localhost:8765/?path=<RELATIVE_PATH>
```

`<RELATIVE_PATH>` is URL-encoded and relative to the audio root. It has no leading slash and no `..`.

- If the path is an audio file, AudioMass opens and loads it: `?path=music%2Fclip%2001.wav`
- If the path is a folder, the "Server files" panel opens in that folder: `?path=music`

## What is served

- Extensions: `wav mp3 flac ogg oga opus m4a aac aif aiff wma webm amss`. Anything else returns 404.
- Hidden (dot-prefixed) files and folders are never listed or served.
- Paths that resolve outside the root, including through symlinks, return 404.
- Everything is read-only. Nothing can be written or deleted through the server.

## HTTP API

| Endpoint | Returns |
|---|---|
| `GET /api/list?path=REL` | `{"path","dirs":[...],"files":[...]}` (audio files only); 404 `{}` if the path is bad |
| `GET /media/REL` | Raw audio bytes (whole file, no Range support) |
| `GET /?path=REL` | AudioMass UI, deep-linked as above |

## Layout

- `server.py` is the whole server. The file-browser panel and deep-link JS are the `PANEL` string, which is injected into `app/index.html` when the page is served.
- `app/` holds the unmodified AudioMass static files.
- `run.sh` is the launcher.

See `AGENTS.md` for notes aimed at coding agents.

## License

AudioMass is MIT licensed. See `LICENSE-AudioMass` and `THIRD_PARTY_NOTICES.md`.
