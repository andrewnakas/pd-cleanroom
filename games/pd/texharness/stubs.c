#include <ultra64.h>
#include "types.h"
#include "bss.h"
u8 g_Is4Mb = 0;
void texSetBitstring(u8 *bitstring) { g_TexBitstring = bitstring; g_TexAccumValue = 0; g_TexAccumNumBits = 0; }
s32 texReadBits(s32 want) { while (g_TexAccumNumBits < want) { g_TexAccumValue = g_TexAccumValue << 8 | *g_TexBitstring; g_TexBitstring++; g_TexAccumNumBits += 8; } g_TexAccumNumBits -= want; return (g_TexAccumValue >> g_TexAccumNumBits) & ((1 << want) - 1); }
u8 _texturesdataSegmentRomStart;
void dmaExec(void *a, romptr_t b, u32 c) {}
void *mempAllocFromRight(u32 a, u8 b) { return 0; }
u32 mempGetPoolFree(u8 a, u8 b) { return 0; }
s32 modTextureLoad(u16 a, void *b, u32 c) { return 0; }
void osInvalDCache(void *a, s32 b) {}
void osWritebackDCacheAll(void) {}
uintptr_t osVirtualToPhysical(void *a) { return 0; }
void *rzipGetSomething(void) { return 0; }
s32 rzipInflate(void *a, void *b, void *c) { return 0; }
