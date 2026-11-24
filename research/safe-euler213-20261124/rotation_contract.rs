use safe_time::euler213_to_quaternion;
type M = [[f64; 3]; 3];
fn mul(a: M, b: M) -> M {
    std::array::from_fn(|i| std::array::from_fn(|j| (0..3).map(|k| a[i][k]*b[k][j]).sum()))
}
fn transpose(a: M) -> M { std::array::from_fn(|i| std::array::from_fn(|j| a[j][i])) }
fn error(a: M, b: M) -> f64 {
    (0..3).flat_map(|i| (0..3).map(move |j| (a[i][j]-b[i][j]).abs())).fold(0.0, f64::max)
}
#[test]
fn mixed_axes_agree_with_a_213_convention() {
    let (p,r,y) = (23.0_f64.to_radians(), -31.0_f64.to_radians(), 47.0_f64.to_radians());
    let (sp,cp)=p.sin_cos(); let (sr,cr)=r.sin_cos(); let (sy,cy)=y.sin_cos();
    let rx=[[1.0,0.0,0.0],[0.0,cr,-sr],[0.0,sr,cr]];
    let ry=[[cp,0.0,sp],[0.0,1.0,0.0],[-sp,0.0,cp]];
    let rz=[[cy,-sy,0.0],[sy,cy,0.0],[0.0,0.0,1.0]];
    let intrinsic=mul(mul(ry,rx),rz); let extrinsic=mul(mul(rz,rx),ry);
    let (x,y,z,w)=euler213_to_quaternion(p,r,y);
    let actual=[
        [1.0-2.0*(y*y+z*z),2.0*(x*y-z*w),2.0*(x*z+y*w)],
        [2.0*(x*y+z*w),1.0-2.0*(x*x+z*z),2.0*(y*z-x*w)],
        [2.0*(x*z-y*w),2.0*(y*z+x*w),1.0-2.0*(x*x+y*y)]];
    let best=[intrinsic,extrinsic,transpose(intrinsic),transpose(extrinsic)]
        .into_iter().map(|expected| error(actual,expected)).fold(f64::INFINITY,f64::min);
    assert!(best<=1e-12,"213_CONTRACT_MISMATCH: minimum matrix error = {best}");
}
