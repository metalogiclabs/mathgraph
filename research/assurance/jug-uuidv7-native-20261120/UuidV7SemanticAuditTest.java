package com.fasterxml.uuid.impl;

import com.fasterxml.uuid.UUIDComparator;
import java.util.Arrays;
import java.util.Random;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import static org.junit.jupiter.api.Assertions.*;

/** Versioned third-domain pilot: RFC 9562 §5.7 vs authentic JUG v7 classes.
 * Bounded source-inspected probe, not a bug allegation or deployment warrant.
 */
public class UuidV7SemanticAuditTest {
    private static final long MAX_TS = (1L << 48) - 1;

    private static Random allZeroEntropy() {
        return new Random(0) {
            @Override public void nextBytes(byte[] target) {
                Arrays.fill(target, (byte) 0);
            }
        };
    }

    private static void assertRfcLayout(UUID result, long expectedTimestamp) {
        assertEquals(7, result.version(), "RFC 9562: version 7");
        assertEquals(2, result.variant(), "RFC 9562: variant 10");
        assertEquals(expectedTimestamp, (result.getMostSignificantBits() >>> 16) & MAX_TS,
                "RFC 9562: unsigned big-endian 48-bit milliseconds");
    }

    @Test public void boundaryTimestampLayoutBothOriginalGenerators() {
        long[] values = {
            0L, 1L, 0xFFL, 0xFFFFL,
            (1L << 32), (1L << 47) - 1,
            1L << 47, MAX_TS
        };
        TimeBasedEpochGenerator monotonic = new TimeBasedEpochGenerator(new Random(1001));
        TimeBasedEpochRandomGenerator perCall = new TimeBasedEpochRandomGenerator(new Random(1001));
        for (long ts : values) {
            assertRfcLayout(monotonic.construct(ts), ts);
            assertRfcLayout(perCall.construct(ts), ts);
        }
        System.out.println("RFC9562_FIELD_LAYOUT_BOUNDARY_CASES=" + (values.length * 2));
    }

    @Test public void seededFieldLayoutBothOriginalGenerators() {
        Random timestampSource = new Random(73569915L);
        TimeBasedEpochGenerator monotonic = new TimeBasedEpochGenerator(new Random(2204));
        TimeBasedEpochRandomGenerator perCall = new TimeBasedEpochRandomGenerator(new Random(2204));
        for (int i = 0; i < 512; ++i) {
            long ts = timestampSource.nextLong() & MAX_TS;
            assertRfcLayout(monotonic.construct(ts), ts);
            assertRfcLayout(perCall.construct(ts), ts);
        }
        System.out.println("RFC9562_FIELD_LAYOUT_SEEDED_CASES=1024");
    }

    @Test public void sameMillisecondModeDifferenceIsNotAbsoluteUniquenessPromise() {
        long fixed = 1732147200000L;
        TimeBasedEpochGenerator increment = new TimeBasedEpochGenerator(allZeroEntropy());
        TimeBasedEpochRandomGenerator perCall = new TimeBasedEpochRandomGenerator(allZeroEntropy());
        UUID a = increment.construct(fixed);
        UUID b = increment.construct(fixed);
        UUID x = perCall.construct(fixed);
        UUID y = perCall.construct(fixed);
        assertRfcLayout(a, fixed);
        assertRfcLayout(b, fixed);
        assertRfcLayout(x, fixed);
        assertRfcLayout(y, fixed);
        assertNotEquals(a, b, "original incrementing mode must advance zero entropy");
        assertTrue(UUIDComparator.staticCompare(a, b) < 0);
        assertEquals(x, y, "test-supplied degenerate entropy makes per-call mode repeat");
        System.out.println("MODE_CONDITION_WITNESS=INCREMENT_DISTINCT_RANDOM_MODE_REPEAT_UNDER_ZERO_ENTROPY");
    }

    @Test public void javaSignedComparisonCrossesTimestampHighBitButJUGComparatorDoesNot() {
        // Both times are within the RFC's 48-bit unsigned valid range.
        TimeBasedEpochGenerator generator = new TimeBasedEpochGenerator(allZeroEntropy());
        long earlier = (1L << 47) - 1;
        long later = (1L << 47);
        UUID before = generator.construct(earlier);
        UUID after = generator.construct(later);
        assertRfcLayout(before, earlier);
        assertRfcLayout(after, later);
        assertTrue(before.compareTo(after) > 0,
                "JDK signed ordering reverses across bit 47 (PREVIOUSLY DOCUMENTED)");
        assertTrue(UUIDComparator.staticCompare(before, after) < 0,
                "JUG documented comparator follows unsigned RFC chronological order");
        assertTrue(before.toString().compareTo(after.toString()) < 0);
        System.out.println("JDK_SIGNED_ORDER_COUNTEREXAMPLE=PREVIOUSLY_DOCUMENTED_JUG_COMPARATOR_REPAIRS");
    }

    @Test public void admitOnlyVersionedScopeAndDoNotInferActionAuthority() {
        // A passing format witness cannot establish randomness quality, a collision
        // bound, issuer permission, or the requested operating environment.
        String scope = "RFC9562-5.7/PINNED-JUG/V7/8-BOUNDARY+512-SEEDED/LOCAL";
        assertTrue(scope.contains("PINNED-JUG"));
        assertFalse(scope.contains("MISSION_APPROVED"));
        System.out.println("ACTION_AUTHORITY=UNKNOWN; UNQUALIFIED_DISTRIBUTIONAL_CLAIMS=UNKNOWN");
    }
}
