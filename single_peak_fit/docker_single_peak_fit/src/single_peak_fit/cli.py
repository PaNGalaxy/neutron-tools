import argparse
import json
import load_gsas
from hack import MantidPeakAnalyzer
from pathlib import Path
from setup import GaussianProfile

# define a CLI
parser = argparse.ArgumentParser()


parser.add_argument( '-f', '--filename', \
                     help = 'name of gsas file to load', \
                     type =  str )

# Captain! These and all references can be thrown overboard
parser.add_argument( '-b', '--bank_id', \
                     help = 'index of the bank to use', \
                     type =  str )

parser.add_argument( '-c', '--center', \
                     help = 'peak center', \
                     type =  str )

parser.add_argument( '-l', '--xmin', \
                     help = 'xmin', \
                     type =  str )

parser.add_argument( '-r', '--xmax', \
                     help = 'xmax', \
                     type =  str )

# Captain! inputs: bank_id, left_bound=xmin, right_bound=xmax, 
'''
bank_id = 2
center = 11900
left_bound = 11141
right_bound = 12660
'''
# parse the command line
args = parser.parse_args()

print( f'Ahoy, Captain! filename: {args.filename}' )
print( f'Ahoy, Captain! bank_id: {args.bank_id}' )

bank_id = int(args.bank_id)
center = int(args.center)
left_bound = int(args.xmin)
right_bound = int(args.xmax)

# Load data file
'''
gsas_ws = \
load_gsas.load_gsas( \
filename="/app/tests/data/NOM_Fe2O3_ramp_to_500K_at_temperature_95.05_K.gsa", \
           units="TOF", \
           allowCaching=False, \
           unique=True )
'''
gsas_ws = \
load_gsas.load_gsas( \
filename=f'{args.filename}', \
           units="TOF", \
           allowCaching=False, \
           unique=True )

# Set workspace to peak analyzer
peak_analyzer = MantidPeakAnalyzer(gsas_ws)

# Set peak profile
peak_profile = GaussianProfile(unit="TOF", bank=bank_id, peak_name="LastPeak")
peak_profile.set_parameter_value("PeakCentre", center)
peak_profile.set_parameter_value("Sigma", 200)
peak_profile.set_parameter_value("Height", 0.1)
peak_profile.set_peak_range(center - left_bound, right_bound - center)

# Fit
effective, native = peak_analyzer.single_peak_analyzer(peak_profile, "Linear")

effective_list_name = "effective"

native_list_name = "native"

json_output = { effective_list_name : effective, native_list_name : native }

with open( '/portal/enpp.json', 'w' ) as output_file:

  output_file = json.dump( json_output, output_file )
