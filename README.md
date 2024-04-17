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

Then you can run via `python <path_to_script> <argument1> <argument2>...`
Please refer to the main function docstring in the playDotHt_v1.py file for details about the behavior not mentioned here.

There is two modes for running the script, in both case the script will parse any existing transaction status from the input csv file, and resume the corresponding transaction where it was left off. This allows you to resume transcribing from a previous "snapshot", whether it was created by a previous run of the script or by you manually, it does not matter:
it only matters what the value for the `tts_{lang_code}_{voice}_status` and `tts_{lang_code}_{voice}_tx_id`columns are.
for instance when running the script for `es-co` and `es-CO-SalomeNeural`:
for a `tts_es-co_es-CO-SalomeNeural_status` colum value of `'pending'` or `'error'` or empty, we will request the tts audio
for a `tts_es-co_es-CO-SalomeNeural_status` colum value of `'in_progress'` we'll skip above steps and wait for the tts transcription to be completed
for a `tts_es-co_es-CO-SalomeNeural_status` colum value that starts with `'https://'` we'll skip above steps and start downloading the audio file right away
for a `tts_es-co_es-CO-SalomeNeural_status` colum value of any other value, we'll skip above steps and won't do anything

When a transaction is fully processed, the value for `tts_es-co_es-CO-SalomeNeural_status` is the path to the audio file (by defaults `./audio_files/{lang_code}/{item_id}.mp3`)

### Non-override mode
This is the mode by default. It dumps the status of the tts transactions to a new output file.
You can specify a specific file name via the optional `output_file_path` argument or let a default file be created at `./snapshots_{user_id}/tts_{timestamp}_{user_id}.csv`

e.g.:
```
python playDotHt_v1.py ./snapshots/previous_snapshot_to_resume.csv es-co es-CO-SalomeNeural 123456789 LKJHGFDSA
```
where...
- the first argument is the path to your input csv file
- the second and third arguments are the target column and the target Play.ht voice (respectively).
- the fourth and fifth are your Play.ht user_id and api_key arguments (respectively), you'll need to provide your own. You may omit these\two last arguments if you provide them via environment variables: `PLAY_DOT_HT_USER_ID` and `PLAY_DOT_HT_API_KEY` respectively

### Override mode

You call the script the same way as in the other mode. The difference is that you pass True for an additional `overwrite_input_file` argument.
This will cause the script to not create a new output file and instead dump the transaction statuses into the existing input csv file. 
e.g.:
```
python playDotHt_v1.py ./snapshots/previous_snapshot_to_resume.csv es-co es-CO-SalomeNeural myUserId myApiKey True"
```


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
