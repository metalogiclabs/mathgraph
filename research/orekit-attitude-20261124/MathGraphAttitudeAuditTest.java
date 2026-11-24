package org.orekit.files.ccsds.ndm.adm.aem;

import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.nio.file.StandardOpenOption;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

import org.hipparchus.geometry.euclidean.threed.Rotation;
import org.hipparchus.geometry.euclidean.threed.RotationOrder;
import org.hipparchus.geometry.euclidean.threed.Vector3D;
import org.junit.jupiter.api.Assertions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.orekit.Utils;
import org.orekit.data.DataSource;
import org.orekit.files.ccsds.ndm.ParserBuilder;
import org.orekit.files.ccsds.ndm.adm.AttitudeEndpoints;
import org.orekit.files.ccsds.ndm.adm.AttitudeType;
import org.orekit.time.AbsoluteDate;
import org.orekit.utils.TimeStampedAngularCoordinates;

/** Bounded audit. The oracle uses elementary passive matrices and Hamilton products,
 * independently of Orekit's Euler constructors/extractors and read/write round trips.
 * Units in direct build/generate calls are SI; KVN wire values are degrees and deg/s.
 */
public class MathGraphAttitudeAuditTest {
    private static final double[][] ANGLES = {{0.23, 0.41, -0.67}, {-0.52, 0.83, 0.36},
                                              {0.78, 1.12, -0.49}, {-0.31, 0.64, 0.93}};
    private static final double[] D = {0.013, -0.021, 0.034};
    private static final double[] W = {0.017, -0.029, 0.043};

    @BeforeEach
    void setup() { Utils.setDataRoot("regular-data"); }

    @Test
    void independentOrientationAndDerivativeControls() throws Exception {
        int cases = 0;
        final List<String> errors = new ArrayList<>();
        for (RotationOrder order : RotationOrder.values()) {
            for (double[] a : ANGLES) {
                final double[][] m = matrix(order, a);
                final double[] q = quaternion(order, a);
                final double[] qd = quaternionDerivative(order, a);
                final double[] w = rate(order, a);
                for (boolean forward : new boolean[] {true, false}) {
                    final double[][] expected = forward ? m : transpose(m);
                    final double[] expectedRate = forward ? w : scale(mv(transpose(m), w), -1);
                    for (boolean first : new boolean[] {true, false}) {
                        for (AttitudeType type : new AttitudeType[] {AttitudeType.QUATERNION,
                                AttitudeType.EULER_ANGLE, AttitudeType.QUATERNION_DERIVATIVE,
                                AttitudeType.EULER_ANGLE_DERIVATIVE}) {
                            final boolean isQ = type == AttitudeType.QUATERNION || type == AttitudeType.QUATERNION_DERIVATIVE;
                            final boolean derivative = type == AttitudeType.QUATERNION_DERIVATIVE || type == AttitudeType.EULER_ANGLE_DERIVATIVE;
                            final double[] values = isQ ? ordered(q, first) : a.clone();
                            final double[] input = derivative ? join(values, isQ ? ordered(qd, first) : D) : values;
                            final TimeStampedAngularCoordinates ac = type.build(first, forward, order, true, AbsoluteDate.J2000_EPOCH, input);
                            final double re = maxDiff(expected, ac.getRotation().getMatrix());
                            final double we = derivative ? distance(expectedRate, ac.getRotationRate().toArray()) : 0;
                            cases++;
                            if (re > 3e-14 || we > 3e-12) errors.add(type + " " + order + " " + forward + " " + first + " matrix=" + re + " rate=" + we);
                            // Independently seed generateData, then decode its output with the matrix oracle.
                            final double[] oq = forward ? q : new double[] {q[0], -q[1], -q[2], -q[3]};
                            final TimeStampedAngularCoordinates seed = new TimeStampedAngularCoordinates(AbsoluteDate.J2000_EPOCH,
                                    new Rotation(oq[0], oq[1], oq[2], oq[3], false), new Vector3D(expectedRate), Vector3D.ZERO);
                            final double[] generated = type.generateData(first, forward, order, true, seed);
                            final double[][] generatedMatrix = isQ ? quaternionMatrix(unordered(generated, first)) : matrix(order, generated);
                            final double ge = maxDiff(m, generatedMatrix);
                            cases++;
                            if (ge > 3e-14) errors.add("generate " + type + " " + order + " matrix=" + ge);
                        }
                    }
                }
            }
        }
        record("orientation-derivative-controls", cases, errors);
    }

    @Test
    void directAngularVelocityFrames() throws Exception {
        int cases = 0;
        final List<String> errors = new ArrayList<>();
        for (RotationOrder order : RotationOrder.values()) {
            for (double[] a : ANGLES) {
                final double[][] m = matrix(order, a);
                for (boolean forward : new boolean[] {true, false}) {
                    for (boolean body : new boolean[] {true, false}) {
                        for (boolean first : new boolean[] {true, false}) {
                            for (AttitudeType type : new AttitudeType[] {AttitudeType.QUATERNION_ANGVEL, AttitudeType.EULER_ANGLE_ANGVEL}) {
                                final double[] angles = type == AttitudeType.QUATERNION_ANGVEL ? ordered(quaternion(order, a), first) : a;
                                final double[] payload = forward ? (body ? W : mv(transpose(m), W)) :
                                        scale(body ? W : mv(m, W), -1);
                                final TimeStampedAngularCoordinates ac = type.build(first, forward, order, body, AbsoluteDate.J2000_EPOCH, join(angles, payload));
                                final double error = distance(W, ac.getRotationRate().toArray());
                                cases++;
                                csv("direct", type + "," + order + "," + forward + "," + body + "," + first + "," + error);
                                if (error > 3e-13) errors.add(type + " " + order + " forward=" + forward + " body=" + body + " error=" + error);
                            }
                        }
                    }
                }
            }
        }
        record("direct-angular-velocity", cases, errors);
    }

    @Test
    void parsedAemAngularVelocityFrames() throws Exception {
        int cases = 0;
        final List<String> errors = new ArrayList<>();
        for (RotationOrder order : RotationOrder.values()) {
            for (double[] a : ANGLES) {
                final double[][] m = matrix(order, a);
                for (boolean forward : new boolean[] {true, false}) {
                    for (boolean body : new boolean[] {true, false}) {
                        for (AttitudeType type : new AttitudeType[] {AttitudeType.QUATERNION_ANGVEL, AttitudeType.EULER_ANGLE_ANGVEL}) {
                            final Aem file = parse(message(type, order, a, forward, body));
                            final AemSegment segment = file.getSegments().get(0);
                            final TimeStampedAngularCoordinates ac = segment.getAngularCoordinates().get(0);
                            final double error = distance(W, ac.getRotationRate().toArray());
                            final double matrixError = maxDiff(forward ? m : transpose(m), ac.getRotation().getMatrix());
                            cases++;
                            csv("parsed", type + "," + order + "," + forward + "," + body + ",false," + error + "," + matrixError);
                            if (error > 3e-13 || matrixError > 3e-14) errors.add(type + " " + order + " forward=" + forward + " body=" + body + " rate=" + error + " matrix=" + matrixError);
                        }
                    }
                }
            }
        }
        record("parsed-aem-angular-velocity", cases, errors);
    }

    @Test
    void generatedAngularVelocityFrames() throws Exception {
        int cases = 0;
        final List<String> errors = new ArrayList<>();
        for (RotationOrder order : RotationOrder.values()) {
            for (double[] a : ANGLES) {
                final double[][] m = matrix(order, a);
                final double[] q = quaternion(order, a);
                for (boolean forward : new boolean[] {true, false}) {
                    final double[] oq = forward ? q : new double[] {q[0], -q[1], -q[2], -q[3]};
                    final TimeStampedAngularCoordinates seed = new TimeStampedAngularCoordinates(AbsoluteDate.J2000_EPOCH,
                            new Rotation(oq[0], oq[1], oq[2], oq[3], false), new Vector3D(W), Vector3D.ZERO);
                    for (boolean body : new boolean[] {true, false}) {
                        final double[] expected = forward ? (body ? W : mv(transpose(m), W)) : scale(body ? W : mv(m, W), -1);
                        for (boolean first : new boolean[] {true, false}) {
                            for (AttitudeType type : new AttitudeType[] {AttitudeType.QUATERNION_ANGVEL, AttitudeType.EULER_ANGLE_ANGVEL}) {
                                final double[] data = type.generateData(first, forward, order, body, seed);
                                final boolean isQ = type == AttitudeType.QUATERNION_ANGVEL;
                                final int start = isQ ? 4 : 3;
                                final double error = distance(expected, new double[] {data[start], data[start + 1], data[start + 2]});
                                final double matrixError = maxDiff(m, isQ ? quaternionMatrix(unordered(data, first)) : matrix(order, data));
                                cases++;
                                csv("generate", type + "," + order + "," + forward + "," + body + "," + first + "," + error + "," + matrixError);
                                if (error > 3e-13 || matrixError > 3e-14) errors.add(type + " " + order + " forward=" + forward + " body=" + body + " rate=" + error + " matrix=" + matrixError);
                            }
                        }
                    }
                }
            }
        }
        record("generated-angular-velocity", cases, errors);
    }

    @Test
    void originalAuthorFixtureBodyRate() {
        final String resource = "/ccsds/adm/aem/AEMExample14.txt";
        final Aem file = new ParserBuilder().buildAemParser().parseMessage(new DataSource(resource,
                () -> getClass().getResourceAsStream(resource)));
        // The author's fourth segment explicitly declares ANGVEL_FRAME = SC_BODY_1.
        final Vector3D expected = new Vector3D(Math.toRadians(-0.021029),
                Math.toRadians(0.023643), Math.toRadians(18.288407));
        final Vector3D actual = file.getSegments().get(3).getAngularCoordinates().get(0).getRotationRate();
        System.out.println("MATHGRAPH original-fixture expected=" + expected + " actual=" + actual +
                " error-rad-s=" + expected.distance(actual));
        Assertions.assertEquals(0.0, expected.distance(actual), 1e-14);
    }

    @Test
    void defaultDirectionCompatibility() throws Exception {
        final AttitudeEndpoints implicit = parse(message(AttitudeType.QUATERNION_ANGVEL,
                RotationOrder.XYZ, ANGLES[0], true, true)).getSegments().get(0).getMetadata().getEndpoints();
        final AttitudeEndpoints explicit = parse(message(AttitudeType.QUATERNION_ANGVEL,
                RotationOrder.XYZ, ANGLES[0], true, true)).getSegments().get(0).getMetadata().getEndpoints();
        explicit.setA2b(true);
        Assertions.assertTrue(implicit.isA2b());
        Assertions.assertTrue(explicit.isA2b());
        Assertions.assertAll(() -> Assertions.assertTrue(implicit.isCompatibleWith(implicit)),
                             () -> Assertions.assertTrue(implicit.isCompatibleWith(explicit)),
                             () -> Assertions.assertTrue(explicit.isCompatibleWith(implicit)));
    }

    private static Aem parse(String message) {
        return new ParserBuilder().buildAemParser().parseMessage(new DataSource("synthetic.aem",
                () -> new ByteArrayInputStream(message.getBytes(StandardCharsets.UTF_8))));
    }

    private static String message(AttitudeType type, RotationOrder order, double[] a, boolean forward, boolean body) {
        final boolean isQ = type == AttitudeType.QUATERNION_ANGVEL;
        final double[][] m = matrix(order, a);
        final double[] payload = forward ? (body ? W : mv(transpose(m), W)) : scale(body ? W : mv(m, W), -1);
        final double[] values = isQ ? ordered(quaternion(order, a), false) : a;
        final StringBuilder line = new StringBuilder("2023-01-01T00:00:00");
        for (double value : values) line.append(String.format(Locale.ROOT, " %.17g", isQ ? value : Math.toDegrees(value)));
        for (double value : payload) line.append(String.format(Locale.ROOT, " %.17g", Math.toDegrees(value)));
        return "CCSDS_AEM_VERS = 2.0\nCREATION_DATE = 2023-01-01T00:00:00\nORIGINATOR = MATHGRAPH\n" +
                "META_START\nOBJECT_NAME = SYNTHETIC\nOBJECT_ID = 2023-001A\nCENTER_NAME = EARTH\n" +
                "REF_FRAME_A = " + (forward ? "EME2000" : "SC_BODY_1") + "\n" +
                "REF_FRAME_B = " + (forward ? "SC_BODY_1" : "EME2000") + "\n" +
                "TIME_SYSTEM = TAI\nSTART_TIME = 2023-01-01T00:00:00\nSTOP_TIME = 2023-01-01T00:00:01\n" +
                "ATTITUDE_TYPE = " + (isQ ? "QUATERNION/ANGVEL" : "EULER_ANGLE/ANGVEL") + "\n" +
                (isQ ? "" : "EULER_ROT_SEQ = " + order + "\n") +
                "ANGVEL_FRAME = " + (body ? "SC_BODY_1" : "EME2000") + "\nMETA_STOP\nDATA_START\n" +
                line + "\n" + line.toString().replace("00:00:00", "00:00:01") + "\nDATA_STOP\n";
    }

    // CCSDS 504.0-B-2 Annex F3: M_BA = M_axis3(a3) M_axis2(a2) M_axis1(a1).
    private static double[][] elementary(char axis, double a) {
        double c = Math.cos(a), s = Math.sin(a);
        switch (axis) {
            case 'X': return new double[][] {{1,0,0},{0,c,s},{0,-s,c}};
            case 'Y': return new double[][] {{c,0,-s},{0,1,0},{s,0,c}};
            case 'Z': return new double[][] {{c,s,0},{-s,c,0},{0,0,1}};
            default: throw new IllegalArgumentException();
        }
    }
    private static double[][] matrix(RotationOrder order, double[] a) {
        return mm(elementary(order.name().charAt(2), a[2]), mm(elementary(order.name().charAt(1), a[1]), elementary(order.name().charAt(0), a[0])));
    }
    private static double[] quaternion(RotationOrder order, double[] a) {
        double[] q = {1,0,0,0};
        for (int i=0;i<3;i++) {
            double[] p = {Math.cos(a[i]/2),0,0,0}; p[1+"XYZ".indexOf(order.name().charAt(i))] = Math.sin(a[i]/2);
            q = hamilton(q,p);
        }
        return q;
    }
    private static double[] quaternionDerivative(RotationOrder order, double[] a) {
        double[] sum = new double[4];
        for (int k=0;k<3;k++) {
            double[] q = {1,0,0,0};
            for (int i=0;i<3;i++) {
                double[] p = {i==k ? -Math.sin(a[i]/2)*D[i]/2 : Math.cos(a[i]/2),0,0,0};
                p[1+"XYZ".indexOf(order.name().charAt(i))] = i==k ? Math.cos(a[i]/2)*D[i]/2 : Math.sin(a[i]/2);
                q = hamilton(q,p);
            }
            for(int j=0;j<4;j++) sum[j]+=q[j];
        }
        return sum;
    }
    private static double[] rate(RotationOrder order, double[] a) {
        // Five-point finite difference of independent matrix curve, then -Rdot R^T = skew(omega_body).
        double h=0.001; double[][] derivative=new double[3][3];
        for(int k : new int[] {-2,-1,1,2}) {
            double[] shifted = {a[0]+k*h*D[0],a[1]+k*h*D[1],a[2]+k*h*D[2]};
            double coefficient = k==-2 ? 1 : k==-1 ? -8 : k==1 ? 8 : -1;
            double[][] m=matrix(order,shifted);
            for(int i=0;i<3;i++) for(int j=0;j<3;j++) derivative[i][j]+=coefficient*m[i][j]/(12*h);
        }
        double[][] s=mm(derivative,transpose(matrix(order,a)));
        return new double[] {(s[1][2]-s[2][1])/2,(s[2][0]-s[0][2])/2,(s[0][1]-s[1][0])/2};
    }
    private static double[] hamilton(double[] a,double[] b) {
        return new double[] {a[0]*b[0]-a[1]*b[1]-a[2]*b[2]-a[3]*b[3],
            a[0]*b[1]+a[1]*b[0]+a[2]*b[3]-a[3]*b[2],
            a[0]*b[2]-a[1]*b[3]+a[2]*b[0]+a[3]*b[1],
            a[0]*b[3]+a[1]*b[2]-a[2]*b[1]+a[3]*b[0]};
    }
    private static double[][] quaternionMatrix(double[] q) {
        double w=q[0],x=q[1],y=q[2],z=q[3];
        return new double[][] {{w*w+x*x-y*y-z*z,2*(x*y+z*w),2*(x*z-y*w)},
            {2*(x*y-z*w),w*w-x*x+y*y-z*z,2*(y*z+x*w)},
            {2*(x*z+y*w),2*(y*z-x*w),w*w-x*x-y*y+z*z}};
    }
    private static double[] ordered(double[] q,boolean first) {return first ? q.clone() : new double[] {q[1],q[2],q[3],q[0]};}
    private static double[] unordered(double[] q,boolean first) {return first ? new double[] {q[0],q[1],q[2],q[3]} : new double[] {q[3],q[0],q[1],q[2]};}
    private static double[] join(double[] a,double[] b) {double[] r=new double[a.length+b.length];System.arraycopy(a,0,r,0,a.length);System.arraycopy(b,0,r,a.length,b.length);return r;}
    private static double[][] mm(double[][] a,double[][] b) {double[][] r=new double[3][3];for(int i=0;i<3;i++)for(int j=0;j<3;j++)for(int k=0;k<3;k++)r[i][j]+=a[i][k]*b[k][j];return r;}
    private static double[][] transpose(double[][] a) {double[][] r=new double[3][3];for(int i=0;i<3;i++)for(int j=0;j<3;j++)r[i][j]=a[j][i];return r;}
    private static double[] mv(double[][] a,double[] v) {double[] r=new double[3];for(int i=0;i<3;i++)for(int j=0;j<3;j++)r[i]+=a[i][j]*v[j];return r;}
    private static double[] scale(double[] a,double s) {double[] r=a.clone();for(int i=0;i<r.length;i++)r[i]*=s;return r;}
    private static double maxDiff(double[][] a,double[][] b) {double e=0;for(int i=0;i<3;i++)for(int j=0;j<3;j++)e=Math.max(e,Math.abs(a[i][j]-b[i][j]));return e;}
    private static double distance(double[] a,double[] b) {double e=0;for(int i=0;i<3;i++)e+=(a[i]-b[i])*(a[i]-b[i]);return Math.sqrt(e);}
    private static void csv(String group,String row) throws Exception {Files.write(Paths.get("target/mathgraph-"+group+".csv"),(row+"\n").getBytes(StandardCharsets.UTF_8),StandardOpenOption.CREATE,StandardOpenOption.APPEND);}
    private static void record(String name,int cases,List<String> errors) {
        System.out.println("MATHGRAPH " + name + " cases=" + cases + " discrepancies=" + errors.size());
        Assertions.assertTrue(errors.isEmpty(), () -> String.join("\n",errors.subList(0,Math.min(8,errors.size()))));
    }
}
