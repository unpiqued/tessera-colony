"""Wrap dist/tessera-colony.html in the same skeleton the artifact viewer adds, for local browser tests."""
import sys, pathlib
src = pathlib.Path(sys.argv[1]).read_text()
out = pathlib.Path(sys.argv[2])
skel = ('<!doctype html><html><head><meta charset=utf8><meta name=viewport content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top);padding-bottom:env(safe-area-inset-bottom)}body{margin:0;font:14px system-ui}'
        'img{max-width:100%}[hidden]{display:none!important}</style></head><body>')
out.write_text(skel + src + '</body></html>')
