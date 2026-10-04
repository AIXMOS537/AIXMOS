#!/usr/bin/env python3
"""Build a client-only release without copying any owner's memory or vault.

Reuse only dependency trees from a checksum-verified existing installer.
The private PII marker file is mandatory and never packaged.
"""
import argparse
import hashlib
from pathlib import Path
import shutil
import struct
import tempfile
import zipfile
import build_installer as build


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--base-installer', type=Path, required=True)
    ap.add_argument('--base-sha256', required=True)
    ap.add_argument('--pii-markers', type=Path, required=True)
    ap.add_argument('--output', type=Path, required=True)
    a = ap.parse_args()
    if build.sha256(a.base_installer).lower() != a.base_sha256.lower():
        ap.error('base installer checksum mismatch')
    markers = [s.strip() for s in a.pii_markers.read_text(encoding='utf-8').splitlines()
               if s.strip() and not s.startswith('#')]
    if not markers:
        ap.error('a nonempty private marker list is required')
    build.PII_MARKERS = str(a.pii_markers.resolve())
    out = a.output.resolve()
    if out.exists() and any(out.iterdir()):
        ap.error('output directory must be empty (existing releases are never deleted)')
    out.mkdir(parents=True, exist_ok=True)
    root = Path(build.ROOT)

    def app(z):
        for name in ('aixmos_local.py', 'project_aixmos_server.py', 'context_tools.py', 'index.html', 'LOCAL-AGENT.md'):
            z.write(root / name, name)
        z.write(root / 'LOCAL-AGENT.md', 'README.md')
        build.add_tree(z, str(root / 'aixmos'), 'aixmos')
        build.add_tree(z, str(root / 'skills'), 'skills')      # built-in skills ship in the product, never empty
        build.add_tree(z, str(root / 'licence'), 'licence')    # issuer PUBLIC key only (verify); never a private key
        z.writestr('memory/workspace/README.txt', 'Your local AIXMOS workspace.\n')

    with tempfile.TemporaryDirectory(prefix='aixmos-build-') as tmp:
        payload = Path(tmp) / 'payload.zip'
        dependencies = ('runtime/', 'vendor/', 'bin/', 'whisper/')
        with zipfile.ZipFile(payload, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
            app(z)
            z.write(root / 'installer/installer.py', 'setup/installer.py')
            with zipfile.ZipFile(a.base_installer) as old:
                names = set(old.namelist())
                if not {'runtime/python.exe', 'runtime/pythonw.exe'} <= names:
                    ap.error('base installer lacks the Windows runtime')
                for info in old.infolist():
                    name = info.filename
                    if name.startswith(dependencies) and not name.endswith('/'):
                        parts = Path(name).parts
                        if '..' in parts or '\\' in name or ':' in name:
                            ap.error('unsafe dependency entry')
                        z.writestr(info, old.read(name))
            z.write(root / 'installer/aixmos.ico', 'aixmos.ico')
        build.secret_gate(payload)
        stub = build.build_stub(str(root / 'installer/aixmos.ico'))
        exe = out / 'AIXMOS-Local-Agent-2.1.1-Setup.exe'
        with exe.open('wb') as target:
            for source in (Path(stub), payload):
                with source.open('rb') as f:
                    shutil.copyfileobj(f, target)
            target.write(struct.pack('<q', payload.stat().st_size) + build.MAGIC)
        unix = out / 'mac-linux'
        unix.mkdir()
        with zipfile.ZipFile(unix / 'aixmos-app.zip', 'w', zipfile.ZIP_DEFLATED) as z:
            app(z)
        build.secret_gate(unix / 'aixmos-app.zip')
        for name in ('install.sh', 'AIXMOS-Install.command'):
            data = (root / 'installer/unix' / name).read_bytes().replace(b'\r\n', b'\n')
            (unix / name).write_bytes(data)
        shutil.copyfile(root / 'LOCAL-AGENT.md', out / 'START-HERE.md')
        files = sorted(p for p in out.rglob('*') if p.is_file())
        (out / 'SHA256SUMS.txt').write_text(''.join(build.sha256(p) + '  ' + p.relative_to(out).as_posix() + '\n'
                                                  for p in files), encoding='utf-8')
        print('Built:', exe)


if __name__ == '__main__':
    main()
