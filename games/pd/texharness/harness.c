/* Dirty-room only: decode PD textures with the game's own decompressor.
 * usage: harness <texdir> <first> <count> > out.bin
 * record: u16 num, u8 ok, u8 format, u8 w, u8 h, u8 numlods, u8 hasloddata, u8 iszlib, u8 ncol, u32 nbytes, bytes */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <fcntl.h>
#include <io.h>
#include <ultra64.h>
#include "constants.h"
#include "game/tex.h"
#include "game/texdecompress.h"
#include "bss.h"
#include "types.h"

s32 texInflateZlib(u8 *src, u8 *dst, bool hasloddata, s32 numlods, struct texpool *pool, bool unusedarg);
s32 texInflateNonZlib(u8 *src, u8 *dst, bool hasloddata, s32 numlods, struct texpool *pool, bool unusedarg);

int main(int argc, char **argv) {
	static u8 src[65536], dst[65536];
	static struct tex texs[4];
	struct texpool pool;
	_setmode(_fileno(stdout), _O_BINARY);
	int first = atoi(argv[2]), count = atoi(argv[3]);
	char path[512];
	for (int n = first; n < first + count; n++) {
		snprintf(path, sizeof path, "%s/%04x.bin", argv[1], n);
		FILE *f = fopen(path, "rb");
		u8 rec[12] = {0};
		rec[0] = n & 0xff; rec[1] = n >> 8;
		if (!f) { fwrite(rec, 1, 12, stdout); continue; }
		size_t len = fread(src, 1, sizeof src, f); fclose(f);
		if (len == 0) { fwrite(rec, 1, 12, stdout); continue; }
		memset(dst, 0, sizeof dst); memset(texs, 0, sizeof texs);
		pool.rightpos = &texs[1];
		texs[1].texturenum = n;
		int hasl = (src[0] & 0x80) >> 7, isz = (src[0] & 0x40) >> 6, nl = src[0] & 0x3f;
		if (nl > 5) nl = 5;
		if (isz) { fwrite(rec, 1, 12, stdout); continue; }
		s32 out = isz ? texInflateZlib(src + 1, dst, hasl, nl, &pool, 0) : texInflateNonZlib(src + 1, dst, hasl, nl, &pool, 0);
		int fmt = -1;
		rec[2] = out > 0; rec[4] = texs[1].width; rec[5] = texs[1].height; rec[6] = texs[1].numlods;
		rec[7] = hasl; rec[8] = isz; rec[9] = texs[1].unk0a;
		/* format byte: recover from the stream header */
		rec[3] = isz ? src[1] : (src[1] >> 4);
		(void)fmt;
		u32 nb = out > 0 ? out : 0;
		if (rec[3] == 6) nb *= 2; /* IA4 channel path writes a double row stride */
		memcpy(rec + 10, &nb, 2);
		fwrite(rec, 1, 12, stdout);
		fwrite(&nb, 4, 1, stdout);
		fwrite(dst, 1, nb, stdout);
	}
	return 0;
}
