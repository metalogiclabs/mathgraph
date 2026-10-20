// Frozen source: bounded Aeneas Drop soundness regression, based on upstream issue #1410.
// No unsafe code, no external crates. Native Rust result: fn0() = 7.
pub struct Guard<'a> {
    log: &'a mut i32,
    id: i32,
}
impl<'a> Drop for Guard<'a> {
    fn drop(&mut self) {
        *self.log = *self.log * 10 + self.id;
    }
}
pub fn fn0() -> i32 {
    let mut log = 0;
    {
        let _g = Guard { log: &mut log, id: 7 };
    }
    log
}
pub fn control() -> i32 {
    let log = 0;
    log
}
fn main() {
    println!("NATIVE_DROP={}", fn0());
    println!("NATIVE_CONTROL={}", control());
}
