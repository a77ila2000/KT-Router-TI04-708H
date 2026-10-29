// CH341 transport adapted from the hardware-tested TI04 helper.
using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
public static class Ti04NorReadOnly {
    public const int Size = 2097152;
    public const int ChunkSize = 2048; // Match AsProgrammer v2.1.2 ReadFlash25 for CH341.
    const string Dll = "CH341DLL.DLL";
    [DllImport(Dll, CallingConvention=CallingConvention.StdCall, SetLastError=true)]
    static extern IntPtr CH341OpenDevice(uint index);
    [DllImport(Dll, CallingConvention=CallingConvention.StdCall)]
    static extern void CH341CloseDevice(uint index);
    [DllImport(Dll, CallingConvention=CallingConvention.StdCall, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool CH341SetStream(uint index, uint mode);
    [DllImport(Dll, CallingConvention=CallingConvention.StdCall, SetLastError=true)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool CH341StreamSPI4(uint index, uint cs, uint length, [In, Out] byte[] buffer);
    [DllImport(Dll, CallingConvention=CallingConvention.StdCall)]
    [return: MarshalAs(UnmanagedType.Bool)]
    static extern bool CH341Set_D5_D0(uint index, uint direction, uint value);
    static bool opened;
    public static byte[] ReadFrame(int address, int count) {
        if (address < 0 || count < 1 || count > ChunkSize || address > Size - count)
            throw new ArgumentOutOfRangeException("read outside GD25Q16C / block limit");
        byte[] b = new byte[count + 4];
        b[0] = 0x03; b[1] = (byte)(address >> 16); b[2] = (byte)(address >> 8); b[3] = (byte)address;
        for (int i=4; i<b.Length; ++i) b[i] = 0xFF;
        return b;
    }
    public static void CheckFrame(byte[] b) {
        if (b == null || b.Length == 0) throw new ArgumentException("empty command");
        if (b[0] == 0x9F && b.Length == 4) {
            for (int i=1; i<4; ++i) if (b[i] != 0xFF) throw new ArgumentException("JEDEC dummy bytes");
            return;
        }
        if (b[0] == 0x03 && b.Length >= 5 && b.Length <= ChunkSize + 4) {
            int address = (b[1]<<16) | (b[2]<<8) | b[3];
            if (address > Size - (b.Length - 4)) throw new ArgumentException("read range");
            for (int i=4; i<b.Length; ++i) if (b[i] != 0xFF) throw new ArgumentException("READ dummy bytes");
            return;
        }
        throw new ArgumentException("only JEDEC 9F and READ 03 are permitted");
    }
    static void Transfer(byte[] b) {
        byte[][] parts = SplitFrame(b);
        if (!opened) throw new InvalidOperationException("device not open");
        // Match upstream SPIWrite(CS=0) followed by SPIRead(CS=1).
        // This is adapter GPIO setup, not a flash status-register write.
        if (!CH341Set_D5_D0(0, 0x29, 0))
            throw new Win32Exception(Marshal.GetLastWin32Error(), "SPI pin setup failed");
        if (!CH341StreamSPI4(0, 0, (uint)parts[0].Length, parts[0]))
            throw new Win32Exception(Marshal.GetLastWin32Error(), "SPI command transfer failed");
        if (!CH341StreamSPI4(0, 0x80, (uint)parts[1].Length, parts[1]))
            throw new Win32Exception(Marshal.GetLastWin32Error(), "SPI response transfer failed");
        Buffer.BlockCopy(parts[1], 0, b, parts[0].Length, parts[1].Length);
    }
    public static byte[][] SplitFrame(byte[] b) {
        CheckFrame(b);
        int commandLength = b[0] == 0x9F ? 1 : 4;
        byte[] command = new byte[commandLength];
        byte[] response = new byte[b.Length - commandLength];
        Buffer.BlockCopy(b, 0, command, 0, commandLength);
        for (int i=0; i<response.Length; ++i) response[i] = 0xFF;
        // A 4096-byte response failed on the connected driver; use upstream's 2048-byte chunks.
        if (response.Length > ChunkSize) throw new ArgumentOutOfRangeException("DLL transfer limit");
        return new byte[][] {command, response};
    }
    public static void Open() {
        if (opened) throw new InvalidOperationException("already open");
        IntPtr handle = CH341OpenDevice(0);
        if (handle == new IntPtr(-1)) throw new Win32Exception(Marshal.GetLastWin32Error(), "CH341 open failed");
        opened = true;
        if (!CH341SetStream(0, 0x81)) throw new Win32Exception(Marshal.GetLastWin32Error(), "CH341 SPI init failed");
    }
    public static string Jedec() {
        byte[] b = new byte[] {0x9F,0xFF,0xFF,0xFF};
        Transfer(b);
        return b[1].ToString("X2")+b[2].ToString("X2")+b[3].ToString("X2");
    }
    public static byte[] ReadBlock(int address, int count) {
        byte[] b = ReadFrame(address, count);
        Transfer(b);
        byte[] data = new byte[count];
        Buffer.BlockCopy(b, 4, data, 0, count);
        return data;
    }
    public static bool All(byte[] data, byte value) {
        foreach (byte b in data) if (b != value) return false;
        return true;
    }
    public static void Close() {
        if (!opened) return;
        try { if (!CH341Set_D5_D0(0, 0, 0)) throw new InvalidOperationException("could not release SPI pins"); }
        finally { CH341CloseDevice(0); opened = false; }
    }
}