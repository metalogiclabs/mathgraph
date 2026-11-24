"""OSTk astrodynamics 18.0.1, with normal OSTk Python data setup completed."""
import numpy as np
from ostk.physics.time import Instant, Duration
from ostk.physics.coordinate import Frame, Position, Velocity
from ostk.mathematics.geometry.d3.transformation.rotation import Quaternion
from ostk.mathematics.curve_fitting import Interpolator
from ostk.astrodynamics.trajectory import State
from ostk.astrodynamics.flight.profile.model import Tabulated

epoch, frame = Instant.J2000(), Frame.GCRF()
states = [State(epoch + Duration.seconds(t),
                Position.meters(np.array([100.0 + 7*t, 0.0, 0.0]), frame),
                Velocity.meters_per_second(np.array([7.0, 0.0, 0.0]), frame),
                Quaternion.unit(), np.zeros(3), frame)
          for t in [0, 10, 20]]
for order in [[0, 1, 2], [1, 0, 2]]:
    model = Tabulated([states[i] for i in order], Interpolator.Type.Linear)
    x = model.calculate_state_at(epoch + Duration.seconds(5)).get_position().get_coordinates()[0]
    print(order, x)
# Expected both: 135.0. Actual released 18.0.1: 135.0, 205.0.
