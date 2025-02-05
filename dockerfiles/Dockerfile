FROM savannah.ornl.gov/ndip/galaxy/galaxy/dev:latest

RUN wget https://download.docker.com/linux/static/stable/x86_64/docker-24.0.2.tgz
RUN tar zxvf docker-24.0.2.tgz && cp docker/docker /usr/bin/docker

# Install dependencies for Planemo
RUN apt-get install -y python3-pip

# Install Planemo
RUN pip3 install planemo

COPY dockerfiles/dummy_tool.xml /tmp/dummy_tool.xml

RUN cd /tmp && planemo test --galaxy_root /galaxy /tmp/dummy_tool.xml

CMD ["bash"]

