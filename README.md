# ORCID Toolbox

A web app built using the [Streamlit](https://streamlit.io/) framework offering several tools to interact with [ORCID](https://orcid.org) profiles.

Work in progress. Interface currently in French only.

## Installation

Install dependencies with

```
pip install -r requirements.txt
````

This project also depends on the [references-tractor](https://github.com/sirisacademic/references-tractor) library for named entity recognition, used to match references. However, `references-tractor` is currently not included in the pip registry. Also, since we're using internal helper functions from this library, it needs to be installed in editable mode.

Instead, install it manually by downloading or cloning the above linked repository inside the `lib` subfolder before building dependencies 
**in editable mode**:

```
cd lib
git clone https://github.com/sirisacademic/references-tractor.git
pip install -e references-tractor/. --prefer-binary
```

The `--prefer-binary` flag was necessary on my (older) Intel-based Mac, in order to prevent `pip` from trying to compile the required binaries from scratch, which was causing issues. Your mileage may vary.

It is also possible to run the application without installing `references-tractor`, this will simply disable the reference matching functionality.

## Running

Once all the dependencies have been installed, start the web app:

```
streamlit run app.py
```

The first time trying to match a list of references will take some time as the tokenizers will need to be installed first. It should be faster on later runs.

More details to come.