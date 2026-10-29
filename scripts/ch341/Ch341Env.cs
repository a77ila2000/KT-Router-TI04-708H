// Bounded 4KiB writer; caller validates YOUR bootdelay-only candidate first.
public static class Ti04EnvSector {
    public const int Offset = 0xE0000, SectorSize = 0x1000, PageSize = 256;
    public static string BeforeHash;
    public static string CandidateHash;
    const string Dll = "CH341DLL.DLL";
    [System.Runtime.InteropServices.DllImport(Dll, CallingConvention=System.Runtime.InteropServices.CallingConvention.StdCall)]
    [return: System.Runtime.InteropServices.MarshalAs(System.Runtime.InteropServices.UnmanagedType.Bool)]
    static extern bool CH341StreamSPI4(uint index, uint cs, uint length, [System.Runtime.InteropServices.In, System.Runtime.InteropServices.Out] byte[] buffer);
    public static string Phase = "not-started";
    public static int EraseCalls, ProgramCalls;
    public static int Status1 = -1, Status2 = -1;
    public static string VerifiedHash;
    static bool authorized;

    public static string Hash(byte[] data) {
        using (var sha=System.Security.Cryptography.SHA256.Create())
            return BitConverter.ToString(sha.ComputeHash(data)).Replace("-", "").ToLowerInvariant();
    }
    public static bool Equal(byte[] a, byte[] b) {
        if (a.Length != b.Length) return false;
        for (int i=0; i<a.Length; ++i) if (a[i] != b[i]) return false;
        return true;
    }
    public static byte[] EraseFrame(int address) {
        if (address != Offset) throw new ArgumentOutOfRangeException("only the first APPSBLENV sector may be erased");
        return new byte[] {0x20, (byte)(address>>16), (byte)(address>>8), (byte)address};
    }
    public static byte[] PageFrame(int address, byte[] page) {
        if (page == null || page.Length != PageSize || address < Offset || address > Offset+SectorSize-PageSize || (address % PageSize)!=0)
            throw new ArgumentOutOfRangeException("page outside the single authorized sector");
        byte[] frame=new byte[PageSize+4];
        frame[0]=0x02; frame[1]=(byte)(address>>16); frame[2]=(byte)(address>>8); frame[3]=(byte)address;
        Buffer.BlockCopy(page,0,frame,4,PageSize); return frame;
    }
    static void SendMutation(byte[] frame) {
        if (!authorized) throw new InvalidOperationException("full-image preflight has not passed");
        bool allowed=(frame.Length==1 && (frame[0]==0x06 || frame[0]==0x04));
        if (frame.Length==4 && frame[0]==0x20)
            allowed=Equal(frame,EraseFrame(Offset));
        if (frame.Length==PageSize+4 && frame[0]==0x02) {
            int address=(frame[1]<<16)|(frame[2]<<8)|frame[3];
            allowed=address>=Offset && address<=Offset+SectorSize-PageSize && address%PageSize==0;
        }
        if (!allowed) throw new InvalidOperationException("forbidden flash operation");
        if (!CH341StreamSPI4(0,0x80,(uint)frame.Length,frame))
            throw new InvalidOperationException("flash command transfer failed; no automatic retry");
    }
    static byte ReadStatus(byte opcode) {
        if (opcode!=0x05 && opcode!=0x35) throw new ArgumentOutOfRangeException("status opcode");
        // One CS transaction, automatic release; no status-register write is implemented.
        byte[] frame=new byte[] {opcode,0xFF};
        if (!CH341StreamSPI4(0,0x80,2,frame)) throw new InvalidOperationException("status read failed");
        return frame[1];
    }
    static void CheckReadyAndProtection() {
        Status1=ReadStatus(0x05); Status2=ReadStatus(0x35);
        if ((Status1&3)!=0) throw new InvalidOperationException("chip is busy or write-enable is unexpectedly set");
        if ((Status1&0x7C)!=0 || (Status2&0x40)!=0)
            throw new InvalidOperationException("protection configuration is nonzero; refusing to unprotect or alter it");
    }
    static void WriteEnable() {
        SendMutation(new byte[] {0x06});
        if ((ReadStatus(0x05)&3)!=2) throw new InvalidOperationException("WEL was not set while idle");
    }
    static void WaitReady(int timeoutMs) {
        var timer=System.Diagnostics.Stopwatch.StartNew();
        while (true) {
            byte status=ReadStatus(0x05);
            if ((status&1)==0) {
                if ((status&2)!=0) throw new InvalidOperationException("write command did not clear WEL");
                return;
            }
            if (timer.ElapsedMilliseconds>=timeoutMs) throw new TimeoutException("flash busy timeout; no retry or power cycle");
            System.Threading.Thread.Sleep(2);
        }
    }
    static byte[] ReadAll(string label) {
        byte[] data=new byte[Ti04NorReadOnly.Size];
        for (int offset=0; offset<data.Length; offset+=Ti04NorReadOnly.ChunkSize) {
            byte[] part=Ti04NorReadOnly.ReadBlock(offset,Ti04NorReadOnly.ChunkSize);
            Buffer.BlockCopy(part,0,data,offset,part.Length);
            if ((offset+part.Length)%524288==0) Console.WriteLine(label+": "+(offset+part.Length)+"/2097152 bytes");
        }
        return data;
    }
    static void SaveNew(string path, byte[] data) {
        using (var file=new System.IO.FileStream(path,System.IO.FileMode.CreateNew,System.IO.FileAccess.Write,System.IO.FileShare.None)) {
            file.Write(data,0,data.Length); file.Flush(true);
        }
    }
    static void CheckOutsideSector(byte[] before, byte[] candidate) {
        if (before.Length!=Ti04NorReadOnly.Size || candidate.Length!=before.Length) throw new InvalidOperationException("image size mismatch");
        for (int i=0; i<before.Length; ++i)
            if ((i<Offset || i>=Offset+SectorSize) && before[i]!=candidate[i])
                throw new InvalidOperationException("candidate changes bytes outside the allowed sector");
    }
    public static void Apply(byte[] expectedBefore, byte[] candidate, string directory) {
        if (Hash(expectedBefore)!=BeforeHash || Hash(candidate)!=CandidateHash) throw new InvalidOperationException("unexpected preimage or candidate");
        CheckOutsideSector(expectedBefore,candidate);
        Phase="preflight-read";
        try {
            Ti04NorReadOnly.Open();
            if (Ti04NorReadOnly.Jedec()!="C84015") throw new InvalidOperationException("unexpected JEDEC");
            CheckReadyAndProtection();
            byte[] before=ReadAll("Pre-write read");
            SaveNew(System.IO.Path.Combine(directory,"before-native.bin"),before);
            if (Equal(before,candidate)) { VerifiedHash=Hash(before); Phase="candidate-already-present-no-write"; return; }
            if (!Equal(before,expectedBefore)) throw new InvalidOperationException("live image differs from YOUR verified source; nothing erased");
            SaveNew(System.IO.Path.Combine(directory,"rollback-sector-at-e0000.bin"),Subarray(before,Offset,SectorSize));
            SaveNew(System.IO.Path.Combine(directory,"candidate-sector-at-e0000.bin"),Subarray(candidate,Offset,SectorSize));
            if (Ti04NorReadOnly.Jedec()!="C84015") throw new InvalidOperationException("JEDEC changed before write");
            CheckReadyAndProtection();
            authorized=true;
            Phase="erasing-e0000-4KiB";
            WriteEnable(); EraseCalls++; SendMutation(EraseFrame(Offset)); WaitReady(10000);
            byte[] erased=new byte[SectorSize];
            for (int off=0; off<SectorSize; off+=Ti04NorReadOnly.ChunkSize)
                Buffer.BlockCopy(Ti04NorReadOnly.ReadBlock(Offset+off,Ti04NorReadOnly.ChunkSize),0,erased,off,Ti04NorReadOnly.ChunkSize);
            if (!Ti04NorReadOnly.All(erased,0xFF)) throw new InvalidOperationException("sector erase verification failed; no page program attempted");
            Console.WriteLine("Only sector 0xE0000 erased and verified FF.");
            Phase="programming-e0000-4KiB";
            for (int page=0; page<SectorSize/PageSize; ++page) {
                int address=Offset+page*PageSize;
                byte[] data=Subarray(candidate,address,PageSize);
                WriteEnable(); ProgramCalls++; SendMutation(PageFrame(address,data)); WaitReady(2000);
                if (!Equal(Ti04NorReadOnly.ReadBlock(address,PageSize),data))
                    throw new InvalidOperationException("page readback mismatch at "+address.ToString("X6")+"; no automatic retry");
            }
            SendMutation(new byte[] {0x04}); CheckReadyAndProtection(); authorized=false;
            Phase="full-image-verification";
            byte[] after=ReadAll("Post-write read");
            SaveNew(System.IO.Path.Combine(directory,"after-native.bin"),after);
            if (!Equal(after,candidate)) throw new InvalidOperationException("entire post-write image differs; keep router power off");
            CheckOutsideSector(before,after);
            VerifiedHash=Hash(after); Phase="verified-full-2MiB";
            Console.WriteLine("PASS: all 2097152 readback bytes equal candidate; outside sector unchanged.");
        } finally {
            authorized=false;
            Ti04NorReadOnly.Close();
        }
    }
    static byte[] Subarray(byte[] data,int offset,int count) {
        byte[] part=new byte[count]; Buffer.BlockCopy(data,offset,part,0,count); return part;
    }
    public static void SelfTest() {
        byte[] expectedErase={0x20,0x0E,0,0};
        if (!Equal(EraseFrame(Offset),expectedErase)) throw new Exception("erase address encoding");
        for (int i=0;i<16;++i) {
            byte[] page=new byte[PageSize]; for(int j=0;j<page.Length;++j) page[j]=(byte)(i+j);
            int address=Offset+i*PageSize; byte[] frame=PageFrame(address,page);
            if (frame.Length!=260 || frame[0]!=2 || ((frame[1]<<16)|(frame[2]<<8)|frame[3])!=address || !Equal(Subarray(frame,4,256),page))
                throw new Exception("page framing or payload");
        }
        foreach(int address in new int[] {0,Offset-1,Offset+1,Offset+SectorSize}) {
            bool rejected=false; try { EraseFrame(address); } catch(ArgumentOutOfRangeException) { rejected=true; }
            if(!rejected) throw new Exception("erase boundary accepted");
            rejected=false; try { PageFrame(address,new byte[256]); } catch(ArgumentOutOfRangeException) { rejected=true; }
            if(!rejected) throw new Exception("page boundary accepted");
        }
        foreach(int size in new int[] {0,255,257,4096}) {
            bool rejected=false; try { PageFrame(Offset,new byte[size]); } catch(ArgumentOutOfRangeException) { rejected=true; }
            if(!rejected) throw new Exception("incorrect page length accepted");
        }
        byte[] a=new byte[Ti04NorReadOnly.Size],b=new byte[Ti04NorReadOnly.Size];
        b[Offset]=1; b[Offset+SectorSize-1]=2; CheckOutsideSector(a,b);
        b[Offset+SectorSize]=3;
        bool outsideRejected=false; try { CheckOutsideSector(a,b); } catch(InvalidOperationException) { outsideRejected=true; }
        if(!outsideRejected) throw new Exception("outside-sector change accepted");
        bool unarmedRejected=false; try { SendMutation(new byte[] {0x06}); } catch(InvalidOperationException) { unarmedRejected=true; }
        if(!unarmedRejected) throw new Exception("unarmed mutation accepted");
        Console.WriteLine("PASS: one-sector bounds, all 16 page frames, payload preservation, outside-sector rejection and no unarmed write; no device access.");
    }
}