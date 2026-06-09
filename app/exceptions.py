class AppError(Exception):
    """Base class for errors safe to show to API and bot users."""


class StockDataError(AppError):
    pass


class AIProviderError(AppError):
    pass


class RateLimitError(AppError):
    pass


class ConfigurationError(AppError):
    pass

