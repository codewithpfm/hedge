"""
    This module contains the class FeatherHandler 
    that handles the saving and loading of data in feather format.
"""
import os
import typing
import pyarrow.feather as feather


class FeatherHandler:
    """
    Class that hansles the saving and loading of data in feather format.
    """

    def __init__(self, dirname: str) -> None:
        # Defines a path where the files are to be stored.
        self.data_dir = dirname

    def save_data(self, filename: str, data: typing.Any) -> None:
        """
        Saves the data in feather format.
        """
        # Check if the directory exists.
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        # Save the data in feather format.
        feather.write_feather(data, f"self.data_dir/{filename}.feather")

    def load_data(self, filename: str) -> typing.Any:
        """
        Loads the data from feather format.
        """
        if not os.path.exists(self.data_dir):
            raise FileNotFoundError("The directory does not exist.")

        # Load the data from feather format.
        data = feather.read_feather(f"{filename}.feather")
        return data
