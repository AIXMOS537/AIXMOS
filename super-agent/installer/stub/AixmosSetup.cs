// AIXMOS-4THEPEOPLE-Setup.exe -- native self-extracting bootstrapper (compiled with the csc.exe
// that ships in every Windows 10/11, no SDK needed). The payload zip is appended to this exe:
//
//   [ stub exe ][ payload.zip ][ 8-byte little-endian payload length ][ "AIXMOS4P" ]
//
// On launch it reads its own tail, extracts the payload straight into the install dir (default
// %LOCALAPPDATA%\AIXMOS, no admin), keeps the user's memory/ folder except memory/kit, then hands
// off to the bundled Python runtime: runtime\python.exe setup\installer.py --installed-dir <dir>
// plus any flags the user passed (--role, --tmmt-dev, --no-model, ...).
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.IO.Compression;
using System.Text;

static class AixmosSetup
{
    const string Magic = "AIXMOS4P";

    static int Main(string[] args)
    {
        try { Console.OutputEncoding = Encoding.UTF8; } catch { }
        Console.ForegroundColor = ConsoleColor.Cyan;
        Console.WriteLine("==============================================================");
        Console.WriteLine("   PROJECT AIXMOS  //  4THEPEOPLE  //  one-shot setup");
        Console.WriteLine("==============================================================");
        Console.ResetColor();

        string dest = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "AIXMOS");
        var pass = new List<string>();
        bool quiet = false;
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--dir" && i + 1 < args.Length) { dest = args[++i]; continue; }
            if (args[i] == "--quiet") quiet = true;
            pass.Add(args[i]);
        }
        dest = Path.GetFullPath(dest);

        try
        {
            string self = Process.GetCurrentProcess().MainModule.FileName;
            Console.WriteLine("[1/6] Extracting AIXMOS to " + dest);
            Extract(self, dest);
        }
        catch (Exception e)
        {
            Fail("Extraction failed: " + e.Message, quiet);
            return 1;
        }

        string py = Path.Combine(dest, "runtime", "python.exe");
        string script = Path.Combine(dest, "setup", "installer.py");
        if (!File.Exists(py) || !File.Exists(script))
        {
            Fail("Payload incomplete (runtime or setup missing).", quiet);
            return 1;
        }
        var sb = new StringBuilder();
        sb.Append('"').Append(script).Append("\" --installed-dir \"").Append(dest).Append('"');
        foreach (var a in pass) sb.Append(' ').Append(Quote(a));
        var psi = new ProcessStartInfo(py, sb.ToString()) { UseShellExecute = false, WorkingDirectory = dest };
        psi.EnvironmentVariables["PYTHONIOENCODING"] = "utf-8";
        using (var p = Process.Start(psi))
        {
            p.WaitForExit();
            return p.ExitCode;
        }
    }

    static void Extract(string self, string dest)
    {
        using (var fs = new FileStream(self, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
        {
            if (fs.Length < 16) throw new InvalidDataException("no payload");
            var tail = new byte[16];
            fs.Seek(-16, SeekOrigin.End);
            fs.Read(tail, 0, 16);
            if (Encoding.ASCII.GetString(tail, 8, 8) != Magic) throw new InvalidDataException("no AIXMOS payload attached to this exe");
            long len = BitConverter.ToInt64(tail, 0);
            long start = fs.Length - 16 - len;
            if (len <= 0 || start <= 0) throw new InvalidDataException("bad payload length");
            var slice = new SubStream(fs, start, len);
            Directory.CreateDirectory(dest);
            bool keepMemory = Directory.Exists(Path.Combine(dest, "memory"));
            string root = Path.GetFullPath(dest).TrimEnd('\\') + "\\";
            using (var zip = new ZipArchive(slice, ZipArchiveMode.Read))
            {
                int n = 0, total = zip.Entries.Count;
                foreach (var e in zip.Entries)
                {
                    string name = e.FullName.Replace('\\', '/');
                    if (keepMemory && name.StartsWith("memory/") && !name.StartsWith("memory/kit/")) continue;
                    string target = Path.GetFullPath(Path.Combine(dest, name.Replace('/', '\\')));
                    if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase)) throw new InvalidDataException("Unsafe archive path");
                    if (name.EndsWith("/")) { Directory.CreateDirectory(target); continue; }
                    Directory.CreateDirectory(Path.GetDirectoryName(target));
                    try { e.ExtractToFile(target, true); }
                    catch (IOException ex) { throw new IOException("Cannot update " + name + ". Stop AIXMOS and close paired clients before upgrading.", ex); }
                    if (++n % 200 == 0) Console.Write("    " + n + " / " + total + " files\r");
                }
                Console.WriteLine("    " + n + " files in place" + (keepMemory ? " (existing memory kept)" : "") + "        ");
            }
        }
    }

    static string Quote(string a)
    {
        if (a.Length > 0 && a.IndexOfAny(new[] { ' ', '\t', '"' }) < 0) return a;
        return "\"" + a.Replace("\"", "\\\"") + "\"";
    }

    static void Fail(string msg, bool quiet)
    {
        Console.ForegroundColor = ConsoleColor.Red;
        Console.WriteLine("SETUP FAILED: " + msg);
        Console.ResetColor();
        if (!quiet) { Console.WriteLine("Press Enter to close."); Console.ReadLine(); }
    }
}

// Read-only window over [start, start+length) of another stream, so ZipArchive can seek inside the exe.
class SubStream : Stream
{
    readonly Stream s; readonly long start, len; long pos;
    public SubStream(Stream s, long start, long len) { this.s = s; this.start = start; this.len = len; }
    public override bool CanRead { get { return true; } }
    public override bool CanSeek { get { return true; } }
    public override bool CanWrite { get { return false; } }
    public override long Length { get { return len; } }
    public override long Position { get { return pos; } set { pos = value; } }
    public override int Read(byte[] buf, int off, int count)
    {
        long left = len - pos; if (left <= 0) return 0;
        if (count > left) count = (int)left;
        s.Seek(start + pos, SeekOrigin.Begin);
        int r = s.Read(buf, off, count); pos += r; return r;
    }
    public override long Seek(long o, SeekOrigin origin)
    {
        pos = origin == SeekOrigin.Begin ? o : origin == SeekOrigin.Current ? pos + o : len + o; return pos;
    }
    public override void Flush() { }
    public override void SetLength(long v) { throw new NotSupportedException(); }
    public override void Write(byte[] b, int o, int c) { throw new NotSupportedException(); }
}
