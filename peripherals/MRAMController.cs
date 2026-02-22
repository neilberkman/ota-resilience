// Copyright (c) 2026
// SPDX-License-Identifier: Apache-2.0

using System;
using System.Threading;

using Antmicro.Renode.Core;
using Antmicro.Renode.Core.Structure.Registers;
using Antmicro.Renode.Peripherals;
using Antmicro.Renode.Peripherals.Bus;

namespace Antmicro.Renode.Peripherals.Memory
{
    // Persistent, byte-addressable MRAM model with 8-byte erase/program semantics.
    public class MRAMMemory : IMemory, IBytePeripheral, IWordPeripheral, IDoubleWordPeripheral, IQuadWordPeripheral, IKnownSize
    {
        public MRAMMemory(long size = DefaultSize, long wordSize = DefaultWordSize)
        {
            if(size <= 0 || size > int.MaxValue)
            {
                throw new ArgumentException("MRAM size must be between 1 and Int32.MaxValue");
            }

            this.size = size;
            WordSize = wordSize;
            storage = new byte[size];
        }

        public void Reset()
        {
            // Intentionally do NOT clear storage: this models non-volatile memory.
            WriteInProgress = false;
            LastFaultInjected = false;
        }

        public byte ReadByte(long offset)
        {
            if(AliasTarget != null)
            {
                return AliasTarget.ReadByte(offset);
            }
            ValidateRange(offset, 1);
            return storage[offset];
        }

        public ushort ReadWord(long offset)
        {
            if(AliasTarget != null)
            {
                return AliasTarget.ReadWord(offset);
            }
            ValidateRange(offset, 2);
            return (ushort)(ReadByte(offset)
                | (ReadByte(offset + 1) << 8));
        }

        public uint ReadDoubleWord(long offset)
        {
            if(AliasTarget != null)
            {
                return AliasTarget.ReadDoubleWord(offset);
            }
            ValidateRange(offset, 4);
            return (uint)(ReadByte(offset)
                | (ReadByte(offset + 1) << 8)
                | (ReadByte(offset + 2) << 16)
                | (ReadByte(offset + 3) << 24));
        }

        public ulong ReadQuadWord(long offset)
        {
            if(AliasTarget != null)
            {
                return AliasTarget.ReadQuadWord(offset);
            }
            ValidateRange(offset, 8);
            return ReadDoubleWord(offset)
                | ((ulong)ReadDoubleWord(offset + 4) << 32);
        }

        public void WriteByte(long offset, byte value)
        {
            WriteBytesInternal(offset, new[] { value });
        }

        public void WriteWord(long offset, ushort value)
        {
            WriteBytesInternal(offset, new[]
            {
                (byte)(value & 0xFF),
                (byte)((value >> 8) & 0xFF),
            });
        }

        public void WriteDoubleWord(long offset, uint value)
        {
            WriteBytesInternal(offset, new[]
            {
                (byte)(value & 0xFF),
                (byte)((value >> 8) & 0xFF),
                (byte)((value >> 16) & 0xFF),
                (byte)((value >> 24) & 0xFF),
            });
        }

        public void WriteQuadWord(long offset, ulong value)
        {
            WriteBytesInternal(offset, new[]
            {
                (byte)(value & 0xFF),
                (byte)((value >> 8) & 0xFF),
                (byte)((value >> 16) & 0xFF),
                (byte)((value >> 24) & 0xFF),
                (byte)((value >> 32) & 0xFF),
                (byte)((value >> 40) & 0xFF),
                (byte)((value >> 48) & 0xFF),
                (byte)((value >> 56) & 0xFF),
            });
        }

        public byte[] ReadBytes(long offset, int count, IPeripheral context)
        {
            if(AliasTarget != null)
            {
                return AliasTarget.ReadBytes(offset, count, context);
            }

            ValidateRange(offset, count);
            var result = new byte[count];
            Array.Copy(storage, offset, result, 0, count);
            return result;
        }

        public void WriteBytes(long offset, byte[] array, int startingIndex, int count, IPeripheral context)
        {
            if(array == null)
            {
                throw new ArgumentNullException(nameof(array));
            }

            if(startingIndex < 0 || count < 0 || startingIndex + count > array.Length)
            {
                throw new ArgumentOutOfRangeException($"Invalid write window start={startingIndex}, count={count}, arrayLength={array.Length}");
            }

            var data = new byte[count];
            Array.Copy(array, startingIndex, data, 0, count);
            WriteBytesInternal(offset, data);
        }

        public void InjectFault(long address, long length, byte pattern = 0x00)
        {
            if(AliasTarget != null)
            {
                AliasTarget.InjectFault(address, length, pattern);
                return;
            }

            if(length <= 0)
            {
                return;
            }

            ValidateRange(address, length);
            for(var i = 0L; i < length; i++)
            {
                storage[address + i] = pattern;
            }
            LastFaultInjected = true;
            LastFaultPattern = pattern;
        }

        public void InjectPartialWrite(long address)
        {
            if(AliasTarget != null)
            {
                AliasTarget.InjectPartialWrite(address);
                return;
            }

            var aligned = AlignDown(address, WordSize);
            ValidateRange(aligned, WordSize);

            var half = WordSize / 2;
            for(var i = half; i < WordSize; i++)
            {
                storage[aligned + i] = 0x00;
            }

            LastFaultInjected = true;
            LastFaultPattern = 0x00;
        }

        public ulong GetWordWriteCount()
        {
            if(AliasTarget != null)
            {
                return AliasTarget.GetWordWriteCount();
            }
            return TotalWordWrites;
        }

        public bool IsWriteInProgress()
        {
            if(AliasTarget != null)
            {
                return AliasTarget.IsWriteInProgress();
            }
            return WriteInProgress;
        }

        public long Size
        {
            get { return size; }
            set
            {
                if(AliasTarget != null)
                {
                    // Aliases inherit target geometry.
                    return;
                }

                if(value <= 0)
                {
                    throw new ArgumentException("MRAM size must be > 0");
                }

                if(value > int.MaxValue)
                {
                    throw new ArgumentException("MRAM size exceeds max supported backing array size");
                }

                if(value == size)
                {
                    return;
                }

                var newStorage = new byte[value];
                var bytesToCopy = Math.Min(size, value);
                Array.Copy(storage, newStorage, bytesToCopy);
                storage = newStorage;
                size = value;
            }
        }

        public long WordSize
        {
            get { return wordSize; }
            set
            {
                if(value <= 0)
                {
                    throw new ArgumentException("WordSize must be > 0");
                }

                // Keep word boundaries power-of-two for efficient alignment logic.
                if((value & (value - 1)) != 0)
                {
                    throw new ArgumentException("WordSize must be a power-of-two");
                }

                wordSize = value;
            }
        }

        public byte EraseFill { get; set; }

        public bool EnforceWordWriteSemantics { get; set; } = true;

        public bool ReadOnly { get; set; }

        // Optional alias to expose NV_READ_OFFSET style mirrored view.
        public MRAMMemory AliasTarget { get; set; }

        public ulong FaultAtWordWrite { get; set; } = ulong.MaxValue;

        public uint WriteLatencyMicros { get; set; }

        public bool WriteInProgress { get; private set; }

        public bool LastFaultInjected { get; private set; }

        public byte LastFaultPattern { get; private set; }

        public ulong TotalWordWrites { get; private set; }

        public long LastWriteAddress { get; private set; }

        private void WriteBytesInternal(long offset, byte[] data)
        {
            if(AliasTarget != null)
            {
                if(ReadOnly)
                {
                    return;
                }

                AliasTarget.WriteBytesInternal(offset, data);
                return;
            }

            if(ReadOnly)
            {
                return;
            }

            if(data.Length == 0)
            {
                return;
            }

            ValidateRange(offset, data.Length);
            LastWriteAddress = offset;

            if(!EnforceWordWriteSemantics)
            {
                for(var i = 0; i < data.Length; i++)
                {
                    storage[offset + i] = data[i];
                }
                return;
            }

            var firstWordStart = AlignDown(offset, WordSize);
            var lastWordStart = AlignDown(offset + data.Length - 1, WordSize);

            WriteInProgress = true;
            LastFaultInjected = false;

            try
            {
                for(var wordStart = firstWordStart; wordStart <= lastWordStart; wordStart += WordSize)
                {
                    var mergedWord = new byte[WordSize];
                    for(var i = 0L; i < WordSize; i++)
                    {
                        mergedWord[i] = storage[wordStart + i];
                    }

                    for(var i = 0; i < data.Length; i++)
                    {
                        var absoluteAddress = offset + i;
                        if(absoluteAddress < wordStart || absoluteAddress >= wordStart + WordSize)
                        {
                            continue;
                        }

                        mergedWord[absoluteAddress - wordStart] = data[i];
                    }

                    EraseWord(wordStart);

                    var currentWriteIndex = TotalWordWrites + 1;
                    if(currentWriteIndex == FaultAtWordWrite)
                    {
                        var partialBytes = WordSize / 2;
                        for(var i = 0L; i < partialBytes; i++)
                        {
                            storage[wordStart + i] = mergedWord[i];
                        }

                        for(var i = partialBytes; i < WordSize; i++)
                        {
                            storage[wordStart + i] = 0x00;
                        }

                        LastFaultInjected = true;
                        LastFaultPattern = 0x00;
                        TotalWordWrites++;
                        break;
                    }

                    ProgramWord(wordStart, mergedWord);
                    TotalWordWrites++;

                    if(WriteLatencyMicros > 0)
                    {
                        var milliseconds = (int)Math.Max(1, WriteLatencyMicros / 1000);
                        Thread.Sleep(milliseconds);
                    }
                }
            }
            finally
            {
                WriteInProgress = false;
            }
        }

        private void EraseWord(long wordStart)
        {
            for(var i = 0L; i < WordSize; i++)
            {
                storage[wordStart + i] = EraseFill;
            }
        }

        private void ProgramWord(long wordStart, byte[] mergedWord)
        {
            for(var i = 0L; i < WordSize; i++)
            {
                storage[wordStart + i] = mergedWord[i];
            }
        }

        private long AlignDown(long value, long alignment)
        {
            return value & ~(alignment - 1);
        }

        private void ValidateRange(long offset, long length)
        {
            if(offset < 0 || length < 0 || (offset + length) > size)
            {
                throw new ArgumentOutOfRangeException($"MRAM access out of range: offset={offset}, length={length}, size={size}");
            }
        }

        private long size;
        private long wordSize;
        private byte[] storage;

        private const long DefaultSize = 0x80000;
        private const long DefaultWordSize = 8;
    }
}

namespace Antmicro.Renode.Peripherals
{
    // Control/register block companion for MRAMMemory.
    public class MRAMController : BasicDoubleWordPeripheral, IKnownSize
    {
        public MRAMController(Machine machine) : base(machine)
        {
            DefineRegisters();
            Reset();
        }

        public override void Reset()
        {
            base.Reset();

            efuseStrobeLen.Value = 0;
            efuseCtrl.Value = 0;
            efuseOp.Value = 0;
            mramCfg.Value = 0;
            mramOverride.Value = 0;
            mramCtrlWriteableBits = 0;
            mramUe.Value = 0;

            for(var i = 0; i < eccCounters.Length; i++)
            {
                eccCounters[i] = 0;
            }

            illegalOperation = false;

            // Intentionally do not touch Mram.Reset() here; memory persistence is critical.
        }

        public void InjectFault(long address, long length)
        {
            if(Mram == null)
            {
                illegalOperation = true;
                return;
            }

            try
            {
                Mram.InjectFault(NormalizeAddress(address), length);
            }
            catch(ArgumentOutOfRangeException)
            {
                illegalOperation = true;
            }
        }

        public void InjectPartialWrite(long address)
        {
            if(Mram == null)
            {
                illegalOperation = true;
                return;
            }

            try
            {
                Mram.InjectPartialWrite(NormalizeAddress(address));
            }
            catch(ArgumentOutOfRangeException)
            {
                illegalOperation = true;
            }
        }

        public bool WriteInProgress
        {
            get { return Mram != null && Mram.IsWriteInProgress(); }
        }

        public ulong WordWriteCount
        {
            get { return Mram == null ? 0UL : Mram.GetWordWriteCount(); }
        }

        public long Size
        {
            get { return ControllerWindowSize; }
        }

        public bool FullMode { get; set; } = true;

        public Antmicro.Renode.Peripherals.Memory.MRAMMemory Mram { get; set; }

        public long MramBaseAddress { get; set; } = 0x10000000;

        public long NvReadOffset { get; set; } = 0x80000;

        private void DefineRegisters()
        {
            Registers.MiscStatus.Define(this)
                .WithValueField(0, 32, FieldMode.Read, valueProviderCallback: _ => ComposeMiscStatus());

            Registers.EfuseStrobeLen.Define(this)
                .WithValueField(0, 32, out efuseStrobeLen, FieldMode.Read | FieldMode.Write);

            Registers.EfuseCtrl.Define(this)
                .WithValueField(0, 32, out efuseCtrl, FieldMode.Read | FieldMode.Write);

            Registers.EfuseOp.Define(this)
                .WithValueField(0, 32, out efuseOp, FieldMode.Read | FieldMode.Write);

            Registers.MramCfg.Define(this)
                .WithValueField(0, 32, out mramCfg, FieldMode.Read | FieldMode.Write);

            Registers.MramOverride.Define(this)
                .WithValueField(0, 32, out mramOverride, FieldMode.Read | FieldMode.Write);

            Registers.MramCtrl.Define(this)
                .WithValueField(0, 32,
                    valueProviderCallback: _ => ComposeMramCtrl(),
                    writeCallback: (_, value) =>
                    {
                        // Writable bits: ECC_BYPASS[0], ERASE_EN[2:1], PROG_EN[3].
                        mramCtrlWriteableBits = (uint)(value & 0xF);
                    });

            Registers.MramEc0.Define(this)
                .WithValueField(0, 32, valueProviderCallback: _ => eccCounters[0], writeCallback: (_, value) => eccCounters[0] = (uint)value);
            Registers.MramEc1.Define(this)
                .WithValueField(0, 32, valueProviderCallback: _ => eccCounters[1], writeCallback: (_, value) => eccCounters[1] = (uint)value);
            Registers.MramEc2.Define(this)
                .WithValueField(0, 32, valueProviderCallback: _ => eccCounters[2], writeCallback: (_, value) => eccCounters[2] = (uint)value);
            Registers.MramEc3.Define(this)
                .WithValueField(0, 32, valueProviderCallback: _ => eccCounters[3], writeCallback: (_, value) => eccCounters[3] = (uint)value);

            Registers.MramUe.Define(this)
                .WithValueField(0, 32, out mramUe, FieldMode.Read | FieldMode.Write);

            Registers.MramEcUeRst.Define(this)
                .WithValueField(0, 32, FieldMode.Write, writeCallback: (_, value) =>
                {
                    if(value == 0)
                    {
                        return;
                    }

                    for(var i = 0; i < eccCounters.Length; i++)
                    {
                        eccCounters[i] = 0;
                    }
                    mramUe.Value = 0;
                });
        }

        private uint ComposeMiscStatus()
        {
            // Keep ROM-useful flags set while emulating operational bits 8..11.
            var status = 0U;
            status |= (1U << 2); // TRIM_FUSED
            status |= (1U << 3); // MRAM_PROGRAMMED

            if(Mram != null && Mram.IsWriteInProgress())
            {
                status |= (1U << 9);  // PROG_ACTIVE
                status |= (1U << 10); // ERASE_ACTIVE
            }

            if(illegalOperation)
            {
                status |= (1U << 11); // ILLEGAL_OPERATION
            }

            return status;
        }

        private uint ComposeMramCtrl()
        {
            var ctrl = mramCtrlWriteableBits;

            // Model immediate readiness in the simplified timing model.
            ctrl |= (1U << 8); // RDY_FOR_ERASE
            ctrl |= (1U << 9); // RDY_FOR_PROG

            return ctrl;
        }

        private long NormalizeAddress(long address)
        {
            if(Mram == null)
            {
                return address;
            }

            if(address >= 0 && address < Mram.Size)
            {
                return address;
            }

            if(address >= MramBaseAddress && address < MramBaseAddress + Mram.Size)
            {
                return address - MramBaseAddress;
            }

            var nvReadBase = MramBaseAddress + NvReadOffset;
            if(address >= nvReadBase && address < nvReadBase + Mram.Size)
            {
                return address - nvReadBase;
            }

            throw new ArgumentOutOfRangeException($"Address 0x{address:X} is outside modeled MRAM windows");
        }

        private IValueRegisterField efuseStrobeLen;
        private IValueRegisterField efuseCtrl;
        private IValueRegisterField efuseOp;
        private IValueRegisterField mramCfg;
        private IValueRegisterField mramOverride;
        private IValueRegisterField mramUe;

        private uint mramCtrlWriteableBits;
        private readonly uint[] eccCounters = new uint[4];
        private bool illegalOperation;

        private const long ControllerWindowSize = 0x58;

        private enum Registers : long
        {
            MiscStatus = 0x00,
            EfuseStrobeLen = 0x04,
            EfuseCtrl = 0x08,
            EfuseOp = 0x0C,
            MramCfg = 0x20,
            MramOverride = 0x24,
            MramCtrl = 0x30,
            MramEc0 = 0x40,
            MramEc1 = 0x44,
            MramEc2 = 0x48,
            MramEc3 = 0x4C,
            MramUe = 0x50,
            MramEcUeRst = 0x54,
        }
    }
}
