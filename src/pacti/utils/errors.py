"""Global error classes."""


class IncompatibleArgsError(ValueError):
    """Argument validation errors."""


class FileDataFormatError(Exception):
    """Incorrect format"""


class ContractFormatError(FileDataFormatError):
    """Incorrect format"""
