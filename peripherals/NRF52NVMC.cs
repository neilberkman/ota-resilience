// Copyright (c) 2026
// SPDX-License-Identifier: Apache-2.0
//
// nRF52840 NVMC (Non-Volatile Memory Controller) with word-level write tracking.
// Handles CONFIG (write/erase enable), ERASEPAGE, READY.
//
// Write tracking: on each WEN(1)->REN(0) transition, diffs the MappedMemory
// against a snapshot taken when WEN was set to count individual 4-byte word
// writes.  This handles the nRFX driver writing multiple words under a single
// WEN window (e.g. 16-byte magic = 4 word writes).
//
// Performance: set DiffLookahead to int.MaxValue to always diff (required
// for accurate write counts — calibration and sweep must use the same mode).
// With a smaller DiffLookahead, diffing only starts when TotalWordWrites is
// within DiffLookahead of FaultAtWordWrite; outside that window each WEN->REN
// counts as 1 write.  Only use limited DiffLookahead when you know every
// WEN->REN writes exactly 1 word.
//
// Fault injection: when TotalWordWrites reaches FaultAtWordWrite mid-window,
// FaultFlashSnapshot is built with only the words up to the fault applied.

using System;
using System.Collections.Generic;
using System.Text;

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

        // Write tracking: count of individual 4-byte word writes to flash.
        public ulong TotalWordWrites { get; set; }

        // Arm fault injection: when TotalWordWrites reaches this value,
        // set FaultFired=true.  Use ulong.MaxValue to disable.
        public ulong FaultAtWordWrite { get; set; } = ulong.MaxValue;

        // True if the fault was triggered during this run.
        public bool FaultFired { get; set; }

        // Snapshot of MappedMemory flash taken at the exact fault word.
        // If the fault falls mid-window, only words up to the fault are
        // applied; later words keep their pre-WEN values.
        public byte[] FaultFlashSnapshot { get; set; }

        // How many WEN->REN transitions ahead of FaultAtWordWrite to start
        // doing full-flash diffs.  Outside this window, each transition
        // counts as 1 write (fast path).  Set to int.MaxValue to always
        // diff (needed for accurate calibration).
        public int DiffLookahead { get; set; } = 32;

        // Reference to MappedMemory for erase operations when Nvm is null.
        public MappedMemory Flash { get; set; }

        // Base address of the Flash MappedMemory on the system bus.
        public long FlashBaseAddress { get; set; } = 0x00000000;

        // Size of the Flash MappedMemory.
        public long FlashSize { get; set; } = 0;

        // Erase fill value for MappedMemory erase operations.
        public byte EraseFill { get; set; } = 0xFF;

        // Write trace: when enabled, records (writeIndex, flashOffset, value)
        // for each word write during diff mode.  Used by calibration to build
        // a heuristic priority map AND to enable trace-replay mode where flash
        // state at any fault point can be reconstructed without re-emulation.
        public bool WriteTraceEnabled { get; set; }

        // Number of trace entries recorded.
        public int WriteTraceCount => writeTrace.Count;

        // Serialize the trace as "writeIndex:flashOffset:value\n" lines.
        // Called from Python/.resc to export after calibration.
        public string WriteTraceToString()
        {
            var sb = new StringBuilder(writeTrace.Count * 24);
            foreach(var entry in writeTrace)
            {
                sb.Append(entry.Item1);
                sb.Append(':');
                sb.Append(entry.Item2);
                sb.Append(':');
                sb.Append(entry.Item3);
                sb.Append('\n');
            }
            return sb.ToString();
        }

        // Clear the trace (call before calibration run).
        public void WriteTraceClear()
        {
            writeTrace.Clear();
        }

        private uint configValue = 0;

        // Snapshot taken when CONFIG transitions to WEN, used for diffing.
        // Only allocated when in the diff-lookahead window.
        private byte[] wenSnapshot;

        // Accumulated write trace entries: (writeIndex, flashOffset, value).
        private readonly List<Tuple<ulong, int, uint>> writeTrace = new List<Tuple<ulong, int, uint>>();

        private void DefineRegisters()
        {
            // READY at 0x400 — always ready (instant operations).
            Registers.Ready.Define(this, 1);

            // READYNEXT at 0x408 — always ready.
            Registers.ReadyNext.Define(this, 1);

            // CONFIG at 0x504 — write enable mode.
            // Values: 0=REN (read-only), 1=WEN (write), 2=EEN (erase).
            Registers.Config.Define(this)
                .WithValueField(0, 2, writeCallback: (_, val) =>
                {
                    var oldConfig = configValue;
                    configValue = (uint)val;

                    if(Flash == null || FlashSize <= 0)
                    {
                        // No MappedMemory — fall back to simple counting.
                        if(oldConfig == 1 && val == 0)
                        {
                            TotalWordWrites++;
                            if(TotalWordWrites == FaultAtWordWrite && !FaultFired)
                            {
                                FaultFired = true;
                            }
                        }
                        return;
                    }

                    // Are we close enough to the fault target to need
                    // word-level precision?
                    // DiffLookahead == int.MaxValue forces always-diff mode
                    // (used during calibration to get accurate word counts).
                    bool needDiff = !FaultFired
                        && (DiffLookahead == int.MaxValue
                            || (FaultAtWordWrite != ulong.MaxValue
                                && TotalWordWrites + (ulong)DiffLookahead >= FaultAtWordWrite));

                    // Entering WEN: snapshot flash if we need word-level diff.
                    if(val == 1 && oldConfig != 1)
                    {
                        if(needDiff)
                        {
                            wenSnapshot = Flash.ReadBytes(0, checked((int)FlashSize));
                        }
                        else
                        {
                            wenSnapshot = null;
                        }
                    }

                    // Exiting WEN → REN.
                    if(oldConfig == 1 && val == 0)
                    {
                        if(wenSnapshot != null && !FaultFired)
                        {
                            // Word-level diff mode: count each changed 4-byte word.
                            var current = Flash.ReadBytes(0, checked((int)FlashSize));
                            int len = checked((int)FlashSize);

                            for(int off = 0; off <= len - 4; off += 4)
                            {
                                bool changed = current[off]     != wenSnapshot[off]
                                            || current[off + 1] != wenSnapshot[off + 1]
                                            || current[off + 2] != wenSnapshot[off + 2]
                                            || current[off + 3] != wenSnapshot[off + 3];
                                if(!changed)
                                {
                                    continue;
                                }

                                TotalWordWrites++;
                                if(WriteTraceEnabled)
                                {
                                    uint val32 = (uint)(current[off]
                                        | (current[off + 1] << 8)
                                        | (current[off + 2] << 16)
                                        | (current[off + 3] << 24));
                                    writeTrace.Add(Tuple.Create(TotalWordWrites, off, val32));
                                }

                                if(TotalWordWrites == FaultAtWordWrite)
                                {
                                    FaultFired = true;

                                    // Build partial snapshot: pre-WEN state
                                    // with only words up to this offset applied.
                                    var snap = new byte[len];
                                    Array.Copy(wenSnapshot, snap, len);
                                    for(int j = 0; j <= off; j += 4)
                                    {
                                        if(j > len - 4) break;
                                        if(current[j]     != wenSnapshot[j]
                                        || current[j + 1] != wenSnapshot[j + 1]
                                        || current[j + 2] != wenSnapshot[j + 2]
                                        || current[j + 3] != wenSnapshot[j + 3])
                                        {
                                            snap[j]     = current[j];
                                            snap[j + 1] = current[j + 1];
                                            snap[j + 2] = current[j + 2];
                                            snap[j + 3] = current[j + 3];
                                        }
                                    }
                                    FaultFlashSnapshot = snap;
                                    break; // Stop counting further words.
                                }
                            }
                        }
                        else
                        {
                            // Fast path: assume 1 word write per WEN->REN.
                            TotalWordWrites++;

                            if(TotalWordWrites == FaultAtWordWrite && !FaultFired)
                            {
                                FaultFired = true;
                                FaultFlashSnapshot = Flash.ReadBytes(0, checked((int)FlashSize));
                            }
                        }

                        wenSnapshot = null;
                    }
                }, valueProviderCallback: _ => configValue, name: "WEN");

            // ERASEPAGE at 0x508 — write page address to erase.
            Registers.ErasePage.Define(this)
                .WithValueField(0, 32, writeCallback: (_, val) =>
                {
                    if(configValue == 2)
                    {
                        var pageAddr = (long)val;

                        if(Nvm != null)
                        {
                            var offset = pageAddr - NvmBaseAddress;
                            if(offset >= 0 && offset + PageSize <= Nvm.Size)
                            {
                                Nvm.EraseSector(offset, PageSize);
                            }
                        }
                        else if(Flash != null)
                        {
                            var offset = pageAddr - FlashBaseAddress;
                            if(offset >= 0 && offset + PageSize <= FlashSize)
                            {
                                var fillData = new byte[PageSize];
                                for(int i = 0; i < PageSize; i++)
                                {
                                    fillData[i] = EraseFill;
                                }
                                Flash.WriteBytes(offset, fillData);
                            }
                        }
                    }
                }, name: "ERASEPAGE");

            // ERASEALL at 0x50C.
            Registers.EraseAll.Define(this)
                .WithValueField(0, 1, writeCallback: (_, val) =>
                {
                    if(val == 1 && configValue == 2)
                    {
                        if(Nvm != null)
                        {
                            for(long offset = 0; offset < Nvm.Size; offset += PageSize)
                            {
                                var remaining = (int)Math.Min(PageSize, Nvm.Size - offset);
                                Nvm.EraseSector(offset, remaining);
                            }
                        }
                        else if(Flash != null)
                        {
                            var fillData = new byte[PageSize];
                            for(int i = 0; i < PageSize; i++)
                            {
                                fillData[i] = EraseFill;
                            }
                            for(long offset = 0; offset < FlashSize; offset += PageSize)
                            {
                                var remaining = (int)Math.Min(PageSize, FlashSize - offset);
                                if(remaining < PageSize)
                                {
                                    fillData = new byte[remaining];
                                    for(int i = 0; i < remaining; i++)
                                    {
                                        fillData[i] = EraseFill;
                                    }
                                }
                                Flash.WriteBytes(offset, fillData);
                            }
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
