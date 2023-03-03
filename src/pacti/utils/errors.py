"""Global error classes."""


class IncompatibleArgsError(ValueError):
    """Argument validation errors."""

class FileDataFormatError(Exception):
    pass

class ContractFormatError(FileDataFormatError):
    pass