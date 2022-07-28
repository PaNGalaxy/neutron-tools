import pyoncat
import argparse
import os
import sys

ONCAT_URL = "https://oncat.ornl.gov"
BUFSIZ = 8192

def fix_ipts(input_string):
  if not input_string.upper().startswith("IPTS-"):
    return "IPTS-" + input_string
  return input_string

parser = argparse.ArgumentParser();
parser.add_argument("-i", "--instrument", type=str, required=True, help="Instrument name")
parser.add_argument("-f", "--facility", type=str, required=True, help="Facility name")
parser.add_argument("-I", "--ipts", type=str, help="IPTS number")
parser.add_argument("-r", "--run", type=str, help="Run number")
args = parser.parse_args();

oncat = pyoncat.ONCat(ONCAT_URL)

#experiment = oncat.Experiment.retrieve(args.ipts, facility=args.facility, instrument=args.instrument)
#print(experiment.get("indexed.run_number.ranges"))

projection = [
  "indexed.run_number",
  "path",
  "ext"
]

if not args.ipts:
  experiments = oncat.Experiment.list(facility=args.facility, instrument=args.instrument)
  for experiment in experiments:
    if experiment.get("title"):
      print("%s\t%s\t%s" % (experiment.get("name"), experiment.get("title"), experiment.get("")))
elif not args.run:
  datafiles = oncat.Datafile.list(experiment=fix_ipts(args.ipts), facility=args.facility, instrument=args.instrument, projection=projection, exts=[".nxs.h5"])
  for datafile in datafiles:
    print("%s\t%s" % (datafile.get("indexed.run_number"), datafile.get("location")))
else:
  datafiles = oncat.Datafile.list(experiment=fix_ipts(args.ipts), facility=args.facility, instrument=args.instrument, projection=projection, exts=[".nxs.h5"], ranges_q="indexed.run_number:" + args.run)
  if len(datafiles) != 1:
    print("Invalid run number")
    sys.exit(1)
  with open(datafiles[0].get("location"), 'rb') as f, os.fdopen(sys.stdout.fileno(), 'wb', closefd=False) as stdout:
    data = f.read(BUFSIZ)
    while data:
      stdout.write(data)
      stdout.flush()
      data = f.read(BUFSIZ)


