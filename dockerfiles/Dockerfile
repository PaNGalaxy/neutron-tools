FROM savannah.ornl.gov/ndip/galaxy:24.1.dev3.ornl

RUN wget https://download.docker.com/linux/static/stable/x86_64/docker-24.0.2.tgz
RUN tar zxvf docker-24.0.2.tgz && cp docker/docker /usr/bin/docker

# Install dependencies for Planemo
RUN apt-get install -y python3-pip

# Install Planemo
RUN pip3 install planemo

COPY dockerfiles/dummy_tool.xml /tmp/dummy_tool.xml

# this may fail (and does fail for Galaxy 24.0.2, but it's ok - we only need to install dependencies)
RUN cd /tmp && planemo test --galaxy_root /galaxy /tmp/dummy_tool.xml || echo planemo failed, but ok

CMD ["bash"]

