import os
import pandas as pd

from config import ROW_LIMIT, WORKING_DIR


def read_support_tickets(file_path=""):
    """Reads support tickets from the fixed support tickets CSV file.
    Args:
        file_path (str, optional): Must be "support_tickets/support_tickets.csv". Defaults to "".
    """

    try:
        allowed_rel_path = os.path.join("support_tickets", "support_tickets.csv")
        normalized_input = (
            os.path.normpath(file_path) if file_path else allowed_rel_path
        )
        if normalized_input != allowed_rel_path:
            raise Exception(
                f'Only "{allowed_rel_path}" is permitted for read_support_tickets'
            )
        file_path_abs = os.path.abspath(os.path.join(WORKING_DIR, allowed_rel_path))
        if not os.path.isfile(file_path_abs):
            raise Exception(
                f'File not found or is not a regular file: "{allowed_rel_path}"'
            )
        df = pd.read_csv(file_path_abs)
        df["Subject"] = df["Subject"].fillna("No Subject")
        df["Company"] = df["Company"].fillna("None")
        return df.to_dict("records")
    except Exception as e:
        raise Exception(f"Error: {e}")
