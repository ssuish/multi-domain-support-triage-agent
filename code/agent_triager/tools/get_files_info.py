import os

from config import WORKING_DIR


def get_files_info(directory: str = ".") -> str:
    """Gets basic metadata for entries in a directory.

    Args:
        directory (str, optional): Relative directory to inspect. Defaults to ".".
    """

    try:
        data_root = os.path.abspath(WORKING_DIR)
        target_dir = os.path.abspath(os.path.join(data_root, directory))
        if os.path.commonpath([data_root, target_dir]) != data_root:
            raise Exception(
                f'Cannot list "{directory}" as it is outside the permitted data directory'
            )
        if not os.path.isdir(target_dir):
            raise Exception(f'"{directory}" is not a directory')
        result = []
        for name in os.listdir(target_dir):
            if name in (".", ".."):
                continue
            path = os.path.join(target_dir, name)
            file_size = os.path.getsize(path)
            is_dir = os.path.isdir(path)
            result.append(f"{name} : file_size={file_size}, is_dir={is_dir}")
        return "\n".join(result)
    except Exception as e:
        raise Exception(f"Error: {e}")
