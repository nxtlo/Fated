use pyo3::prelude::*;


#[pyfunction]
fn sum(a: usize, b: usize) -> PyResult<usize> {
    Ok(a + b)
}

#[pymodule]
fn rst(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(pyo3::wrap_pyfunction!(sum, m)?)?;
    Ok(())
}