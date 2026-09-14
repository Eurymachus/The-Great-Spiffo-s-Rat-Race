using System;
using System.IO;
using System.Collections.Generic;
using System.Runtime.InteropServices;
using System.Security.AccessControl;
using System.Security.Principal;
using System.Security.Cryptography;

// Native descriptor reads avoid PowerShell provider/Get-Acl overhead. Descriptors
// are evaluated once per unique owner/DACL, including inherited-only descriptors.
public static class StagingIsolationNative {
    [DllImport("advapi32.dll", CharSet=CharSet.Unicode)]
    static extern uint GetNamedSecurityInfo(string name, int type, uint info,
        out IntPtr owner, out IntPtr group, out IntPtr dacl, out IntPtr sacl, out IntPtr sd);
    [DllImport("advapi32.dll")] static extern uint GetSecurityDescriptorLength(IntPtr sd);
    [DllImport("kernel32.dll")] static extern IntPtr LocalFree(IntPtr p);
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    static extern Microsoft.Win32.SafeHandles.SafeFileHandle CreateFile(string path, uint access,
        uint share, IntPtr security, uint creation, uint flags, IntPtr template);
    [StructLayout(LayoutKind.Sequential)] struct FileInfo {
        public uint Attributes; public System.Runtime.InteropServices.ComTypes.FILETIME Creation, Access, Write;
        public uint Volume, SizeHigh, SizeLow, Links, IndexHigh, IndexLow;
    }
    [DllImport("kernel32.dll", SetLastError=true)] static extern bool GetFileInformationByHandle(Microsoft.Win32.SafeHandles.SafeFileHandle h, out FileInfo info);
    public sealed class Descriptor {
        public string Path, Hash, Identity, Owner, Sddl;
        public bool Exceptional;
    }
    public sealed class ScanResult {
        public List<Descriptor> Descriptors = new List<Descriptor>();
        public List<string> ExceptionalPaths = new List<string>();
        public List<string> Findings = new List<string>();
        public long Entries, NativeReads, Evaluations, ExceptionalEntries;
    }
    public static Descriptor Read(string path, bool identity) {
        if ((File.GetAttributes(path) & FileAttributes.ReparsePoint) != 0) throw new IOException("Reparse point: " + path);
        IntPtr owner, group, dacl, sacl, sd;
        uint error = GetNamedSecurityInfo(path, 1, 7, out owner, out group, out dacl, out sacl, out sd);
        if (error != 0) throw new IOException("Security read failed " + error + ": " + path);
        try {
            byte[] bytes = new byte[GetSecurityDescriptorLength(sd)]; Marshal.Copy(sd, bytes, 0, bytes.Length);
            var raw = new RawSecurityDescriptor(bytes, 0);
            string sddl = raw.GetSddlForm(AccessControlSections.Owner | AccessControlSections.Group | AccessControlSections.Access);
            string hash;
            using (var sha = SHA256.Create()) hash = BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(sddl))).Replace("-", "").ToLowerInvariant();
            bool exceptional = (raw.ControlFlags & ControlFlags.DiscretionaryAclProtected) != 0;
            if (raw.DiscretionaryAcl != null) foreach (GenericAce ace in raw.DiscretionaryAcl) if ((ace.AceFlags & AceFlags.Inherited) == 0) exceptional = true;
            string fileId = null;
            if (identity) using (var handle = CreateFile(path, 0, 7, IntPtr.Zero, 3, 0x02200000, IntPtr.Zero)) {
                FileInfo info;
                if (handle.IsInvalid || !GetFileInformationByHandle(handle, out info)) throw new IOException("Filesystem identity unavailable: " + path);
                fileId = info.Volume.ToString("x8") + ":" + info.IndexHigh.ToString("x8") + info.IndexLow.ToString("x8");
            }
            return new Descriptor { Path=path, Hash=hash, Identity=fileId, Owner=raw.Owner.Value, Sddl=sddl, Exceptional=exceptional };
        } finally { LocalFree(sd); }
    }
    public static List<string> Evaluate(Descriptor descriptor, string[] sids, bool boundary) {
        var findings = new List<string>(); var subjects = new HashSet<string>(sids);
        if (boundary ? descriptor.Owner != "S-1-5-18" && descriptor.Owner != "S-1-5-32-544" : subjects.Contains(descriptor.Owner)) findings.Add("Unsafe owner: " + descriptor.Path);
        var raw = new RawSecurityDescriptor(descriptor.Sddl);
        if (raw.DiscretionaryAcl == null) { findings.Add("Null DACL: " + descriptor.Path); return findings; }
        foreach (GenericAce entry in raw.DiscretionaryAcl) {
            var ace = entry as CommonAce;
            if (ace == null || ace.IsCallback) { findings.Add("Unsupported ACE requires review: " + descriptor.Path); continue; }
            if (ace.AceQualifier != AceQualifier.AccessAllowed) continue;
            string sid = ace.SecurityIdentifier.Value;
            // Conservatively reject Allow grants even if a Deny might override them.
            int mask = boundary ? 0x500D0040 : unchecked((int)0xF00D0067);
            bool relevant = boundary ? sid != "S-1-5-18" && sid != "S-1-5-32-544" : subjects.Contains(sid);
            if (relevant && (ace.AccessMask & mask) != 0) findings.Add("Unsafe Allow grant: " + descriptor.Path + " (" + sid + ")");
        }
        return findings;
    }
    public static List<string> EvaluateReportBoundary(Descriptor descriptor, string role) {
        if (role != "File" && role != "Directory" && role != "Ancestor") throw new ArgumentException("Unknown report boundary role");
        var findings = new List<string>();
        var raw = new RawSecurityDescriptor(descriptor.Sddl);
        if (raw.Owner == null || (raw.Owner.Value != "S-1-5-18" && raw.Owner.Value != "S-1-5-32-544")) findings.Add("Unsafe report path owner: " + descriptor.Path);
        if (raw.DiscretionaryAcl == null) { findings.Add("Null report DACL: " + descriptor.Path); return findings; }
        // DELETE on each child and FILE_DELETE_CHILD on its parent are independent
        // ways to remove the protected path. Check both at every path segment.
        int mask = 0x100D0040; // GENERIC_ALL, DELETE, WRITE_DAC, WRITE_OWNER, DELETE_CHILD
        if (role != "Ancestor") mask |= 0x40000116; // GENERIC_WRITE, data/append, EA/attribute writes
        foreach (GenericAce entry in raw.DiscretionaryAcl) {
            // Inherit-only ACEs do not grant access to this object. Any effective
            // inherited grant on the actual child is checked at that child.
            if ((entry.AceFlags & AceFlags.InheritOnly) != 0) continue;
            var ace = entry as CommonAce;
            if (ace == null || ace.IsCallback) { findings.Add("Unsupported report ACE: " + descriptor.Path); continue; }
            if (ace.AceQualifier != AceQualifier.AccessAllowed) continue;
            string sid = ace.SecurityIdentifier.Value;
            if (sid != "S-1-5-18" && sid != "S-1-5-32-544" && (ace.AccessMask & mask) != 0)
                findings.Add("Unsafe " + role + " report rights: " + descriptor.Path + " (" + sid + ")");
        }
        return findings;
    }
    public static ScanResult Scan(string[] roots, string[] sids) {
        var result = new ScanResult(); var seen = new HashSet<string>();
        var pending = new Stack<string>(roots);
        while (pending.Count > 0) {
            string path = pending.Pop(); result.Entries++;
            try {
                var descriptor = Read(path, false); result.NativeReads++;
                if (descriptor.Exceptional) { result.ExceptionalEntries++; result.ExceptionalPaths.Add(path + " | " + descriptor.Hash); }
                if (seen.Add(descriptor.Hash)) {
                    result.Descriptors.Add(descriptor); result.Evaluations++;
                    result.Findings.AddRange(Evaluate(descriptor, sids, false));
                }
                if ((File.GetAttributes(path) & FileAttributes.Directory) != 0) foreach (string child in Directory.EnumerateFileSystemEntries(path)) pending.Push(child);
            } catch (Exception error) { result.Findings.Add("Uninspected path: " + path + ": " + error.Message); }
        }
        return result;
    }
}
