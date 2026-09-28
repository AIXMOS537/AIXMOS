"""extract-linux-ollama.py - unpack the official ollama-linux-amd64.tar.zst, CPU parts only.

    python extract-linux-ollama.py <ollama-linux-amd64.tar.zst> <dest dir>

Why this exists: Windows' bsdtar here has no zstd, but Python 3.14's tarfile
does. The Surface has no usable GPU, so the CUDA / ROCm / MLX libraries - most
of the 1.3 GB - are dropped. The stick is FAT32/exFAT, which cannot hold
symlinks, so links are written out as real copies of their targets.
"""
import os, shutil, sys, tarfile

DROP = ("cuda_", "rocm", "mlx")


def norm(name):
    name = name.replace("\\", "/")
    while name.startswith("./"):
        name = name[2:]
    return name.strip("/")


def keep(name):
    return not any(part.startswith(DROP) for part in name.split("/"))


def main(src, dst):
    os.makedirs(dst, exist_ok=True)
    links, files, size = [], 0, 0
    # Stream mode: one forward pass, no seeking back through a 1.3 GB zstd stream.
    with tarfile.open(src, "r|zst") as t:
        for m in t:
            n = norm(m.name)
            if not n or not keep(n):
                continue
            out = os.path.join(dst, *n.split("/"))
            if m.isdir():
                os.makedirs(out, exist_ok=True)
            elif m.issym() or m.islnk():
                target = norm(m.linkname) if m.islnk() else norm(os.path.normpath(
                    os.path.join(os.path.dirname(n), m.linkname)).replace("\\", "/"))
                links.append((n, target))
            elif m.isfile():
                os.makedirs(os.path.dirname(out), exist_ok=True)
                with t.extractfile(m) as f, open(out, "wb") as o:
                    shutil.copyfileobj(f, o)
                files += 1
                size += m.size
    # Links last, once every target they could point at is on disk. Chains resolve
    # because each pass copies whatever now exists.
    pending = links
    for _ in range(5):
        left = []
        for n, target in pending:
            src_path = os.path.join(dst, *target.split("/"))
            if os.path.isfile(src_path):
                out = os.path.join(dst, *n.split("/"))
                os.makedirs(os.path.dirname(out), exist_ok=True)
                shutil.copyfile(src_path, out)
                files += 1
                size += os.path.getsize(out)
            else:
                left.append((n, target))
        pending = left
    for n, target in pending:
        print("  link not materialized (target dropped or missing): %s -> %s" % (n, target))
    print("%d files, %.1f MB -> %s" % (files, size / 1048576.0, dst))
    if not os.path.isfile(os.path.join(dst, "bin", "ollama")):
        sys.exit("bin/ollama missing after extract")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
