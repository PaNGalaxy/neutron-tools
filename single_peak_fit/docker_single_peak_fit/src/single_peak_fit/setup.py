"""
Classes and methods for peak fitting setup

Design pattern for PeakProfile:
- creation pattern: Factory
"""
from typing import Union, List, Dict, Tuple
from pathlib import Path
from abc import ABC, abstractmethod

import numpy as np


class Parameter(object):
    """Data object for a native parameter of a peak profile considering fitting"""

    def __init__(self, value: float, lower: Union[None, float], upper: Union[None, float], error: Union[float, None]):
        # value
        self._value: float = value
        # fitting setup
        self._init_value = value
        self._lower_boundary = lower
        self._upper_boundary = upper
        # fitting result
        self._fit_error: Union[float, None] = error

    @property
    def value(self):
        return self._value

    def set_init_value(self, value: float):
        self._value = value
        self._init_value = value

    def set_fitted_value(self, value: float, error: float):
        self._value = value
        self._fit_error = error

    def set_from_dict(self, param_dict):
        for key in param_dict:
            # some other values
            private_name = f"_{key}"
            setattr(self, private_name, param_dict[key])


class PeakProfile(ABC):
    """
    Description of a single peak's profile including all information about its profile parameters.

    An individual PeakProfile instance is to describe one peak on one bank
    """

    def __init__(self, unit: str, bank: int, parameter_names: List[str], peak_name: str = ""):
        """Initialization"""
        # Base abstract
        self._peak_type = None
        # peak type
        self._name = peak_name
        self._unit = unit
        self._bank = bank
        # chi^2
        self._chi2 = None
        # peak profile
        self._parameters: Dict[str, Union[Parameter, None]] = dict()
        for par_name in parameter_names:
            self._parameters[par_name] = None
        # effective peak profile
        self._effective_center = None
        self._effective_intensity = None
        self._effective_width = None
        self._effective_height = None
        # Other parameters
        self._peak_range: Tuple[float, float] = (None, None)
        self._peak_width_percentage: float = -10e9  # optional.  negative value is not physical

    @property
    def bank(self) -> int:
        return self._bank

    @property
    def name(self) -> str:
        """Get peak name

        If user does not give name, use a generic name 'Peak'
        """
        if len(self._name) > 0:
            return self._name
        else:
            return "Peak"

    @property
    def unit(self) -> str:
        return self._unit

    @property
    def peak_type(self):
        return self._peak_type

    @abstractmethod
    def position(self) -> float:
        return np.Inf

    @property
    def height(self):
        return self._effective_height

    @property
    def width(self):
        return self._effective_width

    @property
    def intensity(self):
        return self._effective_intensity

    @property
    def chi2(self):
        return self._chi2

    @property
    def width_limit(self) -> float:
        return self._width

    @property
    def peak_width_percentage(self) -> float:
        return self._peak_width_percentage

    @peak_width_percentage.setter
    def peak_width_percentage(self, value: float):
        self._peak_width_percentage = value

    @property
    def range(self):
        return self._peak_range

    def set_peak_range(self, left_range, right_range):
        self._peak_range = left_range, right_range

    def get_parameters(self) -> Dict[str, Parameter]:
        """Get the references to all the parameters in list"""
        return self._parameters

    def get_parameter_values(self, ignore_non_set=False) -> Tuple[List[str], List[float]]:
        """
        Get the values of all parameter values with names

        Returns
        -------
        tuple
            parameter names (list) and parameter values (list) corresponding in position

        """
        par_names = list()
        par_values = list()
        for par_name in sorted(list(self._parameters.keys())):
            if self._parameters[par_name] is not None:
                par_names.append(par_name)
                par_values.append(self.get_parameter_value(par_name))
            elif not ignore_non_set:
                raise KeyError(f"Parameter {par_name} has not been set up.")

        return par_names, par_values

    def get_parameter_value(self, name: str) -> float:
        if name not in self._parameters:
            raise KeyError(f"Parameter {name} is not a valid one")
        elif self._parameters[name] is None:
            raise RuntimeError(f"Parameter {name} has not been specified yet")

        return self._parameters[name].value

    def get_effective_parameters(self) -> Tuple[float, float, float]:
        """Get effective peak parameters: center, intensity and width"""
        return self._effective_center, self._effective_intensity, self._effective_width

    def set_parameter_value(self, name: str, value: float):
        """Set parameter value

        Parameters
        ----------
        name: str
            name must be
        value

        Returns
        -------

        """
        # Init parameter
        if self._parameters[name] is None:
            self._parameters[name] = Parameter(value, None, None, None)

        # If the value has been set up before, then this time, the value only affect initial value
        self._parameters[name].set_init_value(value)

    def set_from_dict(self, peak_dict):
        """Set the peak profile from a dictionary

        Rule:
        - key in dictionary: some_name will be set to self._some_name

        Parameters
        ----------
        peak_dict: dict
            parameters are saved in a dictionary

        """
        for key in peak_dict:
            if key == "parameters":
                # parameters is a special one
                param_dict = peak_dict[key]
                for par_name in param_dict:
                    # Set up a peak profile parameter that is refinable
                    self._parameters[par_name] = Parameter(None, None, None, None)
                    self._parameters[par_name].set_from_dict(param_dict[par_name])
            else:
                # some other values
                private_name = f"_{key}"
                setattr(self, private_name, peak_dict[key])

    def set_fitted_effective_parameters(self, center: float, height: float, width: float, intensity: float):
        """
        Set the values for effective peak parameters from fitting result
        """
        self._effective_center = center
        self._effective_width = width
        self._effective_height = height
        self._effective_intensity = intensity

    def set_fitting_goodness(self, chi2: float):
        self._chi2 = chi2


class GaussianProfile(PeakProfile):
    """
    Gaussian profile
    """

    def __init__(self, unit: str, bank: int, peak_name: str = ""):
        """
        Initialization
        """
        parameter_names = ["Height", "PeakCentre", "Sigma"]
        super(GaussianProfile, self).__init__(unit, bank, parameter_names, peak_name)
        self._peak_type = "Gaussian"

    @property
    def position(self) -> float:
        if "PeakCentre" not in self._parameters:
            raise KeyError(
                f"PeakCentre is not a profile parameter.  Supported parameters are " f"{list(self._parameters.keys())}"
            )
        if self._parameters["PeakCentre"] is None:
            raise ValueError("PeakCentre is not set up with value yet")
        return self._parameters["PeakCentre"].value


class GenericProfile(PeakProfile):
    """
    Description of a single peak's profile including all information about its profile parameters.

    An individual PeakProfile instance is to describe one peak on one bank
    """

    def __init__(
        self, unit: str, bank: int, parameter_names: List[str], peak_name: str = "", peak_type: str = "generic"
    ):
        """Initialization"""
        super(GenericProfile, self).__init__(unit, bank, parameter_names, peak_name)
        self._peak_type = peak_type
        self._peak_pos_param_name = ""

    def set_peak_position_parameter_name(self, peak_pos_name: str):
        """Set the parameter name for peak position/center"""
        if peak_pos_name not in self._parameters:
            raise TypeError(
                f"Peak position/center parameter name {peak_pos_name} is not a valid peak parameter "
                f"name.  Candidates: {list(self._parameters.keys())}"
            )

        self._peak_pos_param_name = peak_pos_name

    @property
    def position(self) -> float:
        return self._parameters[self._peak_pos_param_name].value


class PeakProfileFactory(object):
    @staticmethod
    def create_mantid_builtin_peak_profile(peak_name: str, peak_type: str) -> PeakProfile:
        """
        Create a specific non-abstract PeakProfile in Mantid
        Parameters
        ----------
        peak_name: str
            name of the peak
        peak_type: str
            type of peak: Gaussian, Generic

        """
        if peak_type.lower() == "gaussian":
            # Gaussian peak profile
            profile = GaussianProfile(None, -1, peak_name)
        else:
            # Name not identified
            raise NameError(f"Peak type {peak_type} has not builtin PeakProfile.")

        return profile

    @staticmethod
    def create_generic_peak_profile(
        peak_name: str, peak_type: str, parameter_names: List[str], peak_pos_param_name: str
    ) -> GenericProfile:
        """
        Create a specific non-abstract Generic PeakProfile that is defined in ASRP

        Parameters
        ----------
        peak_name: str
            name of the peak
        peak_type: str
            type of peak: Gaussian, Generic
        parameter_names: list
            parameter names
        peak_pos_param_name: str
            name of the parameter for peak position/center

        """
        profile = GenericProfile(None, -1, parameter_names, peak_name, peak_type)
        profile.set_peak_position_parameter_name(peak_pos_param_name)

        return profile


class PeakFitSetup(object):
    """
    Peak fitting setup
    """

    def __init__(self):
        self._source_file_path: Union[str, Path, None] = None
