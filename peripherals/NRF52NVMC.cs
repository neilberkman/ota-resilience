// Copyright (c) 2026
// SPDX-License-Identifier: Apache-2.0
//
// Minimal nRF52840 NVMC (Non-Volatile Memory Controller) stub.
// Handles CONFIG (write/erase enable), ERASEPAGE, and READY.
// Delegates sector erase to NVMemory.EraseSector (bypasses write tracking).

using System;

using Antmicro.Renode.Core;
using Antmicro.Renode.Core.Structure.Registers;
using Antmicro.Renode.Peripherals;
using Antmicro.Renode.Peripherals.Bus;
using Antmicro.Renode.Peripherals.Memory;

namespace Antmicro.Renode.Peripherals.Miscellaneous
{
    public class NRF52NVMC : BasicDoubleWordPeripheral, IKnownSize
    {
        public NRF52NVMC(IMachine machine) : base(machine)
        {
            DefineRegisters();
        }

        public long Size => 0x1000;

        public NVMemory Nvm { get; set; }

        public long NvmBaseAddress { get; set; } = 0x00000000;

        public int PageSize { get; set; } = 4096;

        private uint configValue = 0;

        private void DefineRegisters()
        {
            // READY at 0x400 — always ready (instant operations).
            Registers.Ready.Define(this, 1);

            // READYNEXT at 0x408 — always ready.
            Registers.ReadyNext.Define(this, 1);

            // CONFIG at 0x504 — write enable mode.
            Registers.Config.Define(this)
                .WithValueField(0, 2, writeCallback: (_, val) =>
                {
                    configValue = (uint)val;
                }, valueProviderCallback: _ => configValue, name: "WEN");

            // ERASEPAGE at 0x508 — write page address to erase.
            Registers.ErasePage.Define(this)
                .WithValueField(0, 32, writeCallback: (_, val) =>
                {
                    if(configValue == 2 && Nvm != null)
                    {
                        var pageAddr = (long)val;
                        var offset = pageAddr - NvmBaseAddress;
                        if(offset >= 0 && offset + PageSize <= Nvm.Size)
                        {
                            Nvm.EraseSector(offset, PageSize);
                        }
                    }
                }, name: "ERASEPAGE");

            // ERASEALL at 0x50C.
            Registers.EraseAll.Define(this)
                .WithValueField(0, 1, writeCallback: (_, val) =>
                {
                    if(val == 1 && configValue == 2 && Nvm != null)
                    {
                        for(long offset = 0; offset < Nvm.Size; offset += PageSize)
                        {
                            var remaining = (int)Math.Min(PageSize, Nvm.Size - offset);
                            Nvm.EraseSector(offset, remaining);
                        }
                    }
                }, name: "ERASEALL");
        }

        private enum Registers
        {
            Ready = 0x400,
            ReadyNext = 0x408,
            Config = 0x504,
            ErasePage = 0x508,
            EraseAll = 0x50C,
        }
    }
}
