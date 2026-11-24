import java.io.ByteArrayInputStream;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.Locale;
import org.hipparchus.geometry.euclidean.threed.Vector3D;
import org.orekit.data.DataContext;
import org.orekit.data.DataSource;
import org.orekit.data.DirectoryCrawler;
import org.orekit.files.ccsds.ndm.ParserBuilder;
import org.orekit.files.ccsds.ndm.adm.aem.Aem;

/** Two synthetic AEM messages differ only in ANGVEL_FRAME.
 * Their quaternion maps external X to body -Y (a passive 90 degree Z rotation).
 * The payload is [1,0,0] deg/s in the declared frame.
 */
public class MinimalAemRate {
    public static void main(String[] args) {
        DataContext.getDefault().getDataProvidersManager().addProvider(new DirectoryCrawler(new File(args[0])));
        for (String frame : new String[] {"SC_BODY_1", "EME2000"}) {
            String message = "CCSDS_AEM_VERS = 2.0\nCREATION_DATE = 2023-01-01T00:00:00\nORIGINATOR = MATHGRAPH\n" +
                "META_START\nOBJECT_NAME = SYNTHETIC\nOBJECT_ID = 2023-001A\nCENTER_NAME = EARTH\n" +
                "REF_FRAME_A = EME2000\nREF_FRAME_B = SC_BODY_1\nTIME_SYSTEM = TAI\n" +
                "START_TIME = 2023-01-01T00:00:00\nSTOP_TIME = 2023-01-01T00:00:01\n" +
                "ATTITUDE_TYPE = QUATERNION/ANGVEL\nANGVEL_FRAME = " + frame + "\nMETA_STOP\nDATA_START\n" +
                "2023-01-01T00:00:00 0 0 0.7071067811865476 0.7071067811865476 1 0 0\n" +
                "2023-01-01T00:00:01 0 0 0.7071067811865476 0.7071067811865476 1 0 0\nDATA_STOP\n";
            Aem file = new ParserBuilder().buildAemParser().parseMessage(new DataSource("minimal.aem",
                    () -> new ByteArrayInputStream(message.getBytes(StandardCharsets.UTF_8))));
            Vector3D actual = file.getSegments().get(0).getAngularCoordinates().get(0).getRotationRate();
            Vector3D expected = "SC_BODY_1".equals(frame) ? new Vector3D(Math.toRadians(1), 0, 0) :
                    new Vector3D(0, -Math.toRadians(1), 0);
            System.out.printf(Locale.ROOT, "%s expected=(%.12f,%.12f,%.12f) actual=(%.12f,%.12f,%.12f) deg/s error=%.12f deg/s%n",
                    frame, Math.toDegrees(expected.getX()), Math.toDegrees(expected.getY()), Math.toDegrees(expected.getZ()),
                    Math.toDegrees(actual.getX()), Math.toDegrees(actual.getY()), Math.toDegrees(actual.getZ()),
                    Math.toDegrees(actual.distance(expected)));
        }
    }
}
