#!/usr/bin/env python3
"""AudioMass + read-only server-side audio browser.

Usage: server.py [--root DIR] [--port N] [--app DIR]

Deep links (path is relative to --root, URL-encoded):
  /?path=music/song.wav   -> opens AudioMass with that file loaded
  /?path=music            -> opens the file browser panel in that folder

- Serves the AudioMass static app (index.html gets a file-browser panel injected).
- GET /api/list?path=REL  -> JSON listing of subdirs + audio files under --root
- GET /media/REL          -> audio file bytes (audio extensions only, no traversal)
Binds to 127.0.0.1 only; reach it with an SSH port forward.
"""
import argparse, json, mimetypes, os, sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, unquote

AUDIO_EXT = {'.wav', '.mp3', '.flac', '.ogg', '.oga', '.opus', '.m4a', '.aac', '.aif', '.aiff', '.wma', '.webm', '.amss'}

PANEL = r"""
<style>
#sb{position:fixed;right:8px;bottom:8px;z-index:99999;font:12px sans-serif;color:#ddd}
#sb button.t{background:#333;color:#ddd;border:1px solid #666;padding:4px 8px;cursor:pointer}
#sb .p{display:none;width:340px;max-height:60vh;overflow:auto;background:#222;border:1px solid #666;margin-bottom:4px;padding:6px}
#sb.o .p{display:block}
#sb .p div{padding:3px 4px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
#sb .p div:hover{background:#444}
#sb .path{color:#9cf;cursor:default!important;border-bottom:1px solid #444;margin-bottom:4px}
</style>
<div id="sb"><div class="p"></div><button class="t">Server files</button></div>
<script>
(function(){
  var sb=document.getElementById('sb'), p=sb.querySelector('.p'), cur='';
  var AUDIO=/\.(wav|mp3|flac|ogg|oga|opus|m4a|aac|aif|aiff|wma|webm|amss)$/i;
  function load(rel){
    var url=location.origin+'/media/'+rel.split('/').map(encodeURIComponent).join('/');
    history.replaceState(null,'','/?path='+encodeURIComponent(rel));
    PKAudioEditor.engine.LoadURL(url);
  }
  sb.querySelector('.t').onclick=function(){sb.classList.toggle('o'); if(sb.classList.contains('o')) ls(cur);};
  function row(txt,fn){var d=document.createElement('div');d.textContent=txt;d.title=txt;d.onclick=fn;p.appendChild(d);}
  function ls(path,cb){
    fetch('/api/list?path='+encodeURIComponent(path)).then(function(r){return r.json();}).then(function(j){
      if(!j.dirs) return;
      cur=j.path; p.innerHTML='';
      var h=document.createElement('div');h.className='path';h.textContent='/'+cur;p.appendChild(h);
      if(cur) row('↑ ..',function(){ls(cur.split('/').slice(0,-1).join('/'));});
      j.dirs.forEach(function(d){row('📁 '+d,function(){ls(cur?cur+'/'+d:d);});});
      j.files.forEach(function(f){row('♫ '+f,function(){
        load(cur?cur+'/'+f:f);
      });});
      cb&&cb();
    });
  }
  var q=new URLSearchParams(location.search).get('path');
  if(q){
    q=q.replace(/^\/+|\/+$/g,'');
    if(AUDIO.test(q)){
      ls(q.split('/').slice(0,-1).join('/'));  // prime the panel at the file's folder
      setTimeout(function(){load(q);},300);     // let the editor finish init
    } else { sb.classList.add('o'); ls(q); }
  }
})();
</script>
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--root', default=os.path.expanduser('~'))
    ap.add_argument('--port', type=int, default=8765)
    ap.add_argument('--app', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'app'))
    a = ap.parse_args()
    root = os.path.realpath(a.root)
    app_dir = os.path.realpath(a.app)

    def safe(rel):
        """Resolve rel under root; return None if it escapes or is hidden."""
        parts = [x for x in rel.split('/') if x]
        if any(x.startswith('.') for x in parts):
            return None
        full = os.path.realpath(os.path.join(root, *parts))
        if full != root and not full.startswith(root + os.sep):
            return None
        return full

    class H(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kw):
            super().__init__(*args, directory=app_dir, **kw)

        def _send(self, code, body, ctype):
            self.send_response(code)
            self.send_header('Content-Type', ctype)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            u = urlparse(self.path)
            if u.path == '/api/list':
                rel = parse_qs(u.query).get('path', [''])[0]
                full = safe(rel)
                if not full or not os.path.isdir(full):
                    return self._send(404, b'{}', 'application/json')
                dirs, files = [], []
                for n in sorted(os.listdir(full), key=str.lower):
                    if n.startswith('.'):
                        continue
                    fp = os.path.join(full, n)
                    if os.path.isdir(fp):
                        dirs.append(n)
                    elif os.path.splitext(n)[1].lower() in AUDIO_EXT:
                        files.append(n)
                out = {'path': '' if full == root else os.path.relpath(full, root),
                       'dirs': dirs, 'files': files}
                return self._send(200, json.dumps(out).encode(), 'application/json')
            if u.path.startswith('/media/'):
                full = safe(unquote(u.path[len('/media/'):]))
                if (not full or not os.path.isfile(full)
                        or os.path.splitext(full)[1].lower() not in AUDIO_EXT):
                    return self._send(404, b'not found', 'text/plain')
                with open(full, 'rb') as f:
                    data = f.read()
                ctype = mimetypes.guess_type(full)[0] or 'application/octet-stream'
                return self._send(200, data, ctype)
            if u.path in ('/', '/index.html'):
                with open(os.path.join(app_dir, 'index.html'), 'rb') as f:
                    html = f.read().decode('utf-8', 'replace')
                html = html.replace('</body>', PANEL + '</body>', 1)
                return self._send(200, html.encode(), 'text/html; charset=utf-8')
            return super().do_GET()

    srv = ThreadingHTTPServer(('127.0.0.1', a.port), H)
    print(f'AudioMass on http://127.0.0.1:{a.port}  (audio root: {root})', flush=True)
    srv.serve_forever()


if __name__ == '__main__':
    main()
