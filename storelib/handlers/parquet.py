import os
import typing
import pyarrow as pa
import pyarrow.parquet as pq


def _safe_filename(name: str) -> str:
    # Polygon currency tickers carry a ``C:`` prefix (e.g. ``C:EURUSD``); the
    # colon is invalid on Windows (NTFS treats it as an alternate-data-stream
    # separator and truncates the filename at it), so the cached parquet never
    # persisted before. Map any reserved char to ``_`` for the on-disk name.
    return name.translate(str.maketrans({c: "_" for c in r':<>"/\\|?*'}))


class ParquetHandler:
    """
    Class that handles the saving and loading of data in Parquet format.
    """

    def __init__(self, dirname: str) -> None:
        # Defines a path where the files are to be stored.
        self.data_dir = dirname

    def save(self, filename: str, data: typing.Any) -> None:
        """
        Saves the data in Parquet format.
        """
        # Check if the directory exists.
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # Save the data in Parquet format.
        table = pa.Table.from_pandas(data)
        pq.write_table(table, f'{self.data_dir}/{_safe_filename(filename)}.parquet')

    def load(self, filename: str) -> typing.Any:
        """
        Loads the data from Parquet format.
        """
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError("The directory does not exist.")

        # Load the data from Parquet format.
        table = pq.read_table(f'{self.data_dir}/{_safe_filename(filename)}.parquet')
        return table.to_pandas()