// SPDX-License-Identifier: LGPL-3.0-only
using System;
using System.Buffers.Binary;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using Nethermind.Core;
using Nethermind.Core.BlockAccessLists;
using Nethermind.Int256;
using Nethermind.Serialization.Rlp;
using NUnit.Framework;

namespace Nethermind.Core.Test.Encoding;

[TestFixture]
public class CrystalBlockAccessListCrossClientTests
{
    private readonly record struct Item(bool IsList, int Start, int End, int Next);
    private readonly record struct CompactStorage(UInt256 Slot, UInt256 Value);
    private sealed record CompactAccount(
        Address Address,
        CompactStorage[] Storage,
        UInt256? Balance,
        ulong? Nonce,
        byte[]? Code);

    private static Item ItemAt(byte[] b, int p)
    {
        byte x = b[p];
        if (x <= 0x7f) return new(false, p, p + 1, p + 1);
        if (x <= 0xb7)
        {
            int n = x - 0x80, s = p + 1;
            return new(false, s, s + n, s + n);
        }
        if (x <= 0xbf)
        {
            int q = x - 0xb7, n = 0;
            for (int i = 0; i < q; i++) n = checked((n << 8) | b[p + 1 + i]);
            int s = p + 1 + q;
            return new(false, s, s + n, s + n);
        }
        if (x <= 0xf7)
        {
            int n = x - 0xc0, s = p + 1;
            return new(true, s, s + n, s + n);
        }
        {
            int q = x - 0xf7, n = 0;
            for (int i = 0; i < q; i++) n = checked((n << 8) | b[p + 1 + i]);
            int s = p + 1 + q;
            return new(true, s, s + n, s + n);
        }
    }

    private static List<Item> Children(byte[] b, Item list)
    {
        Assert.That(list.IsList, Is.True);
        List<Item> outp = [];
        int p = list.Start;
        while (p < list.End)
        {
            Item x = ItemAt(b, p);
            outp.Add(x);
            p = x.Next;
        }
        Assert.That(p, Is.EqualTo(list.End));
        return outp;
    }

    private static byte[] Payload(byte[] b, Item x)
    {
        Assert.That(x.IsList, Is.False);
        return b[x.Start..x.End];
    }

    private static UInt256 U256(byte[] b, Item x) => new(Payload(b, x), isBigEndian: true);

    private static ulong U64(byte[] b, Item x)
    {
        byte[] v = Payload(b, x);
        Assert.That(v.Length, Is.LessThanOrEqualTo(8));
        ulong n = 0;
        foreach (byte z in v) n = (n << 8) | z;
        return n;
    }

    private static Item? LastValueItem(byte[] b, Item list)
    {
        Item? last = null;
        foreach (Item pair in Children(b, list))
        {
            List<Item> parts = Children(b, pair);
            Assert.That(parts.Count, Is.EqualTo(2));
            last = parts[1];
        }
        return last;
    }

    private static CompactAccount[] DecodeCompact(byte[] raw)
    {
        Item root = ItemAt(raw, 0);
        Assert.That(root.IsList, Is.True);
        Assert.That(root.Next, Is.EqualTo(raw.Length));
        List<CompactAccount> accounts = [];

        foreach (Item account in Children(raw, root))
        {
            List<Item> f = Children(raw, account);
            Assert.That(f.Count, Is.EqualTo(6));
            byte[] addressBytes = Payload(raw, f[0]);
            Assert.That(addressBytes.Length, Is.EqualTo(20));
            Address address = new(addressBytes);

            List<CompactStorage> storage = [];
            foreach (Item slotEntry in Children(raw, f[1]))
            {
                List<Item> sf = Children(raw, slotEntry);
                Assert.That(sf.Count, Is.EqualTo(2));
                Item? value = LastValueItem(raw, sf[1]);
                Assert.That(value.HasValue, Is.True);
                storage.Add(new(U256(raw, sf[0]), U256(raw, value!.Value)));
            }

            // f[2] = storage reads: consequence-free for ApplyStateChanges.
            Item? balValue = LastValueItem(raw, f[3]);
            Item? nonceValue = LastValueItem(raw, f[4]);
            Item? codeValue = LastValueItem(raw, f[5]);

            accounts.Add(new(
                address,
                storage.ToArray(),
                balValue.HasValue ? U256(raw, balValue.Value) : null,
                nonceValue.HasValue ? U64(raw, nonceValue.Value) : null,
                codeValue.HasValue ? Payload(raw, codeValue.Value) : null));
        }
        return accounts.ToArray();
    }

    private static void AssertParity(ReadOnlyBlockAccessList full, CompactAccount[] compact, int record)
    {
        Assert.That(compact.Length, Is.EqualTo(full.AccountChanges.Count), $"record {record} account count");
        for (int i = 0; i < compact.Length; i++)
        {
            ReadOnlyAccountChanges f = full.AccountChanges.AsSpan()[i];
            CompactAccount c = compact[i];
            Assert.That(c.Address, Is.EqualTo(f.Address), $"record {record} account {i} address");
            Assert.That(c.Storage.Length, Is.EqualTo(f.StorageChanges.Length), $"record {record} account {i} storage count");
            for (int j = 0; j < c.Storage.Length; j++)
            {
                ReadOnlySlotChanges fs = f.StorageChanges[j];
                Assert.That(c.Storage[j].Slot, Is.EqualTo(fs.Key), $"record {record} slot {j} key");
                Assert.That(c.Storage[j].Value, Is.EqualTo(fs.Changes[^1].Value), $"record {record} slot {j} value");
            }
            if (f.BalanceChanges.Length == 0) Assert.That(c.Balance, Is.Null);
            else Assert.That(c.Balance, Is.EqualTo(f.BalanceChanges[^1].Value));
            if (f.NonceChanges.Length == 0) Assert.That(c.Nonce, Is.Null);
            else Assert.That(c.Nonce, Is.EqualTo(f.NonceChanges[^1].Value));
            if (f.CodeChanges.Length == 0) Assert.That(c.Code, Is.Null);
            else Assert.That(c.Code, Is.EqualTo(f.CodeChanges[^1].Code));
        }
    }

    private static byte[][] LoadCorpus()
    {
        string path = Environment.GetEnvironmentVariable("CRYSTAL_BAL_CORPUS")
            ?? throw new InvalidOperationException("CRYSTAL_BAL_CORPUS not set");
        byte[] b = File.ReadAllBytes(path);
        Assert.That(b.AsSpan(0, 4).SequenceEqual("CV10"u8), Is.True);
        int p = 4;
        int n = (int)BinaryPrimitives.ReadUInt32LittleEndian(b.AsSpan(p, 4)); p += 4;
        byte[][] outp = new byte[n][];
        for (int i = 0; i < n; i++)
        {
            int q = (int)BinaryPrimitives.ReadUInt32LittleEndian(b.AsSpan(p, 4)); p += 4;
            outp[i] = b.AsSpan(p, q).ToArray(); p += q;
        }
        Assert.That(p, Is.EqualTo(b.Length));
        return outp;
    }

    private static double Median(List<double> xs)
    {
        xs.Sort();
        return xs[xs.Count / 2];
    }

    [Test]
    public void Frozen_apply_consequence_matches_Nethermind_and_benchmarks()
    {
        byte[][] records = LoadCorpus();
        Assert.That(records.Length, Is.EqualTo(1112));

        for (int i = 0; i < records.Length; i++)
        {
            ReadOnlyBlockAccessList full = Rlp.Decode<ReadOnlyBlockAccessList>(records[i])!;
            CompactAccount[] compact = DecodeCompact(records[i]);
            AssertParity(full, compact, i);
        }

        List<double> fullTimes = [], compactTimes = [];
        for (int round = 0; round < 7; round++)
        {
            Stopwatch sw = Stopwatch.StartNew();
            int sink = 0;
            for (int rep = 0; rep < 20; rep++)
                foreach (byte[] raw in records)
                    sink ^= Rlp.Decode<ReadOnlyBlockAccessList>(raw)!.AccountChanges.Count;
            sw.Stop(); GC.KeepAlive(sink); fullTimes.Add(sw.Elapsed.TotalSeconds);

            sw.Restart(); sink = 0;
            for (int rep = 0; rep < 20; rep++)
                foreach (byte[] raw in records)
                    sink ^= DecodeCompact(raw).Length;
            sw.Stop(); GC.KeepAlive(sink); compactTimes.Add(sw.Elapsed.TotalSeconds);
        }

        double fullMedian = Median(fullTimes);
        double compactMedian = Median(compactTimes);
        string result = string.Join(Environment.NewLine,
            "ETHEREUM_CRYSTAL_V17_NETHERMIND=PASS",
            $"records={records.Length}",
            "nethermind_final_state_projection_parity_all=true",
            $"full_decode_median_s={fullMedian:F9}",
            $"compact_apply_decode_median_s={compactMedian:F9}",
            $"speedup_vs_full={fullMedian / compactMedian:F9}");
        Console.WriteLine(result);
        TestContext.Progress.WriteLine(result);
        string? resultPath = Environment.GetEnvironmentVariable("CRYSTAL_V17_RESULT");
        if (!string.IsNullOrEmpty(resultPath)) File.WriteAllText(resultPath, result);
    }
}
