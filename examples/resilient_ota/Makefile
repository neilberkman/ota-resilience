TOOLCHAIN_PREFIX ?= arm-none-eabi-
CC := $(TOOLCHAIN_PREFIX)gcc
OBJCOPY := $(TOOLCHAIN_PREFIX)objcopy

TARGET_CPU ?= cortex-m0plus

# VTOR relocation should be enabled on targets that implement VTOR
# (e.g. Cortex-M0+, M3, M4, M7). Cortex-M0 does not provide VTOR.
ifeq ($(TARGET_CPU),cortex-m0)
ENABLE_VTOR_RELOCATION ?= 0
else
ENABLE_VTOR_RELOCATION ?= 1
endif

CFLAGS := -mcpu=$(TARGET_CPU) -mthumb -O2 -g -ffreestanding -fno-builtin -fdata-sections -ffunction-sections
CFLAGS += -DENABLE_VTOR_RELOCATION=$(ENABLE_VTOR_RELOCATION)
LDFLAGS_COMMON := -nostdlib -Wl,--gc-sections

.PHONY: all clean

all: bootloader.elf bootloader.bin slot_a.elf slot_a.bin slot_b.elf slot_b.bin slot_b_bad.elf slot_b_bad.bin boot_meta.bin

bootloader.elf: bootloader.c boot_meta.h linker_boot.ld
	$(CC) $(CFLAGS) $(LDFLAGS_COMMON) -T linker_boot.ld -o $@ bootloader.c

slot_a.elf: firmware.c boot_meta.h linker_slot_a.ld
	$(CC) $(CFLAGS) -DSLOT_ID=0 $(LDFLAGS_COMMON) -T linker_slot_a.ld -o $@ firmware.c

slot_b.elf: firmware.c boot_meta.h linker_slot_b.ld
	$(CC) $(CFLAGS) -DSLOT_ID=1 $(LDFLAGS_COMMON) -T linker_slot_b.ld -o $@ firmware.c

slot_b_bad.elf: firmware_bad.c linker_slot_b.ld
	$(CC) $(CFLAGS) -DSLOT_ID=1 $(LDFLAGS_COMMON) -T linker_slot_b.ld -o $@ firmware_bad.c

bootloader.bin: bootloader.elf
	$(OBJCOPY) -O binary $< $@

slot_a.bin: slot_a.elf
	$(OBJCOPY) -O binary $< $@

slot_b.bin: slot_b.elf
	$(OBJCOPY) -O binary $< $@

slot_b_bad.bin: slot_b_bad.elf
	$(OBJCOPY) -O binary $< $@

boot_meta.bin: gen_boot_meta.py
	python3 gen_boot_meta.py

clean:
	rm -f bootloader.elf bootloader.bin slot_a.elf slot_a.bin slot_b.elf slot_b.bin slot_b_bad.elf slot_b_bad.bin boot_meta.bin
