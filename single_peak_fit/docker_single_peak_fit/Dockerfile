FROM code.ornl.gov:4567/rse/images/miniconda3:4.11.0 as build

ARG CONDA_ENV=single-peak-fit
ENV PATH /opt/conda/envs/$CONDA_ENV/bin:$PATH

WORKDIR /app
RUN conda install -c conda-forge mamba
COPY environment.yaml .
RUN mamba env create --name $CONDA_ENV --file environment.yaml

ENV CONDA_DEFAULT_ENV $CONDA_ENV
RUN echo "conda activate $CONDA_ENV" >> ~/.bashrc

COPY . .

RUN mkdir /portal

VOLUME /portal

ENTRYPOINT [ "python", "/app/src/single_peak_fit/cli.py" ]
