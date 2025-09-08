"""
AI-Shifu i18n Exception Classes
Define specific exceptions for internationalization operations
"""


class I18nException(Exception):
    """Base exception for all i18n related errors"""

    def __init__(self, message: str, code: str = None, details: dict = None):
        self.message = message
        self.code = code or "I18N_ERROR"
        self.details = details or {}
        super().__init__(self.message)

    def __str__(self):
        return f"[{self.code}] {self.message}"

    def to_dict(self):
        """Convert exception to dictionary for JSON serialization"""
        return {
            "error": True,
            "code": self.code,
            "message": self.message,
            "details": self.details,
        }


class TranslationLoadError(I18nException):
    """Raised when translation files cannot be loaded"""

    def __init__(self, file_path: str, reason: str = None):
        self.file_path = file_path
        self.reason = reason
        message = f"Failed to load translation file: {file_path}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="TRANSLATION_LOAD_ERROR",
            details={"file_path": file_path, "reason": reason},
        )


class TranslationNotFoundError(I18nException):
    """Raised when a translation key is not found"""

    def __init__(self, key: str, language: str = None):
        self.key = key
        self.language = language
        message = f"Translation not found: {key}"
        if language:
            message += f" (language: {language})"
        super().__init__(
            message=message,
            code="TRANSLATION_NOT_FOUND",
            details={"key": key, "language": language},
        )


class InvalidTranslationFormatError(I18nException):
    """Raised when translation file format is invalid"""

    def __init__(self, file_path: str, format_error: str):
        self.file_path = file_path
        self.format_error = format_error
        super().__init__(
            message=f"Invalid translation format in {file_path}: {format_error}",
            code="INVALID_TRANSLATION_FORMAT",
            details={"file_path": file_path, "format_error": format_error},
        )


class LanguageNotSupportedError(I18nException):
    """Raised when requested language is not supported"""

    def __init__(self, language: str, supported_languages: list = None):
        self.language = language
        self.supported_languages = supported_languages or []
        message = f"Language not supported: {language}"
        if supported_languages:
            message += f". Supported: {', '.join(supported_languages)}"
        super().__init__(
            message=message,
            code="LANGUAGE_NOT_SUPPORTED",
            details={
                "requested_language": language,
                "supported_languages": self.supported_languages,
            },
        )


class TranslationDirectoryError(I18nException):
    """Raised when translation directory operations fail"""

    def __init__(self, directory: str, operation: str, reason: str = None):
        self.directory = directory
        self.operation = operation
        self.reason = reason
        message = f"Translation directory {operation} failed: {directory}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="TRANSLATION_DIRECTORY_ERROR",
            details={"directory": directory, "operation": operation, "reason": reason},
        )


class InterpolationError(I18nException):
    """Raised when variable interpolation fails"""

    def __init__(
        self, key: str, template: str, variables: dict = None, reason: str = None
    ):
        self.key = key
        self.template = template
        self.variables = variables or {}
        self.reason = reason
        message = f"Interpolation failed for key '{key}': {template}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="INTERPOLATION_ERROR",
            details={
                "key": key,
                "template": template,
                "variables": self.variables,
                "reason": reason,
            },
        )


class ConfigurationError(I18nException):
    """Raised when i18n configuration is invalid"""

    def __init__(self, config_key: str, config_value: str = None, reason: str = None):
        self.config_key = config_key
        self.config_value = config_value
        self.reason = reason
        message = f"Invalid i18n configuration: {config_key}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            details={
                "config_key": config_key,
                "config_value": config_value,
                "reason": reason,
            },
        )


class TranslationSyncError(I18nException):
    """Raised when translation synchronization fails"""

    def __init__(self, source: str, target: str, reason: str = None):
        self.source = source
        self.target = target
        self.reason = reason
        message = f"Translation sync failed from {source} to {target}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            code="TRANSLATION_SYNC_ERROR",
            details={"source": source, "target": target, "reason": reason},
        )
