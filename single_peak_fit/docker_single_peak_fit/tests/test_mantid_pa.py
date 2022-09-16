import pytest
import json
from single_peak_fit import load_gsas
from single_peak_fit.mantid_peak_analysis import MantidPeakAnalyzer
from single_peak_fit.setup import GaussianProfile

# I need another file to test out the dspacing test,
# 


def test_nomad_gaussian_tof(fe2o3_gsas) -> None:
    """Test peak fitting on a NOMAD GSAS file"""

    # Load data file
    gsas_ws = load_gsas(filename=str(fe2o3_gsas), units="TOF", allowCaching=False, unique=True)

    # Set workspace to peak analyzer
    peak_analyzer = MantidPeakAnalyzer(gsas_ws)

    # Set peak profile
    # Captain! inputs: bank_id, left_bound=xmin, right_bound=xmax, 
    bank_id = 2
    center = 11900
    left_bound = 11141
    right_bound = 12660
    # Is 'TOF' the peak fitting type? It is a string...
    peak_profile = GaussianProfile(unit="TOF", bank=bank_id, peak_name="LastPeak")
    peak_profile.set_parameter_value("PeakCentre", center)
    peak_profile.set_parameter_value("Sigma", 200)
    peak_profile.set_parameter_value("Height", 0.1)
    peak_profile.set_peak_range(center - left_bound, right_bound - center)

    # Fit
    effective, native = peak_analyzer.single_peak_analyzer(peak_profile, "Linear")

    assert isinstance( effective, dict )

    assert isinstance( native, dict )

    # Verify result
    effective_gold = \
    {\
    "centre" : 11920.003690181315, \
    "width" : 393.00681154755404, \
    "height" : 2.0177138585360064, \
    "intensity" : 844.0960435976817, \
    "chi2" : 8.487343470607923 \
    }

    native_gold = \
    {\
    # A0: 0.011677744729330359
    # A1: 1.2291720876940528e-05
    "Height" : 2.0177138585360064, \
    "PeakCentre" : 11920.003690181315, \
    "Sigma": 166.89462635451142
    }

    # Effective parameters, with goodness of fit
    # Captain! Parameterize
    assert effective[ "height" ] == pytest.approx(effective_gold[ "height" ], rel=1e-3)
    assert effective[ "width" ] == pytest.approx(effective_gold[ "width" ], rel=1e-2)
    assert effective[ "centre" ] == pytest.approx(effective_gold[ "centre" ], rel=1e-3)
    assert effective[ "intensity" ] == pytest.approx(effective_gold[ "intensity" ], rel=1e-3)
    assert effective[ "chi2" ] == pytest.approx(effective_gold[ "chi2"] , rel=1e-3)

    # Native parameters:
    # Captain! Parameterize
    assert native[ "Height" ] == native_gold[ "Height" ]
    assert native[ "PeakCentre" ] == native_gold[ "PeakCentre" ]
    assert native[ "Sigma" ] == native_gold[ "Sigma" ]

    effective_list_name = "effective"

    native_list_name = "native"

    json_output = { effective_list_name : effective, native_list_name : native }

    with open( '/portal/enpp.json', 'w' ) as output_file:

      output_file = json.dump( json_output, output_file )

    #assert False

if __name__ == "__main__":

    pytest.main( [ __file__ ] )
