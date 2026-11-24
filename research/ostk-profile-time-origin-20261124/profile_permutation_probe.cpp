// Apache-2.0. Synthetic affine motion and constant body spin; no Earth data required.
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <iomanip>
#include <OpenSpaceToolkit/Astrodynamics/Flight/Profile/Model/Tabulated.hpp>
#include <OpenSpaceToolkit/Astrodynamics/Trajectory/State/CoordinateSubset/CartesianPosition.hpp>
#include <OpenSpaceToolkit/Astrodynamics/Trajectory/State/CoordinateSubset/CartesianVelocity.hpp>
#include <OpenSpaceToolkit/Astrodynamics/Trajectory/State/CoordinateSubset/AngularVelocity.hpp>
#include <OpenSpaceToolkit/Physics/Coordinate/Position.hpp>
#include <OpenSpaceToolkit/Physics/Coordinate/Velocity.hpp>

using ostk::core::container::Array;
using ostk::core::container::Map;
using ostk::core::type::Shared;
using ostk::mathematics::object::Vector3d;
using ostk::mathematics::geometry::d3::transformation::rotation::Quaternion;
using ostk::mathematics::curvefitting::Interpolator;
using ostk::physics::time::Instant;
using ostk::physics::time::Duration;
using ostk::physics::coordinate::Frame;
using ostk::physics::coordinate::Position;
using ostk::physics::coordinate::Velocity;
using ostk::astrodynamics::trajectory::State;
using ostk::astrodynamics::trajectory::state::CoordinateSubset;
using ostk::astrodynamics::trajectory::state::coordinatesubset::CartesianPosition;
using ostk::astrodynamics::trajectory::state::coordinatesubset::CartesianVelocity;
using ostk::astrodynamics::trajectory::state::coordinatesubset::AngularVelocity;
using ostk::astrodynamics::flight::profile::model::Tabulated;

std::array<double,4> h(const std::array<double,4>& a, const std::array<double,4>& b) {
    const auto [w,x,y,z]=a;const auto [v,i,j,k]=b;
    return {w*v-x*i-y*j-z*k,w*i+x*v+y*k-z*j,w*j-x*k+y*v+z*i,w*k+x*j-y*i+z*v};
}
std::array<double,4> q_at(double t) {
    const double n=std::sqrt(.001*.001+.002*.002+.003*.003), s=std::sin(n*t/2)/n;
    return h({std::sqrt(.86),.2,.3,-.1},{std::cos(n*t/2),.001*s,.002*s,-.003*s});
}
int main(int argc,char**argv) {
    if(argc!=2)return 2;
    std::ofstream out(argv[1]);out<<std::setprecision(17);
    out<<"order,mode,type,query,expected_x,actual_x,position_error,velocity_error,rate_error,attitude_error,timestamp_error\n";
    const auto epoch=Instant::J2000();const auto frame=Frame::GCRF();
    const Vector3d p0={100,-200,300},v={7,-11,13},w={.001,.002,-.003};
    Array<State> states;
    for(int t : {0,10,20,30}) {
        const auto q=q_at(t);
        states.add(State(epoch+Duration::Seconds(t),Position::Meters(p0+t*v,frame),
            Velocity::MetersPerSecond(v,frame),Quaternion(q[1],q[2],q[3],q[0],Quaternion::Format::XYZS),w,frame));
    }
    std::array<int,4> order={0,1,2,3};int cases=0,wrong=0;
    do {
        Array<State> ordered;for(int i:order)ordered.add(states[i]);
        for(int mode=0;mode<3;mode++) {
            for(const auto type : {Interpolator::Type::Linear,Interpolator::Type::BarycentricRational}) {
                if(mode==2 && type!=Interpolator::Type::BarycentricRational)continue;
                auto create=[&]()->Tabulated {
                    if(mode==0)return Tabulated(ordered,type);
                    if(mode==2)return Tabulated::Default(ordered);
                    const Map<Shared<const CoordinateSubset>,Interpolator::Type> types={
                        {CartesianPosition::Default(),type},{CartesianVelocity::Default(),type},{AngularVelocity::Default(),type}};
                    return Tabulated(ordered,types);
                };
                const auto model=create();
                for(int t : {0,5,10,15,20,25,30}) {
                    const auto date=epoch+Duration::Seconds(t);const auto state=model.calculateStateAt(date);
                    const auto expected=p0+t*v;const auto p=state.getPosition().getCoordinates();
                    const double error=(p-expected).norm();
                    const auto q=q_at(t);const auto actual=state.getAttitude().toVector(Quaternion::Format::XYZS);
                    const auto& values=std::array<double,4>{q[1],q[2],q[3],q[0]};
                    double same=0,opposite=0;
                    for(int i=0;i<4;i++){same=std::max(same,std::abs(actual(i)-values[i]));opposite=std::max(opposite,std::abs(actual(i)+values[i]));}
                    out<<order[0]<<'-'<<order[1]<<'-'<<order[2]<<'-'<<order[3]<<','<<mode<<','<<static_cast<int>(type)<<','<<t<<','
                       <<expected(0)<<','<<p(0)<<','<<error<<','<<(state.getVelocity().getCoordinates()-v).norm()<<','
                       <<(state.getAngularVelocity()-w).norm()<<','<<std::min(same,opposite)<<','<<(state.getInstant()-date).inSeconds()<<'\n';
                    cases++;if(error>1e-7)wrong++;
                }
            }
        }
    } while(std::next_permutation(order.begin(),order.end()));
    std::cout<<"cases="<<cases<<" position_discrepancies="<<wrong<<std::endl;
    return 0;
}
