# ORCID Toolbox

A web app built using the [Streamlit](https://streamlit.io/) framework offering several tools to interact with [ORCID](https://orcid.org) profiles.

Work in progress. Interface currently in French only.

## Installation

Install dependencies with

```
pip install -r requirements.txt
````

### Optional NER dependencies

The reference matching functionality requires named entity recognition (NER) capability.
The model used on this project is [Citation Parser](https://huggingface.co/SIRIS-Lab/citation-parser-ENTITY) 
by SIRIS Lab, either through HuggingFace and the `transformers` library or through SIRIS's 
[references-tractor](https://github.com/sirisacademic/references-tractor) library.
`references-tractor` is more powerful, as it includes a variety of steps developed by SIRIS to more accurately identify
references, but installing it is less straightforward.

The app is designed to revert to `transformers` if `references-tractor` is not available, or to fail gracefully
if neither library is available.

If you decide to use `references-tractor`, you will need it to install it manually **in editable mode**
to allow access to internal functions:

```
cd lib
git clone https://github.com/sirisacademic/references-tractor.git
pip install -e references-tractor/. --prefer-binary
```

The `--prefer-binary` flag was necessary on my (older) Intel-based Mac, in order to prevent `pip` from trying to compile the required binaries from scratch, which was causing issues. Your mileage may vary.

## Running

Once all the dependencies have been installed, start the web app:

```
streamlit run app.py
```

The first time trying to match a list of references will take some time as the tokenizers will need to be installed first. It should be faster on later runs.

More details to come.