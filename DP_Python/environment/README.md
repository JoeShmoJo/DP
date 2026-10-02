# Python environment

`environment.yml` here is a **draft** built from what the scripts import:

| Package | Used by |
|---|---|
| numpy, pandas | everything |
| matplotlib | QAQC plots (step 1) and result plots (step 2) |
| pydsstools | reading/writing obsData.dss |
| dataretrieval >= 1.3.0, cwms-python, requests, certifi | downloading (step 1) |

Create it with

    conda env create -f environment/environment.yml
    conda activate dp_python

## Replace it with the environment that is known to work

Once the process runs in your environment, save that environment here so
anyone can rebuild exactly it, then commit the file:

    conda env export --from-history -n <your env> > environment/environment.yml

or, for an exact (platform-specific) copy of every package:

    conda list --explicit -n <your env> > environment/spec-file.txt
    conda create -n dp_python --file environment/spec-file.txt

If pip packages are involved (pydsstools, dataretrieval, cwms-python), also
keep their versions:

    pip freeze > environment/requirements-pip.txt
