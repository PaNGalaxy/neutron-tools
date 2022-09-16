# ASRP's Single Peak Fit Tool

ASRP repo: https://code.ornl.gov/neutrons/ldrd-auto-refinement

# Developers

### Using conda

Spin up the environment (the default name of the environment is `single-peak-fit`)

```
conda env create --file environment.yaml
conda activate single-peak-fit
```

### Using conda in docker

This uses the RSE shared docker image for miniconda found in [this repo][rse_conda_image]

Build and run the container
```
docker login code.ornl.gov:4567
docker build -t single-peak-fit .
docker run -it single-peak-fit
```

To test quickly with docker, run:
```
docker build -t single-peak-fit . && docker run single-peak-fit pytest
```

[rse_conda_image]: https://code.ornl.gov/rse/images/miniconda3
