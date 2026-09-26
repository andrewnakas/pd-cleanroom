"""DIRTY ROOM / DEV ONLY: dump a retail ROM into the external data-pack layout
the web build loads (never commit or publish the output).

Layout (mirrored by the clean pack):
  <out>/filenames.lst   file names in file-number order (file 1 first), one per line
  <out>/files/<name>    raw ROM bytes of file <name> (as stored: 1173-zipped where the ROM zips)
  <out>/segs/<seg>      raw ROM bytes of each segment in port/src/romdata.c ROMSEG_LIST (ntsc-final)

usage: python -m games.pd.dev_dump_pack <rom.z64> <outdir> [--romdata port/src/romdata.c]
"""
import os, re, sys, zlib

DATA_OFS = 0x39850      # 1173-compressed data segment (ntsc-final)
FILES_OFS = 0x28080     # file offset table inside the inflated data segment


def rzip(buf):
    assert buf[0:2] == b'\x11\x73', 'not 1173-compressed'
    return zlib.decompressobj(wbits=-15).decompress(buf[5:])


def seg_list(romdata_c):
    src = open(romdata_c, encoding='utf-8').read()
    segs = []
    for m in re.finditer(r'ROMSEG_DECL_SEG\((\w+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),\s*(0x[0-9a-fA-F]+),', src):
        segs.append((m.group(1), int(m.group(2), 16), int(m.group(5), 16)))
    return segs


def main():
    args = sys.argv[1:]
    romdata = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'pd', 'pcport', 'port', 'src', 'romdata.c')
    if '--romdata' in args:
        i = args.index('--romdata'); romdata = args[i + 1]; del args[i:i + 2]
    rompath, out = args
    rom = open(rompath, 'rb').read()
    os.makedirs(os.path.join(out, 'segs'), exist_ok=True)
    os.makedirs(os.path.join(out, 'files'), exist_ok=True)

    segs = seg_list(romdata)
    nseg = 0
    for i, (name, ofs, size) in enumerate(segs):
        if not ofs:
            continue
        if not size:
            size = (segs[i + 1][1] if i + 1 < len(segs) else len(rom)) - ofs
        open(os.path.join(out, 'segs', name), 'wb').write(rom[ofs:ofs + size])
        nseg += 1

    data = rzip(rom[DATA_OFS:])
    offs = []
    p = FILES_OFS
    while True:
        o = int.from_bytes(data[p:p + 4], 'big')
        if o == 0 and offs:
            break
        offs.append(o); p += 4
    table = offs[-1]
    names = []
    i = 4
    while True:
        o = int.from_bytes(rom[table + i:table + i + 4], 'big')
        if o == 0:
            break
        a = table + o
        names.append(rom[a:rom.index(0, a)].decode())
        i += 4
    # file n (1-based) spans offs[n]..offs[n+1]
    total = 0
    for n, name in enumerate(names, start=1):
        blob = rom[offs[n]:offs[n + 1]]
        path = os.path.join(out, 'files', name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(blob)
        total += len(blob)
    open(os.path.join(out, 'filenames.lst'), 'w', newline='\n').write('\n'.join(names) + '\n')
    print(f'segs {nseg}  files {len(names)} ({total/1e6:.1f} MB)  -> {out}')


if __name__ == '__main__':
    main()
