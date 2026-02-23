//
// Copyright 2026 ota-resilience contributors
//
// Licensed under the Apache License, Version 2.0.
//

using System;
using System.Collections.Generic;

using Antmicro.Renode.Core;
using Antmicro.Renode.Core.Structure.Registers;
using Antmicro.Renode.Logging;
using Antmicro.Renode.Peripherals.Bus;
using Antmicro.Renode.Peripherals.Memory;

namespace Antmicro.Renode.Peripherals
{
    public class NVMemoryController : BasicDoubleWordPeripheral, IKnownSize
    {
        public NVMemoryController(IMachine machine) : base(machine)
        {
            DefineRegisters();
            Reset();
        }

        public override void Reset()
        {
            base.Reset();

            programEnable = true;
            eraseEnable = true;
            forceReady = false;

            faultAddress = 0;
            faultLength = (ulong)writeGranularity;
            faultPattern = 0;

            partialWriteFaultCount = 0;
            regionFaultCount = 0;
            errorCount = 0;
            lastFaultInjected = false;
            lastError = ErrorCode.None;
        }

        public void InjectPartialWrite(long address)
        {
            if(Nvm == null)
            {
                SetError(ErrorCode.NotLinked);
                return;
            }

            long normalized;
            if(!TryNormalizeAddress(address, out normalized))
            {
                return;
            }

            Nvm.InjectPartialWrite(normalized);
            partialWriteFaultCount++;
            lastFaultInjected = true;
        }

        public void EraseSector(long address)
        {
            if(Nvm == null)
            {
                SetError(ErrorCode.NotLinked);
                return;
            }

            long normalized;
            if(!TryNormalizeAddress(address, out normalized))
            {
                return;
            }

            if(!Nvm.EraseSector(normalized))
            {
                SetError(ErrorCode.InvalidConfiguration);
            }
        }

        public void InjectPartialErase(long address)
        {
            if(Nvm == null)
            {
                SetError(ErrorCode.NotLinked);
                return;
            }

            long normalized;
            if(!TryNormalizeAddress(address, out normalized))
            {
                return;
            }

            if(!Nvm.InjectPartialErase(normalized))
            {
                SetError(ErrorCode.InvalidConfiguration);
                return;
            }

            lastFaultInjected = true;
        }

        public void InjectFault(long address, long length)
        {
            if(Nvm == null)
            {
                SetError(ErrorCode.NotLinked);
                return;
            }

            if(length <= 0)
            {
                SetError(ErrorCode.InvalidLength);
                return;
            }

            long normalized;
            if(!TryNormalizeAddress(address, out normalized))
            {
                return;
            }

            if(normalized + length > GetNvmSize())
            {
                SetError(ErrorCode.AddressOutOfRange);
                return;
            }

            Nvm.InjectFault(normalized, length, faultPattern);
            regionFaultCount++;
            lastFaultInjected = true;
        }

        public bool WriteInProgress
        {
            get
            {
                if(Nvm == null)
                {
                    return false;
                }

                return Nvm.WriteInProgress;
            }
        }

        public ulong WordWriteCount
        {
            get
            {
                if(Nvm == null)
                {
                    return 0;
                }

                return Nvm.GetWordWriteCount();
            }
        }

        public List<long> GetWriteLog()
        {
            return Nvm != null ? Nvm.WriteLog : new List<long>();
        }

        public void ClearWriteLog()
        {
            Nvm?.ClearWriteLog();
        }

        public LocalNVMemory Nvm
        {
            get
            {
                return nvm;
            }
            set
            {
                nvm = value;
                ApplyNvmConfiguration();
            }
        }

        public ulong NvmBaseAddress { get; set; } = 0x10000000UL;

        public ulong NvReadOffset { get; set; } = 0x80000UL;

        public bool FullMode { get; set; }

        public int WriteGranularity
        {
            get
            {
                return Nvm != null ? Nvm.WordSize : writeGranularity;
            }
            set
            {
                if(value <= 0 || (value & (value - 1)) != 0)
                {
                    throw new ArgumentException("WriteGranularity must be a positive power of two");
                }

                writeGranularity = value;
                ApplyNvmConfiguration();
            }
        }

        public int SectorSize
        {
            get
            {
                return Nvm != null ? Nvm.SectorSize : sectorSize;
            }
            set
            {
                if(value < 0 || (value != 0 && (value & (value - 1)) != 0))
                {
                    throw new ArgumentException("SectorSize must be 0 or a positive power of two");
                }

                sectorSize = value;
                ApplyNvmConfiguration();
            }
        }

        public byte EraseValue
        {
            get
            {
                return Nvm != null ? Nvm.EraseFill : eraseValue;
            }
            set
            {
                eraseValue = value;
                ApplyNvmConfiguration();
            }
        }

        public bool EnforceEraseBeforeWrite
        {
            get
            {
                return Nvm != null ? Nvm.EnforceEraseBeforeWrite : enforceEraseBeforeWrite;
            }
            set
            {
                enforceEraseBeforeWrite = value;
                ApplyNvmConfiguration();
            }
        }

        public long Size => 0x100;

        private void DefineRegisters()
        {
            Registers.Status.Define(this)
                .WithFlag(0, FieldMode.Read, valueProviderCallback: _ => forceReady || !WriteInProgress, name: "READY")
                .WithFlag(1, FieldMode.Read, valueProviderCallback: _ => WriteInProgress, name: "WRITE_IN_PROGRESS")
                .WithFlag(2, FieldMode.Read, valueProviderCallback: _ => lastFaultInjected, name: "LAST_FAULT")
                .WithFlag(3, FieldMode.Read, valueProviderCallback: _ => programEnable, name: "PROGRAM_ENABLE")
                .WithFlag(4, FieldMode.Read, valueProviderCallback: _ => eraseEnable, name: "ERASE_ENABLE")
                .WithFlag(5, FieldMode.Read, valueProviderCallback: _ => FullMode, name: "FULL_MODE")
                .WithFlag(6, FieldMode.Read, valueProviderCallback: _ => Nvm != null, name: "NVM_LINKED")
                .WithReservedBits(7, 9)
                .WithValueField(16, 16, FieldMode.Read, valueProviderCallback: _ => (uint)lastError, name: "LAST_ERROR");

            Registers.Configuration.Define(this)
                .WithFlag(0, name: "FULL_MODE",
                    writeCallback: (_, value) => FullMode = value)
                .WithFlag(1, FieldMode.Read | FieldMode.Write, name: "ENFORCE_WORD_WRITES",
                    valueProviderCallback: _ => Nvm != null && Nvm.EnforceWordWriteSemantics,
                    writeCallback: (_, value) =>
                    {
                        if(Nvm != null)
                        {
                            Nvm.EnforceWordWriteSemantics = value;
                        }
                    })
                .WithReservedBits(2, 30);

            Registers.NvmBaseAddress.Define(this)
                .WithValueField(0, 32, name: "NVM_BASE_ADDRESS",
                    writeCallback: (_, value) => NvmBaseAddress = value);

            Registers.NvReadOffset.Define(this)
                .WithValueField(0, 32, name: "NV_READ_OFFSET",
                    writeCallback: (_, value) => NvReadOffset = value);

            Registers.Control.Define(this)
                .WithFlag(0, name: "PROGRAM_ENABLE",
                    writeCallback: (_, value) => programEnable = value)
                .WithFlag(1, name: "ERASE_ENABLE",
                    writeCallback: (_, value) => eraseEnable = value)
                .WithFlag(2, name: "FORCE_READY",
                    writeCallback: (_, value) => forceReady = value)
                .WithFlag(3, FieldMode.Write, name: "CLEAR_FAULT_LATCH",
                    writeCallback: (_, value) =>
                    {
                        if(value)
                        {
                            lastFaultInjected = false;
                        }
                    })
                .WithFlag(4, FieldMode.Write, name: "CLEAR_ERRORS",
                    writeCallback: (_, value) =>
                    {
                        if(value)
                        {
                            lastError = ErrorCode.None;
                            errorCount = 0;
                        }
                    })
                .WithFlag(5, FieldMode.Write, name: "RESET_COUNTS",
                    writeCallback: (_, value) =>
                    {
                        if(value)
                        {
                            partialWriteFaultCount = 0;
                            regionFaultCount = 0;
                        }
                    })
                .WithReservedBits(6, 26);

            Registers.FaultAddress.Define(this)
                .WithValueField(0, 32, name: "FAULT_ADDRESS",
                    writeCallback: (_, value) => faultAddress = value);

            Registers.FaultLength.Define(this)
                .WithValueField(0, 32, name: "FAULT_LENGTH",
                    writeCallback: (_, value) => faultLength = value);

            Registers.FaultPattern.Define(this)
                .WithValueField(0, 8, name: "FAULT_PATTERN",
                    writeCallback: (_, value) => faultPattern = (byte)value)
                .WithReservedBits(8, 24);

            Registers.Command.Define(this)
                .WithFlag(0, FieldMode.Write, name: "INJECT_PARTIAL_WRITE",
                    writeCallback: (_, value) =>
                    {
                        if(value)
                        {
                            InjectPartialWrite((long)faultAddress);
                        }
                    })
                .WithFlag(1, FieldMode.Write, name: "INJECT_REGION_FAULT",
                    writeCallback: (_, value) =>
                    {
                        if(value)
                        {
                            InjectFault((long)faultAddress, (long)faultLength);
                        }
                    })
                .WithReservedBits(2, 30);

            Registers.WordWriteCountLow.Define(this)
                .WithValueField(0, 32, FieldMode.Read, valueProviderCallback: _ => (uint)(WordWriteCount & 0xFFFFFFFFUL), name: "WORD_WRITE_COUNT_LO");

            Registers.WordWriteCountHigh.Define(this)
                .WithValueField(0, 32, FieldMode.Read, valueProviderCallback: _ => (uint)((WordWriteCount >> 32) & 0xFFFFFFFFUL), name: "WORD_WRITE_COUNT_HI");

            Registers.PartialWriteFaultCount.Define(this)
                .WithValueField(0, 32, FieldMode.Read, valueProviderCallback: _ => partialWriteFaultCount, name: "PARTIAL_FAULT_COUNT");

            Registers.RegionFaultCount.Define(this)
                .WithValueField(0, 32, FieldMode.Read, valueProviderCallback: _ => regionFaultCount, name: "REGION_FAULT_COUNT");

            Registers.ErrorCount.Define(this)
                .WithValueField(0, 32, FieldMode.Read, valueProviderCallback: _ => errorCount, name: "ERROR_COUNT");
        }

        private long GetNvmSize()
        {
            if(Nvm == null)
            {
                return 0;
            }

            return (long)Nvm.Size;
        }

        private bool TryNormalizeAddress(long address, out long normalized)
        {
            normalized = -1;

            var size = GetNvmSize();
            if(size <= 0)
            {
                SetError(ErrorCode.NotLinked);
                return false;
            }

            if(address >= 0 && address < size)
            {
                normalized = address;
                return true;
            }

            var directBase = (long)NvmBaseAddress;
            var directEnd = directBase + size;
            if(address >= directBase && address < directEnd)
            {
                normalized = address - directBase;
                return true;
            }

            var nvReadBase = (long)(NvmBaseAddress + NvReadOffset);
            var nvReadEnd = nvReadBase + size;
            if(address >= nvReadBase && address < nvReadEnd)
            {
                normalized = address - nvReadBase;
                return true;
            }

            if(FullMode)
            {
                var mask = size - 1;
                if((size & mask) == 0)
                {
                    normalized = address & mask;
                    return true;
                }
            }

            SetError(ErrorCode.AddressOutOfRange);
            this.Log(LogLevel.Warning, "Address normalization failed for 0x{0:X}; valid bases: 0x{1:X} and 0x{2:X}",
                address, directBase, nvReadBase);
            return false;
        }

        private void SetError(ErrorCode error)
        {
            lastError = error;
            errorCount++;
            this.Log(LogLevel.Warning, "NVM controller error: {0}", error);
        }

        private void ApplyNvmConfiguration()
        {
            if(Nvm == null)
            {
                return;
            }

            Nvm.WordSize = writeGranularity;
            Nvm.SectorSize = sectorSize;
            Nvm.EraseFill = eraseValue;
            Nvm.EnforceEraseBeforeWrite = enforceEraseBeforeWrite;
        }

        private bool programEnable;
        private bool eraseEnable;
        private bool forceReady;
        private bool lastFaultInjected;

        private uint partialWriteFaultCount;
        private uint regionFaultCount;
        private uint errorCount;

        private LocalNVMemory nvm;
        private int writeGranularity = 8;
        private int sectorSize;
        private byte eraseValue = 0xFF;
        private bool enforceEraseBeforeWrite;

        private ulong faultAddress;
        private ulong faultLength;
        private byte faultPattern;

        private ErrorCode lastError;

        private enum Registers : long
        {
            Status = 0x00,
            Configuration = 0x04,
            NvmBaseAddress = 0x08,
            NvReadOffset = 0x0C,
            Control = 0x10,
            FaultAddress = 0x14,
            FaultLength = 0x18,
            FaultPattern = 0x1C,
            Command = 0x20,
            WordWriteCountLow = 0x24,
            WordWriteCountHigh = 0x28,
            PartialWriteFaultCount = 0x2C,
            RegionFaultCount = 0x30,
            ErrorCount = 0x34,
        }

        private enum ErrorCode : ushort
        {
            None = 0,
            NotLinked = 1,
            AddressOutOfRange = 2,
            InvalidLength = 3,
            InvalidConfiguration = 4,
        }
    }

    public class NVReadOnlyAlias : IBytePeripheral, IWordPeripheral, IDoubleWordPeripheral, IQuadWordPeripheral, IMultibyteWritePeripheral, IKnownSize
    {
        public NVReadOnlyAlias(IMachine machine)
        {
            systemBus = machine.GetSystemBus(this);
        }

        public byte ReadByte(long offset)
        {
            return systemBus.ReadByte(Translate(offset));
        }

        public void WriteByte(long offset, byte value)
        {
            // Read-only alias by design: writes are intentionally dropped.
        }

        public ushort ReadWord(long offset)
        {
            return systemBus.ReadWord(Translate(offset));
        }

        public void WriteWord(long offset, ushort value)
        {
            // Read-only alias by design: writes are intentionally dropped.
        }

        public uint ReadDoubleWord(long offset)
        {
            return systemBus.ReadDoubleWord(Translate(offset));
        }

        public void WriteDoubleWord(long offset, uint value)
        {
            // Read-only alias by design: writes are intentionally dropped.
        }

        public ulong ReadQuadWord(long offset)
        {
            return systemBus.ReadQuadWord(Translate(offset));
        }

        public void WriteQuadWord(long offset, ulong value)
        {
            // Read-only alias by design: writes are intentionally dropped.
        }

        public byte[] ReadBytes(long offset, int count, IPeripheral context = null)
        {
            return systemBus.ReadBytes(Translate(offset), count, context: context);
        }

        public void WriteBytes(long offset, byte[] array, int startingIndex, int count, IPeripheral context = null)
        {
            // Read-only alias by design: writes are intentionally dropped.
        }

        public void Reset()
        {
        }

        public ulong BaseAddress { get; set; } = 0x10000000UL;

        public long Size => 0x80000;

        private ulong Translate(long offset)
        {
            return BaseAddress + checked((ulong)offset);
        }

        private readonly IBusController systemBus;
    }
}

namespace Antmicro.Renode.Peripherals.Memory
{
    // Local NVM model for Renode builds that do not yet include NVMemory upstream.
    // API and behavior are aligned with the expected upstream interface.
    public class LocalNVMemory : ArrayMemory, Antmicro.Renode.Peripherals.IPeripheral
    {
        public LocalNVMemory(ulong size = DefaultSize, int wordSize = DefaultWordSize) : base(size)
        {
            if(wordSize <= 0 || (wordSize & (wordSize - 1)) != 0)
            {
                throw new ArgumentException("WordSize must be a positive power of two");
            }

            this.wordSize = wordSize;
            ResetVolatileState();
        }

        void Antmicro.Renode.Peripherals.IPeripheral.Reset()
        {
            ResetVolatileState();
        }

        private void ResetVolatileState()
        {
            // Non-volatile behavior: preserve storage and write counts across machine reset.
            WriteInProgress = false;
            LastFaultInjected = false;
        }

        public override void WriteByte(long offset, byte value)
        {
            WriteBytesWithWordSemantics(offset, new[] { value });
        }

        public override void WriteWord(long offset, ushort value)
        {
            WriteBytesWithWordSemantics(offset, new[]
            {
                (byte)(value & 0xFF),
                (byte)((value >> 8) & 0xFF),
            });
        }

        public override void WriteDoubleWord(long offset, uint value)
        {
            WriteBytesWithWordSemantics(offset, new[]
            {
                (byte)(value & 0xFF),
                (byte)((value >> 8) & 0xFF),
                (byte)((value >> 16) & 0xFF),
                (byte)((value >> 24) & 0xFF),
            });
        }

        public override void WriteQuadWord(long offset, ulong value)
        {
            WriteBytesWithWordSemantics(offset, new[]
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

        public void InjectPartialWrite(long address)
        {
            var aligned = AlignDown(address);
            if(aligned < 0 || aligned + wordSize > Size)
            {
                this.Log(LogLevel.Error, "InjectPartialWrite at 0x{0:X} is outside memory bounds", address);
                return;
            }

            var half = wordSize / 2;
            if(EnforceEraseBeforeWrite)
            {
                for(var i = 0; i < half; i++)
                {
                    // Flash-like partial program: clear bits in the first half,
                    // leave the remainder at pre-write state.
                    array[aligned + i] = (byte)(array[aligned + i] & 0x00);
                }
            }
            else
            {
                for(var i = half; i < wordSize; i++)
                {
                    array[aligned + i] = EraseFill;
                }
            }

            LastFaultInjected = true;
            LastFaultPattern = EnforceEraseBeforeWrite ? (byte)0x00 : EraseFill;
        }

        public void InjectFault(long address, long length, byte pattern = 0x00)
        {
            if(length <= 0)
            {
                return;
            }

            if(address < 0 || address + length > Size)
            {
                this.Log(LogLevel.Error, "InjectFault at 0x{0:X} length {1} is outside memory bounds", address, length);
                return;
            }

            for(var i = 0L; i < length; i++)
            {
                array[address + i] = pattern;
            }
            LastFaultInjected = true;
            LastFaultPattern = pattern;
        }

        public bool EraseSector(long address)
        {
            long sectorStart;
            if(!TryGetSectorStart(address, out sectorStart))
            {
                return false;
            }

            for(var i = 0; i < SectorSize; i++)
            {
                array[sectorStart + i] = EraseFill;
            }

            TotalSectorErases++;
            return true;
        }

        public bool InjectPartialErase(long address)
        {
            long sectorStart;
            if(!TryGetSectorStart(address, out sectorStart))
            {
                return false;
            }

            var partialBytes = Math.Max(1, SectorSize / 2);
            for(var i = 0; i < partialBytes; i++)
            {
                array[sectorStart + i] = EraseFill;
            }

            LastFaultInjected = true;
            LastFaultPattern = EraseFill;
            TotalSectorErases++;
            return true;
        }

        public ulong GetWordWriteCount()
        {
            return TotalWordWrites;
        }

        public int WordSize
        {
            get { return wordSize; }
            set
            {
                if(value <= 0 || (value & (value - 1)) != 0)
                {
                    throw new ArgumentException("WordSize must be a positive power of two");
                }
                wordSize = value;
            }
        }

        public bool EnforceWordWriteSemantics { get; set; } = true;

        public byte EraseFill { get; set; } = 0xFF;

        public int SectorSize { get; set; }

        public bool EnforceEraseBeforeWrite { get; set; }

        public bool WriteInProgress { get; private set; }

        public bool LastFaultInjected { get; private set; }

        public bool LastWriteRejected { get; private set; }

        public ulong TotalWordWrites { get; private set; }

        public ulong TotalSectorErases { get; private set; }

        public byte LastFaultPattern { get; private set; }

        public long LastWriteAddress { get; private set; }

        public ulong FaultAtWordWrite { get; set; } = ulong.MaxValue;

        public List<long> WriteLog { get { return writeLog; } }

        public void ClearWriteLog()
        {
            writeLog.Clear();
        }

        private void WriteBytesWithWordSemantics(long offset, byte[] data)
        {
            if(data.Length == 0)
            {
                return;
            }

            LastWriteAddress = offset;

            if(!EnforceWordWriteSemantics)
            {
                for(var i = 0; i < data.Length; i++)
                {
                    base.WriteByte(offset + i, data[i]);
                }
                return;
            }

            var firstWordStart = AlignDown(offset);
            var lastWordStart = AlignDown(offset + data.Length - 1);

            WriteInProgress = true;
            LastFaultInjected = false;
            LastWriteRejected = false;

            try
            {
                for(var wordStart = firstWordStart; wordStart <= lastWordStart; wordStart += wordSize)
                {
                    var currentWord = new byte[wordSize];
                    var mergedWord = new byte[wordSize];
                    for(var i = 0; i < wordSize; i++)
                    {
                        currentWord[i] = array[wordStart + i];
                        mergedWord[i] = currentWord[i];
                    }

                    for(var i = 0; i < data.Length; i++)
                    {
                        var absoluteAddress = offset + i;
                        if(absoluteAddress < wordStart || absoluteAddress >= wordStart + wordSize)
                        {
                            continue;
                        }
                        mergedWord[absoluteAddress - wordStart] = data[i];
                    }

                    if(EnforceEraseBeforeWrite && !CanProgramWithoutErase(currentWord, mergedWord))
                    {
                        LastWriteRejected = true;
                        this.Log(LogLevel.Warning, "Rejected write at 0x{0:X}: attempted to set programmed bits without erase", wordStart);
                        continue;
                    }

                    var currentWriteIndex = TotalWordWrites + 1;
                    if(currentWriteIndex == FaultAtWordWrite)
                    {
                        var partialBytes = wordSize / 2;
                        for(var i = 0; i < partialBytes; i++)
                        {
                            if(EnforceEraseBeforeWrite)
                            {
                                array[wordStart + i] = (byte)(currentWord[i] & mergedWord[i]);
                            }
                            else
                            {
                                array[wordStart + i] = mergedWord[i];
                            }
                        }

                        if(!EnforceEraseBeforeWrite)
                        {
                            for(var i = partialBytes; i < wordSize; i++)
                            {
                                array[wordStart + i] = EraseFill;
                            }
                        }

                        LastFaultInjected = true;
                        LastFaultPattern = EraseFill;
                        TotalWordWrites++;
                        writeLog.Add(wordStart);
                        break;
                    }

                    if(EnforceEraseBeforeWrite)
                    {
                        for(var i = 0; i < wordSize; i++)
                        {
                            array[wordStart + i] = (byte)(currentWord[i] & mergedWord[i]);
                        }
                    }
                    else
                    {
                        for(var i = 0; i < wordSize; i++)
                        {
                            array[wordStart + i] = EraseFill;
                        }

                        for(var i = 0; i < wordSize; i++)
                        {
                            array[wordStart + i] = mergedWord[i];
                        }
                    }
                    TotalWordWrites++;
                    writeLog.Add(wordStart);
                }
            }
            finally
            {
                WriteInProgress = false;
            }
        }

        private long AlignDown(long value)
        {
            return value & ~((long)wordSize - 1);
        }

        private bool TryGetSectorStart(long address, out long sectorStart)
        {
            sectorStart = -1;

            if(SectorSize <= 0 || (SectorSize & (SectorSize - 1)) != 0)
            {
                this.Log(LogLevel.Error, "Sector operation requested but SectorSize is invalid ({0})", SectorSize);
                return false;
            }

            if(address < 0 || address >= Size)
            {
                this.Log(LogLevel.Error, "Sector operation at 0x{0:X} is outside memory bounds", address);
                return false;
            }

            sectorStart = address - (address % SectorSize);
            if(sectorStart < 0 || sectorStart + SectorSize > Size)
            {
                this.Log(LogLevel.Error, "Sector operation at 0x{0:X} exceeds memory bounds", address);
                return false;
            }

            return true;
        }

        private static bool CanProgramWithoutErase(byte[] currentWord, byte[] targetWord)
        {
            for(var i = 0; i < currentWord.Length; i++)
            {
                if((targetWord[i] | currentWord[i]) != currentWord[i])
                {
                    return false;
                }
            }

            return true;
        }

        private int wordSize;
        private readonly List<long> writeLog = new List<long>();

        private const ulong DefaultSize = 0x80000;
        private const int DefaultWordSize = 8;
    }
}
