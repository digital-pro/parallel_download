from abc import abstractmethod
import os
import threading
import time
from typing import List
import pandas as pd
import requests
import logging
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Constants for API
API_URL = "https://api.play.ht/api/v1/convert"
STATUS_URL = "https://api.play.ht/api/v1/articleStatus"

USER_ID = 'nC0fElwpIcMhZUFoTLBM98gHVy43'
AUTH_TOKEN = ''

def create_directory(path):
    if not os.path.exists(path):
        os.makedirs(path)
    return path


################################################
# API helper methods
################################################

@dataclass(frozen=True)
class TranscriptionTx:
    """
    This immutable dataclass represents a transaction to convert text to speech
    It carries two types of data:
        the data necessary to make the API calls on Play.ht, see https://docs.play.ht/reference/api-convert-tts-standard-premium-voices
        the data we use internally to track the status of the transaction
    """
    voice: str
    item_id: str
    text: str
    transcription_id: str = None
    # below are the data we use internally to track the status of the transaction
    status: str = 'pending'  # pending, in_progress, error, <audio_file_url> - pending means not yet submitted for conversion
    resp_body: str = None # dump of the response body

def convert_tts(transaction: TranscriptionTx, user_id, auth_token) -> TranscriptionTx:
    """
    Convert text to speech using the Play.ht API.

    Args:
        transaction (TranscriptionTx): The transaction object containing the text, voice, and status.
        user_id (str): The user ID for authentication.
        auth_token (str): The authentication token.

    Returns:
        TranscriptionTx: The updated transaction object with the transcription ID and status.
    """
    if transaction.status not in ['pending', 'error']:
        return transaction  # Skip jobs that are already completed or in progress.
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
    response = requests.post(API_URL, headers=headers, json=data)
    if response.status_code == 200:
        result = response.json()
        return replace(transaction, transcription_id=result['transcriptionId'], status='in_progress', resp_body=result)
    else:
        logging.error(f"convert_tts: code={response.status_code}, error={result['error']}")
        return replace(transaction, status='error')

def check_status(transaction: TranscriptionTx, user_id, auth_token) -> TranscriptionTx:
    """
    Check the status of a transcription transaction.

    Args:
        transaction (TranscriptionTx): The transaction object containing the transcription ID and status.
        user_id (str): The user ID for authentication.
        auth_token (str): The authentication token.

    Returns:
        TranscriptionTx: The updated transaction object with the status and audio URL if the transcription is completed.
    """
    if transaction.status not in ['in_progress']:
        return transaction
    if not transaction.transcription_id:
        raise Exception("No transcription ID, aborting")

    headers = {
        'Authorization': auth_token,
        'X-USER-ID': user_id,
        'Accept': 'application/json'
    }
    response = requests.get(f"{STATUS_URL}?transcriptionId={transaction.transcription_id}", headers=headers)
    if response.status_code == 200:
        result = response.json()
        if result.get('error', False): # some error may not mean that the transaction failed !!! #TODO figure out how to distinguish unrecoverable errors
            logging.error(f"check_status: errorMessage={result['errorMessage']}")
            return replace(transaction, status='error', resp_body=result)
        if result.get('converted', False):
            return replace(transaction, status=result['audioUrl'], resp_body=result)
        else:
            return transaction
    else:
        logging.error(f"check_status: status_code={response.status_code}")
        return replace(transaction, resp_body=f'{response.status_code}') # we should not assume that the transaction failed


################################################
# Transactions Status Persistence
################################################

class StatusDataStore:
    @abstractmethod
    def __init__(self, input_file: str):
        if input_file is None:
            raise ValueError("input file cannot be None")
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"input file '{input_file}' not found")
        self.input_file = input_file
        pass
    @abstractmethod
    def extract_transactions(self, lang_code: str, voice: str) -> List[TranscriptionTx]:
        pass
    @abstractmethod
    def persist_tx_status(self, transaction: TranscriptionTx) -> None:
        pass

class CsvManager(StatusDataStore):
    """
    A class to manage the output CSV files.
    The expected columns related to tts transactions follow the following pattern:
    'tts_{self.lang_code}_{self.voice}_{column_name}'
    """

    @dataclass(frozen=True)
    class LockedOutputFile:
        lock: threading.Lock
        filepath: str

    def __init__(self, input_file, item_id_column):
        super().__init__(input_file)
        self.item_id_column = item_id_column
        self.lock = threading.Lock()
        self.locked_output_file = None
        self.overwrite_input_file = False

    def set_csv_output_file(self, output_file_name: str, tx_columns: List[str]):
        """
        Instructs the store to write transaction statuses to a new specific csv file
        """
        if self.overwrite_input_file is True:
            raise ValueError("set_csv_output_file: input file overwriting is enabled, aborting")
        if output_file_name is None:
            raise ValueError("set_csv_output_file: output file cannot be None, aborting")
        elif os.path.exists(output_file_name):
            errorMessage = f"set_csv_output_file: '{output_file_name}' already exists, aborting."
            logging.error(errorMessage)
            raise FileExistsError(errorMessage)
        
        self.locked_output_file = CsvManager.LockedOutputFile(self.lock, output_file_name)

    def set_overwrites_csv_input_file(self, overwrite_input_file: bool, tx_columns: List[str]):
        """
        Instructs the store to write transaction statuses to the input csv file
        """
        if self.locked_output_file is not None:
            raise ValueError("set_overwrites_csv_input_file: output file was set, aborting")

        self.overwrite_input_file = overwrite_input_file
        self.locked_output_file = CsvManager.LockedOutputFile(self.lock, self.input_file)

    def set_target_locale_and_voice(self, lang_code, voice):
        """
        Instructs the store to prepare for writing transaction statuses for a specific locale and voice.

        To avoid duplicating the column header row when writing a transaction status, we
        here ensure the columns exist in the output csv ahead of processing the transactions
        """
        if self.locked_output_file is None:
            raise ValueError("set_target_locale_and_voice: output not set, aborting")
        
        # assign the locale and voice to our instance
        self.lang_code = lang_code
        self.voice = voice
        #  Ensure the columns exist in the output CSV file
        with self.locked_output_file.lock:
            tx_columns = CsvManager.get_tx_columns(lang_code=lang_code, voice=voice)
            ensure_columns_in_csv(csv_file=self.locked_output_file.filepath, columns=tx_columns)

    def parse_input_file(input_file_path: str, required_columns: List[str], tx_columns: List[str]) -> pd.DataFrame:
        """
        Parse the transactions info from input file into a DataFrame.

        Args:
            input_file_path (str): The path of the input file.
            required_columns (List[str]): A list of column names that are required in the input file.
            tx_columns (List[str]): A list of column names for the transaction status.
        Returns:
            pd.DataFrame: The parsed DataFrame.

        Raises:
            Exception: If any of the required columns are missing in the input file.
        """
        logging.info(f"parse_input_file: requiring columns={required_columns}")
        data_frame = pd.read_csv(input_file_path)
        # validate required columns
        for col in required_columns:
            if col not in data_frame.columns:
                errorMessage = f"parse_input_file: Missing column '{col}', aborting."
                logging.error(errorMessage)
                raise Exception(errorMessage)
        # add tx columns if they do not exist
        for col in tx_columns:
            if col not in data_frame.columns:
                data_frame[col] = None
        return data_frame
    
    def extract_transactions(self) -> List[TranscriptionTx]:
        tx_columns = CsvManager.get_tx_columns(lang_code=self.lang_code, voice=self.voice)
        data_frame = self.parse_input_file(self.input_file_path, [self.item_id_column, self.lang_code], tx_columns)
        if data_frame is None:
            errorMessage = f"extract_transactions: could not parse input file, aborting"
            logging.error(errorMessage)
            raise Exception(errorMessage)
        transactions_from_input = CsvManager.extract_transactions_from_df(
            df=data_frame,
            item_id_column=self.item_id_column,
            lang_code=self.lang_code,
            voice=self.voice,
            )
        #TODO perhaps log this snapshot to a text file
        return transactions_from_input
    
    def extract_transactions_from_df(df: pd.DataFrame, item_id_column: str, lang_code: str, voice: str) -> List[TranscriptionTx]:
        transactions = []
        for _, row in df.iterrows():
            transaction = CsvManager.df_row_to_transcription_tx(row=row, item_id_column=item_id_column, lang_code=lang_code, voice=voice)
            transactions.append(transaction)
        return transactions

    def persist_tx_status(self, transaction: TranscriptionTx):
        """
        Persists the status of a transcription transaction to the output csv file.
        It does so behind a lock to avoid concurrent writes from multiple threads and corrupting the file.
        """
        locked_output_file = self.locked_output_file
        if self.overwrite_input_file is True:
            if locked_output_file is not None:
                if locked_output_file.filepath is self.input_file:
                    logging.warn("persist_tx_status: no need to specify output file path when opting to overwrite input file")
                else:
                    errorMsg = f"persist_tx_status: aborting, input file overwriting is enabled but output file is set to '{locked_output_file.filepath}'"
                    logging.error(errorMsg)
                    raise Exception(errorMsg)
            logging.info("persist_tx_status: Input file will be overwritten")
            locked_output_file = CsvManager.locked_output_file(self.lock, self.input_file)
        else:
            if locked_output_file is None:
                errorMsg = f"persist_tx_status: no output file set, aborting"
                logging.error(errorMsg)
                raise Exception(errorMsg)
            elif locked_output_file.filepath is self.input_file:
                errorMsg = f"persist_tx_status: output file is the same as input file, aborting"
                logging.error(errorMsg)
                raise Exception(errorMsg)

        df = pd.read_csv(self.input_file)
        df = CsvManager.dump_tx_status_to_df(transaction, df, self.item_id_column)
        with locked_output_file.lock:
            CsvManager.persist_df_to_csv(transaction, df, self.item_id_column, df)

    def persist_df_to_csv(df: pd.DataFrame, output_csv_file):
        """
        DO NOT USE THIS FUNCTION DIRECTLY. USE persist_tx_status(transaction: TranscriptionTx) INSTEAD.
        Writing to the CSV file is not inherently thread-safe and concurrent writes from multiple threads will corrupt the file.
        """
        # write to file
        df.to_csv(
            output_csv_file,
            mode='w',
            index=False,
            header=False, # !!! ATTENTION: Note that we assume all headers have already been written !!!
            #encoding='utf-8', #TODO check if this is necessary. Google docs export to csv likely uses utf-8
            )

    # def append_to_output(self, data: pd.DataFrame):
    #     """
    #     Appends the given DataFrame to the CSV file in our CsvManager attributes. This to avoid multiple threads
    #     writing concurrently and corrupting the file.

    #     Args:
    #         data (pd.DataFrame): The DataFrame to be appended.

    #     Returns:
    #         None
    #     """
    #     return self.append_to_output_csv(self.LockedOutputFile, data)

    # def append_to_output_csv(locked_output_file: LockedOutputFile, data: pd.DataFrame):
    #     """
    #     Appends the given DataFrame to a CSV file behind a lock. This to avoid multiple threads
    #     writing concurrently and corrupting the file.

    #     Args:
    #         locked_output_file (LockedOutputFile) the locked file to write to
    #         data (pd.DataFrame): The DataFrame to be appended.

    #     Returns:
    #         None
    #     """
    #     with locked_output_file.lock:
    #         data.to_csv(
    #             locked_output_file.filepath,
    #             mode='a', # Append mode
    #             index=False, # Do not write the index name
    #             header=not pd.read_csv(locked_output_file.filepath).empty # Only write header if the file is empty
    #             )

    ## HELPER FUNCTIONS
    def df_row_to_transcription_tx(row: pd.Series, item_id_column, lang_code: str, voice: str) -> TranscriptionTx:
        """
        Parse a TranscriptionTx object from a given data frame row.
        
        !!! Important: Note that `lang_code` and `voice` parameters are also used to derive the expected transaction status column names.

        Args:
            row (pd.Series): The DataFrame row to parse.
            item_id_column (str): The column name for a stable item ID.
            lang_code (str): The locale code to select the column for the text to be transcribed.
            voice (str): The name to select the voice for the transcription.
        """
        return TranscriptionTx(
            voice=voice,
            item_id=            row[item_id_column],
            text=               row[lang_code],
            #TODO make these below more dynamic in case tx_columns are changed
            transcription_id=   row[CsvManager.get_tx_id_column(lang_code=lang_code, voice=voice)],
            status=             row[CsvManager.get_tx_status_column(lang_code=lang_code, voice=voice)],
            resp_body=          row[CsvManager.get_tx_details_columns(lang_code=lang_code, voice=voice)],
            )

    def dump_tx_status_to_df(transaction: TranscriptionTx, df: pd.DataFrame, item_id_column: str) -> pd.DataFrame:
        df.loc[
            df[item_id_column] == transaction.item_id,
            CsvManager.get_tx_columns(lang_code=transaction.lang_code, voice=transaction.voice)
        ] = transaction.transcription_id, transaction.status, transaction.resp_body #TODO make this dynamic in case tx_columns are changed
        return df

    def format_tx_column(lang_code, voice, column_name):
        return f'tts_{lang_code}_{voice}_{column_name}'

    def get_tx_id_column(lang_code, voice):
        return CsvManager.format_tx_column(lang_code, voice, 'tx_id')

    def get_tx_status_column(lang_code, voice):
        return CsvManager.format_tx_column(lang_code, voice, 'status')

    def get_tx_details_columns(lang_code, voice):
        return CsvManager.format_tx_column(lang_code, voice, 'details')

    def get_tx_columns(lang_code, voice):
        return [
            CsvManager.get_tx_id_column(lang_code, voice),
            CsvManager.get_tx_status_column(lang_code, voice),
            CsvManager.get_tx_details_columns(lang_code, voice),
            ]

    def ensure_columns_in_csv(csv_file: str, columns: list):
        # If the file exists, read it
        if os.path.isfile(csv_file):
            df = pd.read_csv(csv_file)
        else:
            # If the file doesn't exist, create an empty DataFrame
            df = pd.DataFrame()

        # Ensure the columns exist in the DataFrame
        for column in columns:
            if column not in df.columns:
                df[column] = None

        # Write the DataFrame to the CSV file
        df.to_csv(csv_file, index=False)

################################################
# DRIVER CODE
################################################

def process_transactions(transactions: List[TranscriptionTx], status_data_store: StatusDataStore, user_id, auth_token, rate_limit_per_minute):
    def process(transaction):
        transaction = convert_tts(transaction, user_id, auth_token)
        status_data_store.persist_tx_status(transaction) # persist tx status
        transaction = check_status(transaction, user_id, auth_token)
        status_data_store.persist_tx_status(transaction)  # persist tx status
        time.sleep(rate_limit_interval)  #TODO: implement real rate limiting


    rate_limit_interval = 60 / rate_limit_per_minute
    with ThreadPoolExecutor(max_workers=10) as executor:
        # futures = [executor.submit(convert_tts, transaction, user_id, auth_token) for transaction in transactions]
        # for future in futures:
        #     transaction = future.result()
        #     time.sleep(rate_limit_interval)  # Manage rate limiting
        #     transaction = check_status(transaction, user_id, auth_token)
        #     df.loc[
        #         df[item_id_column] == transaction.item_id,
        #         [tx_id_column, tx_status_column, tx_details_columns]
        #     ] = transaction.transcription_id, transaction.status, transaction.resp_body
        executor.map(process, transactions)

def setup_csvmanager_status_store(input_file_path, output_file_path, user_id, overwrite_input_file: bool, item_id_column) -> StatusDataStore:
    # create our CsvManager instance
    csv_status_store = CsvManager(input_file_path, item_id_column)
    # setup the destination for persisting the status of our tts transactions 
    if overwrite_input_file is True:
        if output_file_path is not None:
            if output_file_path is not input_file_path:
                errorMsg = f"Conflicting parameters: output file cannot be used when overwriting input file"
                logging.error(errorMsg)
                raise Exception(errorMsg)
            else:
                logging.warning(f"no need to specify output file path when opting to overwrite input file")
        logging.info(f"!!! ATTENTION !!! input csv file will be overwritten")
        # we do not call set_output_file() but opt to overwrite the csv input file instead
        csv_status_store.set_overwrites_csv_input_file(True)
    else:
        if output_file_path is None: # we need to create an output csv file since none was provided
            timestamp = datetime.now(datetime.UTC).strftime('%Y%m%d%H%M%S')
            output_filepath = f"tts_{timestamp}_{user_id}.csv"
            logging.info(f"no output file specified: creating output file as {output_filepath}")
        csv_status_store.set_csv_output_file(output_filepath)
    return csv_status_store

def main(input_status_snapshot, lang_code, voice, user_id, auth_token, item_id_column='item_id', overwrite_input_snapshot=False, output_status_snapshot=None, rate_limit_per_minute=50):
    """
    The main function to process the transcription jobs.

    Args:
        input_file_path (str): The path of the input CSV file where details of text and of past tts transactions are extracted.
        lang_code (str): A locale code, e.g.: 'es-CO' and the name for the column to select for tts transcription
        voice (str): The name of the play.ht voice to use, e.g.: 'es-CO-SalomeNeural'
        user_id (str): The user ID for authentication.
        auth_token (str): The authentication token.
        item_id_column (str, optional): column name in the input file for stable and unique item ID. Defaults to 'item_id'.
        output_file_path (str, optional): The path of the output CSV files to store the state of our transactions. Defaults to 'tts_{timestamp}_{user_id}.csv'
        rate_limit_per_minute (int, optional): The rate limit expected for the endpoint. Defaults to 50.
    """
    status_data_store = setup_csvmanager_status_store(
        input_file_path=input_status_snapshot,
        output_file_path=output_status_snapshot,
        user_id=user_id,
        item_id_column=item_id_column,
        overwrite_input_file=overwrite_input_snapshot,
        )

    # parse transaction objects
    transactions = status_data_store.extract_transactions(lang_code=lang_code, voice=voice)

    process_transactions(
        transactions=transactions,
        status_data_store=status_data_store,
        user_id=user_id,
        auth_token=auth_token,
        rate_limit_per_minute=rate_limit_per_minute,
        )

    # create directory for audio files
    directory_path = create_directory(lang_code)
    #TODO download audio files to directory_path

