Right now this is harcoded to hit the v1 endpoints from Play.ht

## Installing script dependencies - environment setup

You will need python installed (python3 may be required, I'm not sure).
A requirements.txt file is provided.
To avoid polluting your other python projects' dependencies you may want to load up a virtual environment (`venv`) before installing the required packages:

```
python3 -m venv env
```
Then enter your venv, if on MacOS/Linux:
  ```
  source env/bin/activate
  ```
else on Windows:
```
.\env\Scripts\activate
```
Then install the dependencies via
```
pip install -r requirements.txt
```
You can later exit your venv whenever your done working in your project via:
```
deactivate
```
## Before running the script

!!! Careful !!! double check that your input csv file is properly prepared:
- are `<b>` or other formating tags present in the targeted column? perhaps you should target a duplicate of that column instead and remove the tags

## Running the script

If you have elected to install the requirements via a virtual environment, activate it via
`source env/bin/activate` on MacOS/Linux or `.\env\Scripts\activate` on Windows

Then you can run either `python <path_to_script> <argument1> <argument2>...`
e.g.:
```
python playDotHt_v1.py ./snapshots/last_snapshot.csv es-co es-CO-SalomeNeural 123456789 LKJHGFDSA
```
where...
- the first argument is the path to your input csv file
- the second and third arguments are the target column and the target Play.ht voice (respectively).
- the fourth and fifth are your Play.ht user_id and api_key arguments (respectively), you'll need to provide your own. You may omit these\two last arguments if you provide them via environment variables: `PLAY_DOT_HT_USER_ID` and `PLAY_DOT_HT_API_KEY` respectively

Please refer to the main function docstring in the playDotHt_v1.py file for details about the behavior and, if need be, for details about optional arguments not mentioned here.

## After you're done working on this project

If you have elected to install the requirements via a virtual environment, deactivate it via
`deactivate`

## TODOs

### TODO: absorb formating tags like `<b>`
### TODO: check if hidden rows in the google spreadsheet should be removed from input csv
### TODO: test override mode
### TODO: make detecting need for download more robust
### TODO: use an argument parser
### TODO: avoid reading and writing the entire file and update only the corresponding row
