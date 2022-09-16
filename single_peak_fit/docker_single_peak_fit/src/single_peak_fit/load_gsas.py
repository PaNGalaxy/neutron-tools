import datetime
from mantid.simpleapi import (
    ConvertUnits,
    ConvertToPointData,
    LoadGSS,
    mtd,
)
from pathlib import Path
from typing import Union

FilePath = Union[Path, str]


def _wkspname(filename: Path) -> str:
    return filename.name.replace(".gsa", "").replace(".dat", "")


def load_gsas(
    filename: FilePath, units: str = "dSpacing", allowCaching: bool = False, unique=False
):  # TODO declare return
    """https://docs.mantidproject.org/nightly/algorithms/LoadGSS-v1.html
    https://docs.mantidproject.org/nightly/algorithms/ConvertUnits-v1.html"""
    filepath = Path(filename)
    wksp_name = _wkspname(filepath)

    if unique:
        # Unique workspace such that the workspace won't conflict with other worker
        now = datetime.datetime.now()
        time_stamp = f"_{now.second}{now.microsecond}"
        wksp_name += time_stamp
    elif mtd.doesExist(wksp_name):
        wksp_name += "n"

    if allowCaching and wksp_name in mtd:
        # TODO should check units
        wksp = mtd[wksp_name]
    else:
        try:
            wksp = LoadGSS(Filename=str(filepath), OutputWorkspace=wksp_name, UseBankIDasSpectrumNumber=True)
        except IndexError as index_err:
            logging.error(f"Failed to load {str(filepath)} to {wksp_name}")
            raise index_err
        except ValueError as value_err:
            logging.error(f"Failed to load {str(filepath)} to {wksp_name}")
            raise value_err
        wksp = ConvertUnits(InputWorkspace=wksp_name, OutputWorkspace=wksp_name, Target=units, EMode="Elastic")
        wksp = ConvertToPointData(InputWorkspace=wksp_name, OutputWorkspace=wksp_name)

    return wksp

