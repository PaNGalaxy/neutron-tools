 #! /bin/bash

#docker run -it -v /var/run/docker.sock:/var/run/docker.sock \
#   -v /Users/adavitajain/Downloads/galaxy-tools/tools:/Users/adavitajain/Downloads/galaxy-tools/tools \
#   -v /tmp:/tmp \
#dummy-image planemo test --galaxy_root /galaxy --docker --tool_data_path /tmp --no_cleanup fractal.xml

 docker run -it -v /var/run/docker.sock:/var/run/docker.sock \
   -v /Users/adavitajain/Downloads/galaxy-tools/tools:/Users/adavitajain/Downloads/galaxy-tools/tools \
   -v /tmp/planemo:/tmp/planemo \
dummy-image


#docker run -it -v /var/run/docker.sock:/var/run/docker.sock \
#   -v `pwd`/tools:/galaxy-tools/tools \
#   -v `pwd`/tool_data:/galaxy-tools/tool_data \
#   --workdir /galaxy-tools/tools/neutrons \
#   -v /tmp:/tmp \
#dummy-image planemo test --galaxy_root /galaxy --docker --tool_data_path /tmp


