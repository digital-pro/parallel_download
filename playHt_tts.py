# Simplified interface to Play.Ht for translations

import os
import sys
import pandas as pd
import requests
from dataclasses import dataclass, replace


# Constants for API
API_URL = "https://api.play.ht/api/v1/convert"
STATUS_URL = "https://api.play.ht/api/v1/articleStatus"

input_file_name = 'item_bank_translations.csv'

# Trying to get save files co-erced into our desired path
audio_base_dir = "audio_files"

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def convert_tts(user_id, auth_token):
    """
    Convert text to speech using the Play.ht API.

    Args:
        transaction (TranscriptionTx): The transaction object containing the text, voice, and status.
        user_id (str): The user ID for authentication.
        auth_token (str): The authentication token.

    Returns:
        TranscriptionTx: The updated transaction object with the transcription ID and status.
    """
    headers = {
        'Authorization': auth_token,
        'X-USER-ID': user_id,
        'Accept': 'application/json',
        'Content-Type': 'application/json'
    }
    data = {
        "content": [transaction.text],
        "voice": transaction.voice,
        "title": "Individual Audio",
        "trimSilence": True
    }
    # logging.debug(f"convert_tts: submitting item={transaction.item_id}")
    response = requests.post(API_URL, headers=headers, json=data) # see https://docs.play.ht/reference/api-convert-tts-standard-premium-voices
    # What about success -- code 200?
    if response.status_code == 201:
        result = response.json()
        return replace(transaction, transcription_id=result['transcriptionId'], status='in_progress', resp_body=result)
    else:
        return replace(transaction, status='error', resp_body=f'NO RESPONSE (convert), status code={response.status_code}')


def main(
        input_file_path: str,
        lang_code: str,
        voice: str,
        user_id: str = None,
        api_key: str = None,
        output_file_path: str = None,
        item_id_column: str = 'item_id',
        audio_dir: str = None,
        # save_task_audio: str = None,  # saving audio only for specified task (e.g. 'theory-of-mind')
    ):
    """
    The main function to process the transcription jobs.

    Args:
        input_file_path (str): The path of the input CSV file where details of text and of past tts transactions are extracted.
        lang_code (str): A locale code, e.g.: 'es-CO' and the name for the column to select for tts transcription
        voice (str): The name of the play.ht voice to use, e.g.: 'es-CO-SalomeNeural'
        user_id (str, optional): The user ID for authentication. If not provided, it will be read from the environment variable 'PLAY_DOT_HT_USER_ID'.
        api_key (str, optional): The api key authenticating our API calls. If not provided, it will be read from the environment variable 'PLAY_DOT_HT_API_KEY'.
        overwrite_input_file_str (str, optional): A boolean string to indicate whether to overwrite the input file. Defaults to 'False'.
        output_file_path (str, optional): The path for the output CSV files to create and where to store the state of our transactions. Defaults to './snapshots_{user_id}/tts_{timestamp}_{user_id}.csv'
        item_id_column (str, optional): column name in the input file for stable and unique item ID. Defaults to 'item_id'.
        audio_dir (str, optional): The directory to store the audio files. Defaults to "audio_files/{lang_code}/".
    """

    if user_id is None:
        user_id = os.environ['PLAY_DOT_HT_USER_ID']
        if user_id is None:
            raise ValueError("user_id cannot be None")
    if api_key is None:
        api_key = os.environ['PLAY_DOT_HT_API_KEY']
        if api_key is None:
            raise ValueError("auth_token cannot be None")

    # Can't create destination folder for audio files yet
    # As we now want them to per task

    # basically we want to iterate through rows,
    # specifying the column (language) we want translated.
    # We assume that our caller has already massaged our input file as needed
    # columnts might be:
    # item_id,labels,en,es-CO,de,context

    inputData = pd.read_csv(input_file_path)

    # build API call
    for index, ourRow in inputData.iterrows():
        # for debugging
        print(ourRow)

        headers = {
            'Authorization': api_key,
            'X-USER-ID': user_id,
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }

        # We're assuming all the rows have the same columns
        translationNeeded = inputData.loc[index, lang_code]  # The name of the column you want to select
        data = {
            "content" : translationNeeded,
            "voice": voice,
            "title": "Individual Audio",
            "trimSilence": True
    }

    response = requests.post(API_URL, headers=headers, json=data) # see https://docs.play.ht/reference/api-convert-tts-standard-premium-voices


if __name__ == "__main__":
    main(*sys.argv[1:])

