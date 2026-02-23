TOOLCHAIN_PREFIX ?= arm-none-eabi-
CC := $(TOOLCHAIN_PREFIX)gcc
OBJCOPY := $(TOOLCHAIN_PREFIX)objcopy

CFLAGS := -mcpu=cortex-m0plus -mthumb -O2 -g -ffreestanding -fno-builtin -fdata-sections -ffunction-sections
LDFLAGS := -nostdlib -Wl,--gc-sections

# Use the resilient_ota linker script and include path.
LINKER := ../resilient_ota/linker_boot.ld
INCLUDES := -I../resilient_ota

VARIANTS := \
	bootloader_none \
	bootloader_no_fallback \
	bootloader_no_vector_check \
	bootloader_both_replicas_race \
	bootloader_crc_off_by_one \
	bootloader_seq_naive \
	bootloader_no_boot_count

ELF_TARGETS := $(addsuffix .elf,$(VARIANTS))
BIN_TARGETS := $(addsuffix .bin,$(VARIANTS))

.PHONY: all clean

all: $(ELF_TARGETS) $(BIN_TARGETS)

bootloader_none.elf: bootloader_variants.c ../resilient_ota/boot_meta.h $(LINKER)
	$(CC) $(CFLAGS) $(INCLUDES) -DDEFECT=DEFECT_NONE $(LDFLAGS) -T $(LINKER) -o $@ $<

bootloader_no_fallback.elf: bootloader_variants.c ../resilient_ota/boot_meta.h $(LINKER)
	$(CC) $(CFLAGS) $(INCLUDES) -DDEFECT=DEFECT_NO_FALLBACK $(LDFLAGS) -T $(LINKER) -o $@ $<

bootloader_no_vector_check.elf: bootloader_variants.c ../resilient_ota/boot_meta.h $(LINKER)
	$(CC) $(CFLAGS) $(INCLUDES) -DDEFECT=DEFECT_NO_VECTOR_CHECK $(LDFLAGS) -T $(LINKER) -o $@ $<

bootloader_both_replicas_race.elf: bootloader_variants.c ../resilient_ota/boot_meta.h $(LINKER)
	$(CC) $(CFLAGS) $(INCLUDES) -DDEFECT=DEFECT_BOTH_REPLICAS_RACE $(LDFLAGS) -T $(LINKER) -o $@ $<

bootloader_crc_off_by_one.elf: bootloader_variants.c ../resilient_ota/boot_meta.h $(LINKER)
	$(CC) $(CFLAGS) $(INCLUDES) -DDEFECT=DEFECT_CRC_OFF_BY_ONE $(LDFLAGS) -T $(LINKER) -o $@ $<

bootloader_seq_naive.elf: bootloader_variants.c ../resilient_ota/boot_meta.h $(LINKER)
	$(CC) $(CFLAGS) $(INCLUDES) -DDEFECT=DEFECT_SEQ_NAIVE $(LDFLAGS) -T $(LINKER) -o $@ $<

bootloader_no_boot_count.elf: bootloader_variants.c ../resilient_ota/boot_meta.h $(LINKER)
	$(CC) $(CFLAGS) $(INCLUDES) -DDEFECT=DEFECT_NO_BOOT_COUNT $(LDFLAGS) -T $(LINKER) -o $@ $<

%.bin: %.elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f $(ELF_TARGETS) $(BIN_TARGETS)
