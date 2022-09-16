from mantid.simpleapi import FitPeaks, DeleteWorkspace, mtd
from setup import PeakProfile
from typing import Tuple, Any


class MantidPeakAnalyzer(object):
    """This class is a facade to Mantid algorithm FitPeaks
    The initializer takes input of a xarray Dataset which may contain
    multiple DataArray's - each DataArray then contains a specific dataset
    to be analyzed with peak(s) analyzer defined in current class.
    """

    def __init__(self, workspace):
        """Initialization

        Parameters
        ----------
        workspace: workspace
            input data in Mantid workspace
        """
        self._workspace = workspace

    def single_peak_analyzer(self, peak_profile: PeakProfile, background_type) -> Tuple[Any, Any, Any]:
        """This method takes a specific key as input which will then be
        used to refer to one of the DataArray's contained in the Dataset
        passed through the initializer.

        Only a single peak will be analyzed with current method. Peak to
        be analyzed is specified by initial peak position, which should be
        provided with attrs of either the input Dataset or individual DataArray.
        If multiple peak positions are present, current method will take the
        first value in the list.
        """
        # Convert from Bank ID to workspace index
        ws_index = peak_profile.bank - 1

        # Output workspace setup
        peak_name = peak_profile.name
        position_ws_name = f"Positions_{self._workspace}_Bank{peak_profile.bank}_{peak_name}"
        param_table_name = f"Parameters_{self._workspace}_Bank{peak_profile.bank}_{peak_name}"
        calculated_ws_name = f"Model_{self._workspace}_Bank{peak_profile.bank}_{peak_name}"

        # Call FitPeaks
        optional_setup = dict()
        if peak_profile.peak_width_percentage is not None and peak_profile.peak_width_percentage > 0:
            optional_setup["PeakWidthPercent"] = peak_profile.peak_width_percentage

        param_names, param_values = peak_profile.get_parameter_values(ignore_non_set=True)

        print(peak_profile.position, peak_profile.range)
        FitPeaks(
            InputWorkspace=self._workspace,
            StartWorkspaceIndex=ws_index,
            StopWorkspaceIndex=ws_index,
            PeakCenters=[peak_profile.position],
            FitFromRight=True,
            HighBackground=True,
            PeakFunction=peak_profile.peak_type,
            BackgroundType=background_type,  # example Linear
            FitWindowBoundaryList=[
                peak_profile.position - peak_profile.range[0],
                peak_profile.position + peak_profile.range[1],
            ],
            PeakParameterNames=param_names,
            PeakParameterValues=param_values,
            OutputWorkspace=position_ws_name,
            OutputPeakParametersWorkspace=param_table_name,
            FittedPeaksWorkspace=calculated_ws_name,
            PeakWidthPercent=0.01,
            RawPeakParameters=False,
        )

        # Set up the output
        param_table_ws = mtd[param_table_name]
        assert param_table_ws
        col_names = param_table_ws.getColumnNames()
        param_dict = dict()
        for col_index, col_name in enumerate(col_names):
            param_value = param_table_ws.cell(0, col_index)
            param_dict[col_name] = param_value

        # Set values to peak_profile
        # ['wsindex', 'peakindex', 'centre', 'width', 'height', 'intensity', 'A0', 'A1', 'chi2']
        peak_profile.set_fitted_effective_parameters(
            center=param_dict["centre"],
            height=param_dict["height"],
            intensity=param_dict["intensity"],
            width=param_dict["width"],
        )
        peak_profile.set_fitting_goodness(chi2=param_dict["chi2"])

        # Captain! Parameterize these
        effective = dict()
        effective[ "centre" ] = param_dict["centre"]
        effective[ "height" ] = param_dict["height"]
        effective[ "intensity" ] = param_dict["intensity"]
        effective[ "width" ] = param_dict["width"]
        effective[ "chi2" ] = param_dict["chi2"]

        calculated_ws = mtd[calculated_ws_name]
        assert calculated_ws
        model_data = calculated_ws.readX(ws_index), calculated_ws.readY(ws_index), self._workspace.readY(ws_index)

        # Clean up
        for ws_name in position_ws_name, param_table_name, calculated_ws_name:
            DeleteWorkspace(Workspace=ws_name)

        # Fit the peak for the second time for native profile parameters
        FitPeaks(
            InputWorkspace=self._workspace,
            StartWorkspaceIndex=ws_index,
            StopWorkspaceIndex=ws_index,
            PeakCenters=[peak_profile.position],
            FitFromRight=True,
            HighBackground=True,
            PeakFunction=peak_profile.peak_type,
            BackgroundType=background_type,  # example Linear
            FitWindowBoundaryList=[
                peak_profile.position - peak_profile.range[0],
                peak_profile.position + peak_profile.range[1],
            ],
            PeakParameterNames=param_names,
            PeakParameterValues=param_values,
            OutputWorkspace=position_ws_name,
            OutputPeakParametersWorkspace=param_table_name,
            FittedPeaksWorkspace=calculated_ws_name,
            PeakWidthPercent=0.01,
            RawPeakParameters=True,
        )

        # Set up the output
        param_table_ws = mtd[param_table_name]
        assert param_table_ws
        col_names = param_table_ws.getColumnNames()
        print(f"------>  {col_names}")

        param_dict = dict()

        for col_index, col_name in enumerate(col_names):
            param_value = param_table_ws.cell(0, col_index)
            param_dict[col_name] = param_value

        native = dict()

        for param_name, parameter in peak_profile.get_parameters().items():
            native[ param_name ] = param_dict[ param_name ]
            parameter.set_fitted_value(param_dict[param_name], 1.0)

        # Clean up
        for ws_name in position_ws_name, param_table_name, calculated_ws_name:
            DeleteWorkspace(Workspace=ws_name)

        return effective, native




















