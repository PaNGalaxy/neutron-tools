docker run \
-t --name single_peak_fit_container \
--rm \
-v $(pwd):/portal \
single_peak_fit \
-f "/app/tests/data/NOM_Fe2O3_ramp_to_500K_at_temperature_95.05_K.gsa" \
-b 2 \
-c 11900 \
-l 11141 \
-r 12660
