import os

from config import WORKING_DIR


def write_file(file_path, content):
    """Writes the support report to the fixed output CSV file.
    Args:
        file_path (str): Must be "support_tickets/output.csv".
        content (str): Report content to write to the output file.
    """
    try:
        allowed_rel_path = os.path.join("support_tickets", "output.csv")
        normalized_input = os.path.normpath(file_path)
        if normalized_input != allowed_rel_path:
            raise Exception(f'Only "{allowed_rel_path}" is permitted for write_file')
        file_path_abs = os.path.abspath(os.path.join(WORKING_DIR, allowed_rel_path))
        if os.path.isdir(file_path_abs):
            raise Exception(
                f'Cannot write to "{allowed_rel_path}" as it is a directory'
            )
        os.makedirs(os.path.dirname(file_path_abs), exist_ok=True)
        with open(file_path_abs, "w") as f:
            f.write(content + "\n")
        return f'Successfully wrote to "{allowed_rel_path}" ({len(content)} characters written)'
    except Exception as e:
        raise Exception(f"Error: {e}")
