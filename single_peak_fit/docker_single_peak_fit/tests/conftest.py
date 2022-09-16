from pathlib import Path
import pytest


@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    here = Path(__file__).parent
    data_dir = here / "data"

    assert data_dir.exists()
    assert data_dir.is_dir()

    return data_dir


@pytest.fixture(name="fe2o3_gsas")
def fixture__fe2o3_gsas(test_data_dir: Path) -> Path:
    return test_data_dir / "NOM_Fe2O3_ramp_to_500K_at_temperature_95.05_K.gsa"
