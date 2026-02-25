TOOLS ?= $(HOME)/tools/gcc-arm-none-eabi-8-2018-q4-major/bin
CC = $(TOOLS)/arm-none-eabi-gcc
OBJCOPY = $(TOOLS)/arm-none-eabi-objcopy
SIZE = $(TOOLS)/arm-none-eabi-size

CFLAGS  = -mcpu=cortex-m4 -mthumb -mfloat-abi=soft
CFLAGS += -Os -Wall -Wextra -Wno-unused-parameter
CFLAGS += -ffunction-sections -fdata-sections -fno-common
CFLAGS += -nostdlib -nostartfiles

LDFLAGS = -T riotboot.ld -Wl,--gc-sections -Wl,-Map=riotboot.map

SRCS = startup.c riotboot.c
OBJS = $(SRCS:.c=.o)

all: riotboot.elf riotboot.bin
	$(SIZE) riotboot.elf

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

riotboot.elf: $(OBJS)
	$(CC) $(CFLAGS) $(LDFLAGS) $^ -o $@ -lgcc

riotboot.bin: riotboot.elf
	$(OBJCOPY) -O binary $< $@

clean:
	rm -f *.o *.elf *.bin *.map

.PHONY: all clean
