package org.yamcs.mdb;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;

import org.junit.jupiter.api.Test;
import org.yamcs.parameter.Value;
import org.yamcs.parameter.ParameterValue;
import org.yamcs.parameter.SoftwareParameterManager;
import org.yamcs.utils.ValueUtility;
import org.yamcs.xtce.FloatParameterType;
import org.yamcs.xtce.IntegerParameterType;
import org.yamcs.xtce.Parameter;
import org.yamcs.xtce.ParameterType;

/** Offline, exact-source experiment. No server, links, packets or external systems. */
public class MathGraphNumericalProbeTest {
    record Input(Value value, BigInteger mathematicalValue) {}

    private List<Input> inputs() {
        List<Input> result = new ArrayList<>();
        long[] magnitudes = {0, 1, 2, 127, 128, 255, 256, 32767, 32768, 65535, 65536,
                0x7fffffffL, 0x80000000L, 0x80000001L, 0xffffffffL, 0x100000000L,
                0x1fffffffffffffL, 0x20000000000000L, Long.MAX_VALUE};
        for (long n : magnitudes) {
            BigInteger b = BigInteger.valueOf(n);
            if (n <= Integer.MAX_VALUE) result.add(new Input(ValueUtility.getSint32Value((int) n), b));
            result.add(new Input(ValueUtility.getSint64Value(n), b));
            if (n <= 0xffffffffL) result.add(new Input(ValueUtility.getUint32Value((int) n), b));
            result.add(new Input(ValueUtility.getUint64Value(n), b));
        }
        for (long n : new long[] {-1, -2, -127, -128, -129, -32768, -32769, Integer.MIN_VALUE, Long.MIN_VALUE}) {
            if (n >= Integer.MIN_VALUE) result.add(new Input(ValueUtility.getSint32Value((int) n), BigInteger.valueOf(n)));
            result.add(new Input(ValueUtility.getSint64Value(n), BigInteger.valueOf(n)));
        }
        result.add(new Input(ValueUtility.getUint64Value(Long.MIN_VALUE), BigInteger.ONE.shiftLeft(63)));
        result.add(new Input(ValueUtility.getUint64Value(-1L), BigInteger.ONE.shiftLeft(64).subtract(BigInteger.ONE)));
        return result;
    }

    private IntegerParameterType integerType(int bits, boolean signed) {
        return new IntegerParameterType.Builder().setName("probe").setSizeInBits(bits).setSigned(signed).build();
    }

    private BigInteger number(Value v) {
        return switch (v.getType()) {
        case SINT32 -> BigInteger.valueOf(v.getSint32Value());
        case SINT64 -> BigInteger.valueOf(v.getSint64Value());
        case UINT32 -> new BigInteger(Integer.toUnsignedString(v.getUint32Value()));
        case UINT64 -> new BigInteger(Long.toUnsignedString(v.getUint64Value()));
        default -> throw new IllegalArgumentException("Non-integer result");
        };
    }

    private void save(String name, List<String> rows) throws Exception {
        Path out = Path.of(System.getProperty("mathgraph.out", "target/mathgraph"));
        Files.createDirectories(out);
        Files.write(out.resolve(name), rows);
    }

    @Test
    public void integerConversionMatrix() throws Exception {
        List<String> rows = new ArrayList<>();
        rows.add("source\tinput\ttargetBits\ttargetSigned\toracleFits\tactual\tmatch\tdecimalRouteMatch");
        int tested = 0, mismatches = 0, decimalMatches = 0;
        for (Input in : inputs()) {
            for (int bits : new int[] {1, 7, 8, 16, 31, 32, 33, 63, 64}) {
                for (boolean signed : new boolean[] {false, true}) {
                    var target = integerType(bits, signed);
                    BigInteger min = signed ? BigInteger.ONE.shiftLeft(bits - 1).negate() : BigInteger.ZERO;
                    BigInteger max = BigInteger.ONE.shiftLeft(signed ? bits - 1 : bits).subtract(BigInteger.ONE);
                    boolean fits = in.mathematicalValue.compareTo(min) >= 0 && in.mathematicalValue.compareTo(max) <= 0;
                    String actual;
                    boolean match;
                    try {
                        Value converted = DataTypeProcessor.convertEngValueForType(target, in.value);
                        actual = converted.getType() + ":" + number(converted);
                        match = fits && in.mathematicalValue.equals(number(converted));
                    } catch (IllegalArgumentException e) {
                        actual = "REJECT:" + e.getClass().getSimpleName();
                        match = !fits;
                    }
                    boolean decimalMatch;
                    try {
                        Value decimal = DataTypeProcessor.getValueForType(target, target.convertType(in.mathematicalValue.toString()));
                        decimalMatch = fits && in.mathematicalValue.equals(number(decimal));
                    } catch (IllegalArgumentException e) {
                        decimalMatch = !fits;
                    }
                    tested++;
                    if (!match) mismatches++;
                    if (decimalMatch) decimalMatches++;
                    rows.add(in.value.getType() + "\t" + in.mathematicalValue + "\t" + bits + "\t" + signed
                            + "\t" + fits + "\t" + actual + "\t" + match + "\t" + decimalMatch);
                }
            }
        }
        save("integers.tsv", rows);
        System.out.printf("INTEGER_MATRIX tested=%d mismatches=%d decimal_controls=%d%n", tested, mismatches, decimalMatches);
        assertEquals(tested, decimalMatches, "independent range oracle must agree with documented decimal conversion");
        if (Boolean.getBoolean("mathgraph.strict")) assertEquals(0, mismatches);
    }

    @Test
    public void floatingConversionMatrix() throws Exception {
        List<String> rows = new ArrayList<>();
        rows.add("source\tinput\ttargetBits\toracle\tactual\tmatch\tvalueToDoubleControl");
        int tested = 0, mismatches = 0, controls = 0;
        for (Input in : inputs()) {
            for (int bits : new int[] {32, 64}) {
                var target = new FloatParameterType.Builder().setName("probe").setSizeInBits(bits).build();
                double expected = bits == 32 ? (double) in.mathematicalValue.floatValue() : in.mathematicalValue.doubleValue();
                Value converted = DataTypeProcessor.convertEngValueForType(target, in.value);
                double actual = converted.toDouble();
                boolean match = Double.doubleToLongBits(expected) == Double.doubleToLongBits(actual);
                boolean control = Double.doubleToLongBits(in.mathematicalValue.doubleValue()) == Double.doubleToLongBits(in.value.toDouble());
                tested++;
                if (!match) mismatches++;
                if (control) controls++;
                rows.add(in.value.getType() + "\t" + in.mathematicalValue + "\t" + bits + "\t" + expected + "\t" + actual + "\t" + match + "\t" + control);
            }
        }
        save("floats.tsv", rows);
        System.out.printf("FLOAT_MATRIX tested=%d mismatches=%d value_controls=%d%n", tested, mismatches, controls);
        assertEquals(tested, controls, "independent exact-number oracle must agree with Value.toDouble control");
        if (Boolean.getBoolean("mathgraph.strict")) assertEquals(0, mismatches);
    }

    @Test
    public void unsignedLongDocumentedContract() throws Exception {
        List<String> rows = new ArrayList<>();
        rows.add("input\toracleFitsSignedLong\tactual\tmatch");
        int tested = 0, mismatches = 0;
        for (Input in : inputs()) {
            if (in.value.getType() != org.yamcs.protobuf.Yamcs.Value.Type.UINT64) continue;
            boolean fits = in.mathematicalValue.compareTo(BigInteger.valueOf(Long.MAX_VALUE)) <= 0;
            String actual;
            boolean match;
            try {
                long value = in.value.toLong();
                actual = Long.toString(value);
                match = fits && BigInteger.valueOf(value).equals(in.mathematicalValue);
            } catch (UnsupportedOperationException e) {
                actual = "REJECT:UnsupportedOperationException";
                match = !fits;
            }
            tested++;
            if (!match) mismatches++;
            rows.add(in.mathematicalValue + "\t" + fits + "\t" + actual + "\t" + match);
        }
        save("to-long.tsv", rows);
        System.out.printf("TO_LONG_MATRIX tested=%d mismatches=%d%n", tested, mismatches);
        assertTrue(tested > 0);
        if (Boolean.getBoolean("mathgraph.strict")) assertEquals(0, mismatches);
    }

    @Test
    public void softwareParameterConsumer() throws Exception {
        List<String> rows = new ArrayList<>();
        rows.add("input\ttarget\toracleFits\tactual\tmatch");
        int tested = 0, mismatches = 0;
        for (long n : new long[] {0, 1, 127, 128, 255, 256, 0x7fffffffL, 0x80000000L, 0x80000001L, 0xffffffffL}) {
            for (ParameterType target : new ParameterType[] {
                    integerType(8, false), integerType(8, true), integerType(32, false), integerType(64, true),
                    new FloatParameterType.Builder().setName("probe").setSizeInBits(64).build()}) {
                Parameter p = new Parameter("synthetic_parameter");
                p.setParameterType(target);
                ParameterValue pv = new ParameterValue(p);
                pv.setEngValue(ValueUtility.getUint32Value((int) n));
                BigInteger expected = BigInteger.valueOf(n);
                boolean fits = true;
                String label = "float64";
                if (target instanceof IntegerParameterType it) {
                    BigInteger max = BigInteger.ONE.shiftLeft(it.getSizeInBits() - (it.isSigned() ? 1 : 0)).subtract(BigInteger.ONE);
                    fits = expected.compareTo(max) <= 0;
                    label = (it.isSigned() ? "signed" : "unsigned") + it.getSizeInBits();
                }
                String actual;
                boolean match;
                try {
                    // The ordinary whole-value branch does not consult the cache. No manager, server or link is started.
                    Value converted = SoftwareParameterManager.transformValue(null, pv).getEngValue();
                    if (target instanceof FloatParameterType) {
                        actual = Double.toString(converted.toDouble());
                        match = Double.doubleToLongBits(converted.toDouble()) == Double.doubleToLongBits(expected.doubleValue());
                    } else {
                        actual = number(converted).toString();
                        match = fits && expected.equals(number(converted));
                    }
                } catch (IllegalArgumentException e) {
                    actual = "REJECT:" + e.getClass().getSimpleName();
                    match = !fits;
                }
                tested++;
                if (!match) mismatches++;
                rows.add(n + "\t" + label + "\t" + fits + "\t" + actual + "\t" + match);
            }
        }
        save("consumer.tsv", rows);
        System.out.printf("CONSUMER_MATRIX tested=%d mismatches=%d%n", tested, mismatches);
        if (Boolean.getBoolean("mathgraph.strict")) assertEquals(0, mismatches);
    }
}
