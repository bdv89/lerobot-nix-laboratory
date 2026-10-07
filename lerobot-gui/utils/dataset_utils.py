"""
Dataset utility functions for scanning and parsing LeRobot datasets.
"""

from pathlib import Path
from typing import List


def scan_available_datasets(base_path: Path) -> List[str]:
    """
    Scan all available datasets in LeRobot cache directory.

    Args:
        base_path: Base directory to scan (e.g., ~/.cache/huggingface/lerobot/)

    Returns:
        List of dataset IDs in format 'username/dataset_name'

    Example:
        >>> base_path = Path.home() / '.cache/huggingface/lerobot'
        >>> datasets = scan_available_datasets(base_path)
        >>> print(datasets)
        ['user/run_test', 'user/test_dataset', 'local/test_dataset']
    """
    datasets = []

    if not base_path.exists():
        return datasets

    try:
        # Iterate over username directories
        for username_dir in base_path.iterdir():
            # Skip non-directories and calibration folder
            if not username_dir.is_dir() or username_dir.name in ['calibration', '.git']:
                continue

            # Iterate over dataset directories within each username
            for dataset_dir in username_dir.iterdir():
                if dataset_dir.is_dir():
                    # Only include datasets that have actual data (parquet files)
                    data_dir = dataset_dir / "data"
                    if data_dir.exists() and any(data_dir.rglob("*.parquet")):
                        dataset_id = f"{username_dir.name}/{dataset_dir.name}"
                        datasets.append(dataset_id)

    except PermissionError:
        pass  # Silently skip directories without permission

    return sorted(datasets)


def extract_dataset_id_from_path(full_path: str, base_path: Path) -> str:
    """
    Extract dataset ID (username/dataset_name) from an absolute path.

    Args:
        full_path: Absolute path to dataset directory
        base_path: Base lerobot directory

    Returns:
        Dataset ID in format 'username/dataset_name'

    Example:
        >>> base_path = Path('/home/name/.cache/huggingface/lerobot')
        >>> full_path = '/home/name/.cache/huggingface/lerobot/user/test_dataset'
        >>> extract_dataset_id_from_path(full_path, base_path)
        'user/test_dataset'
    """
    try:
        path = Path(full_path)
        relative = path.relative_to(base_path)
        parts = relative.parts

        # Format: username/dataset_name
        if len(parts) >= 2:
            return f"{parts[0]}/{parts[1]}"

        # Fallback if only one part
        if len(parts) == 1:
            return parts[0]

        # Fallback to full relative path
        return str(relative)

    except ValueError:
        # Path is not relative to base_path, return as-is
        return full_path


def validate_dataset_format(dataset_id: str) -> bool:
    """
    Validate dataset ID format.

    Args:
        dataset_id: Dataset ID to validate

    Returns:
        True if format is valid (contains '/'), False otherwise

    Example:
        >>> validate_dataset_format('user/test_dataset')
        True
        >>> validate_dataset_format('invalid')
        False
    """
    return '/' in dataset_id and len(dataset_id.split('/')) == 2


def get_dataset_path(base_path: Path, dataset_id: str) -> Path:
    """
    Convert dataset ID to absolute path.

    Args:
        base_path: Base lerobot directory
        dataset_id: Dataset ID in format 'username/dataset_name'

    Returns:
        Absolute path to dataset directory

    Example:
        >>> base_path = Path.home() / '.cache/huggingface/lerobot'
        >>> get_dataset_path(base_path, 'user/test_dataset')
        PosixPath('/home/user/.cache/huggingface/lerobot/user/test_dataset')
    """
    if validate_dataset_format(dataset_id):
        username, dataset_name = dataset_id.split('/')
        return base_path / username / dataset_name
    else:
        return base_path / dataset_id
