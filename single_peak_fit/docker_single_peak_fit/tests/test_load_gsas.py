from pathlib import Path


from single_peak_fit import load_gsas


def test_load_gsas(fe2o3_gsas: Path) -> None:
    #data = load_gsas(filename=fe2o3_gsas, units="TOF", allowCaching=False, unique=True)
    data = load_gsas(filename="/app/tests/data/NOM_Fe2O3_ramp_to_500K_at_temperature_95.05_K.gsa", units="TOF", allowCaching=False, unique=True)
    assert data
    assert data.getNumberHistograms() == 6
    assert data.readX(0).shape == data.readY(0).shape
