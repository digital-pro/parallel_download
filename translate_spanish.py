import playDotHt_v2

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

# For testing don't co-host with Text Translation repo
input_file_path = "item_bank_translations.csv"
# put changes back into the levante-test repo
lang_code = 'es-ES'
#audio_dir = "c:/levante/levante-test/audio_files/{lang_code}/"
# for debugging
#audio_dir = "audio_files/"
voice = 'Conchita'

playDotHt_v2.main(input_file_path = input_file_path, lang_code = lang_code,
             voice=voice)

# IF we're happy with the output then
# gsutil rsync -d -r <src> gs://<bucket> 