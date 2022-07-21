import pyoncat
import argparse

ONCAT_URL = "https://oncat.ornl.gov"

oncat = pyoncat.ONCat(ONCAT_URL)
instruments = oncat.Instrument.list(facility="SNS")
for i in instruments:
	print("%s,%s,%s,%s" % (i.get("facility"), i.get("full_name"), i.get("name"), i.get("short_name")))
instruments = oncat.Instrument.list(facility="HFIR")
for i in instruments:
	print("%s,%s,%s,%s" % (i.get("facility"), i.get("full_name"), i.get("name"), i.get("short_name")))
