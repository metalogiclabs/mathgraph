use safe_time::euler213_to_quaternion;
fn emit(kind: &str, p: f64, r: f64, y: f64) {
    let (x, yy, z, w) = euler213_to_quaternion(p.to_radians(), r.to_radians(), y.to_radians());
    println!("{kind},{p},{r},{y},{x:.17e},{yy:.17e},{z:.17e},{w:.17e}");
}
fn main() {
    println!("kind,pitch_deg,roll_deg,yaw_deg,x,y,z,w");
    let angles = [-60.0, -30.0, -10.0, 15.0, 45.0, 80.0];
    emit("control", 0.0, 0.0, 0.0);
    for a in angles {
        emit("control", a, 0.0, 0.0);
        emit("control", 0.0, a, 0.0);
        emit("control", 0.0, 0.0, a);
    }
    for p in angles { for r in angles { for y in angles { emit("mixed", p, r, y); }}}
    emit("witness", 23.0, -31.0, 47.0);
}
