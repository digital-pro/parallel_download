To run the main script and/or test scripts, you may create a virtual environment and install the required packages using
the following commands from the project directory:
`python3 -m venv env`
`source env/bin/activate` on MacOS/Linux or `.\env\Scripts\activate` on Windows
`pip install -r requirements.txt`

Then you can run either `python <path_to_script> <argument1> <argument2>...`
e.g.:
`python playDotHt_v1.py ./snapshots/last_snapshot.csv es-co es-CO-SalomeNeural 123456789 LKJHGFDSA`
where...
- the first argument is the path to your input csv file
- the second and third arguments are the target column and the target Play.ht voice (respectively)
- the fourth and fifth are your Play.ht user_id and api_key arguments (respectively). You may omit these
two last arguments if you provide them via environment variables: `PLAY_DOT_HT_USER_ID` and `PLAY_DOT_HT_API_KEY` respectively

Please refer to the main function docstring in the playDotHt_v1.py file for details about the behavior and, if need be,
for details about optional arguments not mentioned here.

# TODO: avoid reading and writing the entire file and update only the corresponding row
# TODO make detecting need for download more robust
# TODO: use an argument parser
# TODO: test override mode