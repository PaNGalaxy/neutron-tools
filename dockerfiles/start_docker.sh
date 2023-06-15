 #! /bin/bash

 docker run -it -v /var/run/docker.sock:/var/run/docker.sock \
   -v /Users/adavitajain/Downloads/galaxy-tools/tools:/Users/adavitajain/Downloads/galaxy-tools/tools \
   -v /tmp:/tmp \
dummy-image

#planemo test --galaxy_root /galaxy --docker --tool_data_path /tmp --no_cleanup fractal.xml