extern crate crypto;
pub mod imple;

use imple::time;
use pyo3::prelude::*;

#[pyfunction]
fn from_duration(secs: usize, mut nanos: u32) -> PyResult<String> {
    if let None = Some(nanos) {
        nanos = 0
    }

    let duration = &std::time::Duration::new(secs as u64, nanos);
    let rest = time::duration_to_humatime(*duration);
    Ok(rest)
}

#[pyfunction]
fn to_iso(stamp: u64) -> PyResult<String> {
    Ok(time::timestamp_to_iso(stamp))
}

#[pyfunction]
fn sum(a: usize, b: usize) -> PyResult<usize> {
    Ok(a + b)
}

#[pymodule]
fn rst(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(pyo3::wrap_pyfunction!(sum, m)?)?;
    m.add_function(pyo3::wrap_pyfunction!(from_duration, m)?)?;
    m.add_function(pyo3::wrap_pyfunction!(to_iso, m)?)?;
    Ok(())
}