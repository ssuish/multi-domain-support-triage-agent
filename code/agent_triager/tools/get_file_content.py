import os
from config import CHARACTER_LIMIT, WORKING_DIR


def get_file_content(file_path):
    """Gets file content from a path within the data directory.
    Args:
        file_path (str): Relative file path under the data directory.
    """
    try:
        data_root = os.path.abspath(WORKING_DIR)
        file_path_abs = os.path.abspath(os.path.join(data_root, file_path))
        if os.path.commonpath([data_root, file_path_abs]) != data_root:
            raise Exception(
                f'Cannot read "{file_path}" as it is outside the permitted data directory'
            )
        if not os.path.isfile(file_path_abs):
            raise Exception(f'File not found or is not a regular file: "{file_path}"')
        with open(file_path_abs, "r") as f:
            file_content = f.read(CHARACTER_LIMIT)
            if f.read(1):
                file_content += (
                    f'[...File "{file_path}" truncated at {CHARACTER_LIMIT} characters]'
                )
            return file_content
    except Exception as e:
        raise Exception(f"Error: {e}")
