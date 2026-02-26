// Copyright (c) 2026
// SPDX-License-Identifier: Apache-2.0
//
// nRF52840 NVMC (Non-Volatile Memory Controller) with word-level write tracking
// and page-erase fault injection.
// Handles CONFIG (write/erase enable), ERASEPAGE, READY.
//
// Write tracking: on each WEN(1)->REN(0) transition, diffs the MappedMemory
// against a snapshot taken when WEN was set to count individual 4-byte word
// writes.  This handles the nRFX driver writing multiple words under a single
// WEN window (e.g. 16-byte magic = 4 word writes).
//
// Erase tracking: each ERASEPAGE register write (while CONFIG=EEN) increments
// TotalPageErases.  Fault injection at the Nth erase produces a partial erase
// (first half of the page erased to 0xFF, second half untouched) to simulate
// power loss mid-erase.
//
// Performance: set DiffLookahead to int.MaxValue to always diff (required
// for accurate write counts — calibration and sweep must use the same mode).
// With a smaller DiffLookahead, diffing only starts when TotalWordWrites is
// within DiffLookahead of FaultAtWordWrite; outside that window each WEN->REN
// counts as 1 write.  Only use limited DiffLookahead when you know every
// WEN->REN writes exactly 1 word.
//
// Fault injection (writes): when TotalWordWrites reaches FaultAtWordWrite
// mid-window, FaultFlashSnapshot is built with only the words up to the fault
// applied.
//
// Fault injection (erases): when TotalPageErases reaches FaultAtPageErase,
// EraseFaultFired is set and the page is only half-erased.  The
// FaultFlashSnapshot captures flash state after the partial erase.

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

        // --- Page erase tracking ---

        // Count of individual page erase operations.
        public ulong TotalPageErases { get; set; }

        // Arm erase fault injection: when TotalPageErases reaches this
        // value, the erase is left incomplete.  Use ulong.MaxValue to
        // disable.
        public ulong FaultAtPageErase { get; set; } = ulong.MaxValue;

        // True if the erase fault was triggered during this run.
        public bool EraseFaultFired { get; set; }

        // Erase trace: when enabled, records (eraseIndex, flashOffset, writesAtThisPoint)
        // for each page erase.  Used by calibration alongside write trace.
        // writesAtThisPoint = TotalWordWrites at the moment of the erase,
        // enabling correct interleaving with the write trace during replay.
        public bool EraseTraceEnabled { get; set; }

        // Number of erase trace entries recorded.
        public int EraseTraceCount => eraseTrace.Count;

        // Serialize the erase trace as "eraseIndex:flashOffset:writesAtThisPoint\n" lines.
        public string EraseTraceToString()
        {
            var sb = new StringBuilder(eraseTrace.Count * 24);
            foreach(var entry in eraseTrace)
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

        // Clear the erase trace (call before calibration run).
        public void EraseTraceClear()
        {
            eraseTrace.Clear();
        }

        // --- Write tracking config ---

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

        // --- Bit-corruption fault injection ---

        // Fault mode for write faults:
        //   0 = power_loss (default): faulted write is blocked entirely.
        //   1 = bit_corruption: faulted write partially programs — some bits
        //       flip 1→0 as intended, others stay at 1.  Models NOR flash
        //       physics where programming = selective 1→0, interrupted = partial.
        public int WriteFaultMode { get; set; } = 0;

        // Seed for deterministic bit corruption (0 = use write index as seed).
        public uint CorruptionSeed { get; set; } = 0;

        // True if any fault (write or erase) has fired.  After a fault,
        // both writes and erases are suppressed — power is dead.
        public bool AnyFaultFired => FaultFired || EraseFaultFired;

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

        // Accumulated erase trace entries: (eraseIndex, flashOffset, writesAtThisPoint).
        private readonly List<Tuple<ulong, long, ulong>> eraseTrace = new List<Tuple<ulong, long, ulong>>();

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
                        if(oldConfig == 1 && val == 0 && !AnyFaultFired)
                        {
                            TotalWordWrites++;
                            if(TotalWordWrites == FaultAtWordWrite)
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
                    bool needDiff = !AnyFaultFired
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
                        if(wenSnapshot != null && !AnyFaultFired)
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
                                    // with words before the fault fully applied.
                                    var snap = new byte[len];
                                    Array.Copy(wenSnapshot, snap, len);
                                    for(int j = 0; j < off; j += 4)
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

                                    // Handle the faulted word itself.
                                    if(WriteFaultMode == 1 && off <= len - 4)
                                    {
                                        // Bit-corruption mode: NOR flash programs
                                        // bits 1→0.  Interrupted = SOME bits flipped.
                                        // Corrupted = old AND (old OR partial_new).
                                        // Simplification: randomly keep ~half the
                                        // intended bit changes.
                                        uint oldWord = (uint)(wenSnapshot[off]
                                            | (wenSnapshot[off + 1] << 8)
                                            | (wenSnapshot[off + 2] << 16)
                                            | (wenSnapshot[off + 3] << 24));
                                        uint newWord = (uint)(current[off]
                                            | (current[off + 1] << 8)
                                            | (current[off + 2] << 16)
                                            | (current[off + 3] << 24));

                                        // Bits that need to change: 1→0 transitions.
                                        uint bitsToFlip = oldWord & ~newWord;
                                        // Deterministic mask from seed + write index.
                                        uint seed = CorruptionSeed != 0
                                            ? CorruptionSeed
                                            : (uint)TotalWordWrites;
                                        // Simple LCG for deterministic bit selection.
                                        seed = seed * 1103515245 + 12345;
                                        uint mask = seed;
                                        // Only flip ~half the bits (those where mask bit = 1).
                                        uint actuallyFlipped = bitsToFlip & mask;
                                        uint corruptedWord = oldWord & ~actuallyFlipped;

                                        snap[off]     = (byte)(corruptedWord);
                                        snap[off + 1] = (byte)(corruptedWord >> 8);
                                        snap[off + 2] = (byte)(corruptedWord >> 16);
                                        snap[off + 3] = (byte)(corruptedWord >> 24);
                                    }
                                    else if(off <= len - 4)
                                    {
                                        // Power-loss mode (default): faulted word
                                        // is NOT applied — keeps pre-WEN value.
                                        // (snap already has wenSnapshot at this offset)
                                    }

                                    FaultFlashSnapshot = snap;
                                    break; // Stop counting further words.
                                }
                            }
                        }
                        else if(!AnyFaultFired)
                        {
                            // Fast path: assume 1 word write per WEN->REN.
                            TotalWordWrites++;

                            if(TotalWordWrites == FaultAtWordWrite)
                            {
                                FaultFired = true;
                                FaultFlashSnapshot = Flash.ReadBytes(0, checked((int)FlashSize));
                            }
                        }

                        wenSnapshot = null;
                    }
                }, valueProviderCallback: _ => configValue, name: "WEN");

            // ERASEPAGE at 0x508 — write page address to erase.
            // Tracks TotalPageErases and supports fault injection at the
            // Nth erase.  On fault: partial erase (first half 0xFF, second
            // half untouched) simulating power loss mid-erase.
            Registers.ErasePage.Define(this)
                .WithValueField(0, 32, writeCallback: (_, val) =>
                {
                    if(configValue != 2)
                    {
                        return;
                    }

                    var pageAddr = (long)val;

                    if(AnyFaultFired)
                    {
                        // A fault (write or erase) already fired — power is
                        // dead, suppress all further operations.
                        return;
                    }

                    if(Nvm != null)
                    {
                        var offset = pageAddr - NvmBaseAddress;
                        if(offset >= 0 && offset + PageSize <= Nvm.Size)
                        {
                            TotalPageErases++;
                            if(EraseTraceEnabled)
                            {
                                eraseTrace.Add(Tuple.Create(TotalPageErases, offset, TotalWordWrites));
                            }

                            if(TotalPageErases == FaultAtPageErase)
                            {
                                // Partial erase: only first half of page.
                                EraseFaultFired = true;
                                int halfPage = PageSize / 2;
                                Nvm.EraseSector(offset, halfPage);
                                // Note: NvMemory doesn't support FaultFlashSnapshot;
                                // the NVM path is the slow per-write-tracking path.
                            }
                            else
                            {
                                Nvm.EraseSector(offset, PageSize);
                            }
                        }
                    }
                    else if(Flash != null)
                    {
                        var offset = pageAddr - FlashBaseAddress;
                        if(offset >= 0 && offset + PageSize <= FlashSize)
                        {
                            TotalPageErases++;
                            if(EraseTraceEnabled)
                            {
                                eraseTrace.Add(Tuple.Create(TotalPageErases, offset, TotalWordWrites));
                            }

                            if(TotalPageErases == FaultAtPageErase)
                            {
                                // Fault: partial erase — first half of the
                                // page is erased to 0xFF, second half is
                                // untouched.  Simulates power loss mid-erase.
                                EraseFaultFired = true;
                                int halfPage = PageSize / 2;
                                var fillData = new byte[halfPage];
                                for(int i = 0; i < halfPage; i++)
                                {
                                    fillData[i] = EraseFill;
                                }
                                Flash.WriteBytes(offset, fillData);

                                // Capture flash state at the fault moment.
                                FaultFlashSnapshot = Flash.ReadBytes(0, checked((int)FlashSize));
                            }
                            else
                            {
                                // Normal full page erase.
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
