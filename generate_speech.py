import playHt_tts
import pandas as pd
import os
import csv
import shutil
import urllib

"""
    To pass to the main function to process the transcription jobs.

    Args:
        input_file_path (str): The path of the input CSV file where details of text and of past tts transactions are extracted.
        lang_code (str): A locale code, e.g.: 'es-CO' and the name for the column to select for tts transcription
        voice (str): The name of the play.ht voice to use, e.g.: 'es-CO-SalomeNeural'
        user_id (str, optional): The user ID for authentication. If not provided, it will be read from the environment variable 'PLAY_DOT_HT_USER_ID'.
        api_key (str, optional): The api key authenticating our API calls. If not provided, it will be read from the environment variable 'PLAY_DOT_HT_API_KEY'.
        overwrite_input_file_str (str, optional): A boolean string to indicate whether to overwrite the input file. Defaults to 'False'.
        output_file_path (str, optional): The path for the output CSV files to create and where to store the state of our transactions. Defaults to './snapshots_{user_id}/tts_{timestamp}_{user_id}.csv'
        item_id_column (str, optional): column name in the input file for stable and unique item ID. Defaults to 'item_id'.
        rate_limit_per_minute (str, optional): The rate limit expected for the endpoint. Defaults to 50.
        audio_dir (str, optional): The directory to store the audio files. Defaults to "audio_files/{lang_code}/".
    """

# sometimes exports from Excel format add a "Sheet" entry before every row :(
def remove_sheet_rows(ourData):

        #for row in reader:
        #    if row and row[0].startswith('Sheet'):
        #        row[0] = row[0].split(',', 1)[-1]  # Remove 'Sheet' prefix
        #    writer.writerow(row)
        #shutil.move(outfile, infile)
    print("NULL")

# Retrieve translations.csv from the repo
# NOTE: If special characters get munged, will need to
#       arrange for an export/download directly from Crowdin
#
# For testing don't co-host with Text Translation repo
input_file_name = "item_bank_translations.csv"
diff_file_name = "needed_item_bank_translations.csv"

# Raw Github URL for translations uploaded from Crowdin
webURL = "https://raw.githubusercontent.com/digital-pro/levante-audio/main/translated.csv"

# Turn into dataframe so we can do any needed edits
# Pandas can now read directly from the web
# or if we need more control we could use requests

# or could read directly if no massaging needed
translationData = pd.read_csv(webURL)

# Current export from Crowdin has columns of
# identifier -> item_id
# labels -> task
# text -> en-US

# Columns that are okay
# es-CO OK
# de OK

# TBD: whether we want to write directly to the repo
#audio_dir = "c:/levante/levante-test/audio_files/{lang_code}/"

# Trying to get save files co-erced into our desired path
audio_base_dir = "audio_files"

# remove "Sheet" rows
#remove_sheet_rows(translationData)
# column edits to match what we need
translationData = translationData.rename(columns={'identifier': 'item_id'})
translationData = translationData.rename(columns={'text': 'en'})
#translationData = translationData.rename(columns={'labels': 'task'})

# We start with a baseline of None, but what if many prompts
# have already been translated. Can we start from there?
# That would involve reading in the previous version
# And looking for None, plus any new prompts in the current file

# we need to stash translation data, now or later
# NOTE: This is the full data -- write back to our file

# clean up the Sheet references in the Context column if they exist
translationData['context'] = translationData['context'].str.replace(r'\nSheet: translation-items-v1', '', regex=True)

translationData.to_csv(input_file_name)

# There is/may also be an existing .csv file (translation_master.csv)
if os.path.exists("translation_master.csv"):
    masterData = pd.read_csv("translation_master.csv")
else:
    # Create a "null state" translation status file
    # so that we know what needs to be generated
    masterData = translationData
    masterData['en'] = None
    masterData['es-CO'] = None
    masterData['de'] = None
    masterData.to_csv("translation_master.csv")
    # Create baseline masterData

# Now we have masterData & translationData




# Current play.ht voices for reference
# es-CO -- es-CO-SalomeNeural
# de -- VickiNeural
# en-US -- en-US-AriaNeural

# Hard-coded as a test 
# should get these as parameters
voice = 'es-CO-SalomeNeural'
lang_code = 'es-CO'

# options for all re-doing changed sources
# but also for redoing strings that haven't been translated
# maybe keep a pd/csv with a "translated" column?
changed_only = False
not_done_only = False # try true:)

# should we filter out just the ones we want here
# or inside the vendor specific code
# seems like here is the right idea

# we have our input.csv and our "master.csv" -- once it is created
# simple dropduplicates doesn't work because master.csv has real translation times
# or maybe it doesn't need to, and we could use shortcuts:
#   * check audio file for existence for "just new"
#   * compare the translation column for changes


playHt_tts.main(input_file_path = input_file_name, lang_code = lang_code,
             voice=voice, changed_only = changed_only, 
             audio_base_dir = audio_base_dir, not_done_only = not_done_only)

# IF we're happy with the output then
# gsutil rsync -d -r <src> gs://<bucket> 