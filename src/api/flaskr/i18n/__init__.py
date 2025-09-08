from flask import Flask
import os
import importlib.util
import json
import time
from collections import defaultdict
import threading
from typing import Dict, Any, Optional, List
import logging

from .exceptions import (
    TranslationLoadError,
    TranslationNotFoundError,
    InvalidTranslationFormatError,
    TranslationDirectoryError,
    InterpolationError,
)


TRANSLATIONS_DEFAULT_NAME = "i18n"

# init translations
_translations = defaultdict(lambda: defaultdict(dict))

_thread_local = threading.local()

# Configuration settings
_config = {
    "max_retries": 3,
    "retry_delay": 0.1,  # seconds
    "fallback_language": "en-US",
    "fallback_directories": [  # Try these directories in order if main ones fail
        "locales",
        "../../../i18n/locales",
        os.path.join(os.path.dirname(__file__), "locales"),
    ],
    "strict_mode": False,  # If True, raises exceptions instead of returning fallback
    "cache_enabled": True,
    "log_missing_keys": True,
    "emergency_fallback": True,  # Use hardcoded emergency translations if all else fails
    "graceful_degradation": True,  # Return key name if translation not found
}

# Statistics and monitoring
_stats = {
    "translations_loaded": 0,
    "missing_keys": set(),
    "load_errors": [],
    "last_reload": None,
}

# Logger
logger = logging.getLogger(__name__)

# Emergency fallback translations for critical system messages
_emergency_translations = {
    "en-US": {
        "COMMON.ERROR": "An error occurred",
        "COMMON.SUCCESS": "Success",
        "COMMON.LOADING": "Loading...",
        "COMMON.RETRY": "Retry",
        "COMMON.CANCEL": "Cancel",
        "USER.LOGIN.TITLE": "Login",
        "USER.REGISTER.TITLE": "Register",
        "AUTH.INVALID_CREDENTIALS": "Invalid credentials",
        "AUTH.ACCESS_DENIED": "Access denied",
        "ERROR.SYSTEM_ERROR": "System error",
        "ERROR.NETWORK_ERROR": "Network error",
    },
    "zh-CN": {
        "COMMON.ERROR": "发生错误",
        "COMMON.SUCCESS": "成功",
        "COMMON.LOADING": "加载中...",
        "COMMON.RETRY": "重试",
        "COMMON.CANCEL": "取消",
        "USER.LOGIN.TITLE": "登录",
        "USER.REGISTER.TITLE": "注册",
        "AUTH.INVALID_CREDENTIALS": "凭据无效",
        "AUTH.ACCESS_DENIED": "访问被拒绝",
        "ERROR.SYSTEM_ERROR": "系统错误",
        "ERROR.NETWORK_ERROR": "网络错误",
    },
}


def _safe_file_operation(operation, *args, max_retries=None, **kwargs):
    """
    Execute file operation with retry logic and proper error handling
    """
    max_retries = max_retries or _config["max_retries"]

    for attempt in range(max_retries + 1):
        try:
            return operation(*args, **kwargs)
        except (OSError, IOError, PermissionError) as e:
            if attempt == max_retries:
                raise
            logger.warning(
                f"File operation failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
            )
            time.sleep(_config["retry_delay"] * (2**attempt))  # Exponential backoff

    return None


def _validate_translation_file(file_path: str, content: dict) -> None:
    """
    Validate translation file content and structure
    """
    if not isinstance(content, dict):
        raise InvalidTranslationFormatError(
            file_path, "Root level must be a dictionary"
        )

    # Check for empty content
    if not content:
        raise InvalidTranslationFormatError(file_path, "Translation file is empty")

    # Check for required structure
    def validate_nested_dict(obj, path=""):
        if not isinstance(obj, dict):
            return
        for key, value in obj.items():
            current_path = f"{path}.{key}" if path else key
            if isinstance(value, dict):
                validate_nested_dict(value, current_path)
            elif not isinstance(value, str):
                raise InvalidTranslationFormatError(
                    file_path,
                    f"Translation value at '{current_path}' must be a string, got {type(value).__name__}",
                )

    validate_nested_dict(content)


def _try_fallback_directories() -> Optional[str]:
    """
    Try multiple fallback directories to find translation files.
    Returns the first valid directory found.
    """
    candidates = []

    # Add configured fallback directories
    for fallback_dir in _config["fallback_directories"]:
        if os.path.isabs(fallback_dir):
            candidates.append(fallback_dir)
        else:
            # Relative to current module directory
            candidates.append(os.path.join(os.path.dirname(__file__), fallback_dir))

    # Add some common locations
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../../..")
    )
    candidates.extend(
        [
            os.path.join(project_root, "i18n/locales"),
            os.path.join(project_root, "locales"),
            os.path.join(os.path.dirname(__file__), "locales"),
            os.path.join(os.path.dirname(__file__), "../locales"),
        ]
    )

    for candidate in candidates:
        if os.path.exists(candidate) and os.access(candidate, os.R_OK):
            try:
                # Verify it contains at least one JSON file
                files = os.listdir(candidate)
                if any(f.endswith(".json") for f in files):
                    logger.info(f"Found valid translation directory: {candidate}")
                    return candidate
            except (OSError, PermissionError):
                continue

    return None


def load_translations_from_json(app: Flask, centralized_dir: str = None) -> bool:
    """
    Load translations from centralized JSON files with comprehensive error handling.
    Returns True if successfully loaded from centralized system.
    """
    global _stats

    if not centralized_dir:
        centralized_dir = _try_fallback_directories()

    if not centralized_dir:
        error = TranslationDirectoryError(
            directory="<not found>",
            operation="locate",
            reason="Neither local nor centralized translation directories found",
        )
        logger.warning(str(error))
        error_dict = error.to_dict()
        error_dict["timestamp"] = time.time()
        _stats["load_errors"].append(error_dict)

        # Use emergency fallback if enabled
        if _config["emergency_fallback"]:
            logger.warning("Loading emergency fallback translations")
            return _load_emergency_translations()

        return False

    if not os.path.exists(centralized_dir):
        error = TranslationDirectoryError(
            directory=centralized_dir,
            operation="access",
            reason="Directory does not exist",
        )
        logger.warning(str(error))
        error_dict = error.to_dict()
        error_dict["timestamp"] = time.time()
        _stats["load_errors"].append(error_dict)
        return False

    if not os.access(centralized_dir, os.R_OK):
        error = TranslationDirectoryError(
            directory=centralized_dir, operation="read", reason="No read permission"
        )
        logger.error(str(error))
        error_dict = error.to_dict()
        error_dict["timestamp"] = time.time()
        _stats["load_errors"].append(error_dict)
        return False

    loaded_languages = []
    errors = []

    try:
        # List directory with error handling
        try:
            files = _safe_file_operation(os.listdir, centralized_dir)
        except Exception as e:
            error = TranslationDirectoryError(
                directory=centralized_dir, operation="list", reason=str(e)
            )
            logger.error(str(error))
            _stats["load_errors"].append(error.to_dict())
            return False

        for file_name in files:
            if file_name.endswith(".json") and file_name != "languages.json":
                lang_code = file_name.replace(".json", "")
                file_path = os.path.join(centralized_dir, file_name)

                try:
                    # Load file with retry logic
                    translations_data = _safe_file_operation(
                        lambda fp: json.load(open(fp, "r", encoding="utf-8")), file_path
                    )

                    # Validate file content
                    _validate_translation_file(file_path, translations_data)

                    # Flatten nested JSON structure to dot notation for backward compatibility
                    flattened = _flatten_json(translations_data)
                    _translations[lang_code].update(flattened)
                    loaded_languages.append(lang_code)

                    logger.info(
                        f"Loaded JSON translations for {lang_code}: {len(flattened)} keys from {file_path}"
                    )

                except json.JSONDecodeError as e:
                    error = InvalidTranslationFormatError(
                        file_path, f"Invalid JSON: {str(e)}"
                    )
                    logger.error(str(error))
                    errors.append(error)
                    error_dict = error.to_dict()
                    error_dict["timestamp"] = time.time()
                    _stats["load_errors"].append(error_dict)

                except InvalidTranslationFormatError as e:
                    logger.error(str(e))
                    errors.append(e)
                    _stats["load_errors"].append(e.to_dict())

                except Exception as e:
                    error = TranslationLoadError(file_path, str(e))
                    logger.error(str(error))
                    errors.append(error)
                    error_dict = error.to_dict()
                    error_dict["timestamp"] = time.time()
                    _stats["load_errors"].append(error_dict)

        # Update statistics
        _stats["translations_loaded"] = sum(
            len(_translations[lang]) for lang in loaded_languages
        )
        _stats["last_reload"] = time.time()

        if loaded_languages:
            logger.info(
                f"Successfully loaded translations for languages: {', '.join(loaded_languages)}"
            )
            return True
        else:
            logger.warning("No translation files were successfully loaded")
            return False

    except Exception as e:
        error = TranslationDirectoryError(
            directory=centralized_dir, operation="process", reason=str(e)
        )
        logger.error(str(error))
        error_dict = error.to_dict()
        error_dict["timestamp"] = time.time()
        _stats["load_errors"].append(error_dict)
        return False


def _flatten_json(
    data: Dict[str, Any], parent_key: str = "", sep: str = "."
) -> Dict[str, str]:
    """
    Flatten nested JSON structure to dot notation.
    Example: {"user": {"login": {"title": "Login"}}} -> {"USER.LOGIN.TITLE": "Login"}
    """
    items = []
    for k, v in data.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_json(v, new_key, sep=sep).items())
        else:
            # Convert to uppercase for backward compatibility
            items.append((new_key.upper(), str(v)))
    return dict(items)


def _load_emergency_translations() -> bool:
    """
    Load hardcoded emergency translations when all other methods fail.
    This ensures the system can still function with basic translations.
    """
    global _translations, _stats

    try:
        for language, translations in _emergency_translations.items():
            _translations[language].update(translations)
            logger.info(
                f"Loaded {len(translations)} emergency translations for {language}"
            )

        _stats["translations_loaded"] = sum(
            len(_translations[lang]) for lang in _emergency_translations.keys()
        )
        _stats["last_reload"] = time.time()

        logger.warning("System running on emergency fallback translations only")
        return True

    except Exception as e:
        logger.error(f"Failed to load emergency translations: {e}")
        return False


def _load_translations_from_python(app: Flask, translations_dir: str):
    """
    Load translations from existing Python module system (for backward compatibility).
    """
    for lang in os.listdir(translations_dir):
        lang_dir = os.path.join(translations_dir, lang)
        if os.path.isdir(lang_dir) and lang_dir != "__pycache__" and lang_dir[0] != ".":
            app.logger.info(f"Loading Python translations for lang: {lang}")
            for module_name in os.listdir(lang_dir):
                module_path = os.path.join(lang_dir, module_name)
                if os.path.isdir(module_path):
                    for file_name in os.listdir(module_path):
                        if file_name.endswith(".py"):
                            file_path = os.path.join(module_path, file_name)
                            spec = importlib.util.spec_from_file_location(
                                module_name, file_path
                            )
                            module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(module)
                            for var_name in dir(module):
                                if not var_name.startswith("__"):
                                    _translations[lang][
                                        module_name.upper() + "." + var_name.upper()
                                    ] = getattr(module, var_name)


def load_translations(app: Flask, translations_dir=None, use_centralized=True):
    """
    Load translations with support for both centralized JSON and legacy Python modules.

    Args:
        app: Flask application instance
        translations_dir: Directory containing legacy Python translations
        use_centralized: Whether to try loading from centralized JSON system first
    """
    if not translations_dir:
        translations_dir = os.path.join(os.path.dirname(__file__))

    # First, try to load from centralized JSON system
    if use_centralized:
        json_loaded = load_translations_from_json(app)
        if json_loaded:
            app.logger.info(
                "Successfully loaded translations from centralized JSON system"
            )
            # Still load Python translations for any missing keys (backward compatibility)
            _load_translations_from_python(app, translations_dir)
            return

    # Fallback to legacy Python system
    app.logger.info("Loading translations from legacy Python system")
    _load_translations_from_python(app, translations_dir)


def _(text: str):
    """
    Legacy translation function with enhanced fallback mechanisms.
    """
    language = "en-US"
    if hasattr(_thread_local, "language"):
        language = _thread_local.language

    # Try current language first
    result = _translations.get(language, {}).get(text.upper())
    if result is not None:
        return result

    # Fallback to configured fallback language
    fallback_lang = _config["fallback_language"]
    if language != fallback_lang:
        result = _translations.get(fallback_lang, {}).get(text.upper())
        if result is not None:
            if _config["log_missing_keys"]:
                logger.debug(
                    f"Translation missing for '{text}' in {language}, used {fallback_lang} fallback"
                )
                _stats["missing_keys"].add(f"{language}:{text}")
            return result

    # Try emergency translations
    if _config["emergency_fallback"]:
        result = _emergency_translations.get(language, {}).get(text.upper())
        if result is not None:
            logger.debug(f"Using emergency translation for '{text}' in {language}")
            return result

        # Try emergency fallback language
        if language != fallback_lang:
            result = _emergency_translations.get(fallback_lang, {}).get(text.upper())
            if result is not None:
                logger.debug(
                    f"Using emergency {fallback_lang} translation for '{text}'"
                )
                return result

    # Log missing translation
    if _config["log_missing_keys"]:
        logger.warning(f"Translation not found: '{text}' for language '{language}'")
        _stats["missing_keys"].add(f"{language}:{text}")

    # Return original text if graceful degradation is enabled
    if _config["graceful_degradation"]:
        return text

    # Strict mode: raise exception
    if _config["strict_mode"]:
        raise TranslationNotFoundError(text, language)

    return text


def get_current_language():
    language = "en-US"
    if hasattr(_thread_local, "language"):
        language = _thread_local.language
    return language


def set_language(language):
    _thread_local.language = language


def get_i18n_list(app: Flask):
    return list(_translations.keys())


def reload_translations(app: Flask, translations_dir=None, use_centralized=True):
    """
    Reload translations (useful for development and when translations are updated).
    """
    global _translations
    _translations.clear()
    load_translations(app, translations_dir, use_centralized)


def get_translation_stats():
    """
    Get statistics about loaded translations.
    """
    stats = {}
    for lang, translations in _translations.items():
        stats[lang] = len(translations)
    return stats


def t(key: str, default: str = None, **kwargs) -> str:
    """
    Enhanced translation function with comprehensive fallback mechanisms and variable interpolation.

    Args:
        key: Translation key (can be dot-notated or uppercase)
        default: Default value if key not found
        **kwargs: Variables for interpolation

    Example:
        t('user.login.title')
        t('common.greeting', name='John')  # "Hello {{name}}" -> "Hello John"
    """
    language = "en-US"
    if hasattr(_thread_local, "language"):
        language = _thread_local.language

    fallback_lang = _config["fallback_language"]

    # Define key variants to try
    key_variants = [key, key.upper()]

    # Try current language first
    for key_variant in key_variants:
        result = _translations.get(language, {}).get(key_variant)
        if result is not None:
            return _interpolate_variables(result, kwargs, key)

    # Fallback to configured fallback language
    if language != fallback_lang:
        for key_variant in key_variants:
            result = _translations.get(fallback_lang, {}).get(key_variant)
            if result is not None:
                if _config["log_missing_keys"]:
                    logger.debug(
                        f"Translation missing for '{key}' in {language}, used {fallback_lang} fallback"
                    )
                    _stats["missing_keys"].add(f"{language}:{key}")
                return _interpolate_variables(result, kwargs, key)

    # Try emergency translations
    if _config["emergency_fallback"]:
        for key_variant in key_variants:
            result = _emergency_translations.get(language, {}).get(key_variant)
            if result is not None:
                logger.debug(f"Using emergency translation for '{key}' in {language}")
                return _interpolate_variables(result, kwargs, key)

        # Try emergency fallback language
        if language != fallback_lang:
            for key_variant in key_variants:
                result = _emergency_translations.get(fallback_lang, {}).get(key_variant)
                if result is not None:
                    logger.debug(
                        f"Using emergency {fallback_lang} translation for '{key}'"
                    )
                    return _interpolate_variables(result, kwargs, key)

    # Log missing translation
    if _config["log_missing_keys"]:
        logger.warning(f"Translation not found: '{key}' for language '{language}'")
        _stats["missing_keys"].add(f"{language}:{key}")

    # Use provided default
    if default is not None:
        return _interpolate_variables(default, kwargs, key)

    # Return key if graceful degradation is enabled
    if _config["graceful_degradation"]:
        return key

    # Strict mode: raise exception
    if _config["strict_mode"]:
        raise TranslationNotFoundError(key, language)

    return key


def _interpolate_variables(text: str, variables: dict, key: str) -> str:
    """
    Safely interpolate variables into translation text.

    Args:
        text: The translation text
        variables: Dictionary of variables to interpolate
        key: The translation key (for error reporting)

    Returns:
        Text with variables interpolated
    """
    if not variables or not isinstance(text, str):
        return text

    try:
        # Replace {{variable}} patterns with actual values
        result = text
        for var_name, var_value in variables.items():
            pattern = f"{{{{{var_name}}}}}"
            if pattern in result:
                result = result.replace(pattern, str(var_value))

        # Check for unresolved variables (debugging aid)
        import re

        unresolved = re.findall(r"\{\{(\w+)\}\}", result)
        if unresolved and _config["log_missing_keys"]:
            logger.debug(f"Unresolved variables in '{key}': {unresolved}")

        return result

    except Exception as e:
        logger.warning(f"Variable interpolation failed for key '{key}': {e}")
        if _config["strict_mode"]:
            raise InterpolationError(key, text, variables, str(e))
        return text


def get_supported_languages():
    """
    Get list of supported languages from the centralized system.
    """
    try:
        project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../../..")
        )
        languages_file = os.path.join(project_root, "i18n/locales/languages.json")

        if os.path.exists(languages_file):
            with open(languages_file, "r", encoding="utf-8") as f:
                languages_config = json.load(f)
            return [
                lang["code"] for lang in languages_config.get("supportedLanguages", [])
            ]
    except Exception:
        pass

    # Fallback to loaded translations
    return list(_translations.keys())


def get_i18n_health_status() -> Dict[str, Any]:
    """
    Get comprehensive health status of the i18n system.
    Used for monitoring and alerting.
    """
    global _stats

    current_time = time.time()
    loaded_languages = list(_translations.keys())

    # Calculate translation completeness
    completeness = {}
    if len(loaded_languages) > 1:
        # Use the language with most translations as reference
        ref_lang_keys = max(
            [set(_translations[lang].keys()) for lang in loaded_languages], key=len
        )
        for lang in loaded_languages:
            lang_keys = set(_translations[lang].keys())
            completeness[lang] = {
                "total_keys": len(lang_keys),
                "coverage_percentage": (len(lang_keys) / len(ref_lang_keys)) * 100
                if ref_lang_keys
                else 0,
                "missing_keys": list(ref_lang_keys - lang_keys),
            }

    # Analyze recent errors
    recent_errors = [
        error
        for error in _stats.get("load_errors", [])
        if current_time - error.get("timestamp", 0) < 3600
    ]  # Last hour

    # Calculate error rate
    error_rate = len(_stats.get("load_errors", [])) / max(
        1, _stats.get("translations_loaded", 1)
    )

    # Determine overall health
    health_score = 100
    issues = []

    if not loaded_languages:
        health_score = 0
        issues.append("No translations loaded")
    elif _config["fallback_language"] not in loaded_languages:
        health_score -= 30
        issues.append(
            f"Fallback language '{_config['fallback_language']}' not available"
        )

    if len(_stats.get("missing_keys", set())) > 50:
        health_score -= 20
        issues.append("High number of missing translation keys")

    if error_rate > 0.1:  # More than 10% error rate
        health_score -= 25
        issues.append("High translation error rate")

    if recent_errors:
        health_score -= 15
        issues.append("Recent loading errors")

    # Determine status
    if health_score >= 90:
        status = "healthy"
    elif health_score >= 70:
        status = "warning"
    elif health_score >= 30:
        status = "critical"
    else:
        status = "failed"

    return {
        "status": status,
        "health_score": max(0, health_score),
        "timestamp": current_time,
        "loaded_languages": loaded_languages,
        "fallback_language": _config["fallback_language"],
        "total_translations": _stats.get("translations_loaded", 0),
        "missing_keys_count": len(_stats.get("missing_keys", set())),
        "error_count": len(_stats.get("load_errors", [])),
        "recent_error_count": len(recent_errors),
        "error_rate": error_rate,
        "last_reload": _stats.get("last_reload"),
        "completeness": completeness,
        "issues": issues,
        "recent_errors": recent_errors,
        "config": {
            "emergency_fallback_enabled": _config["emergency_fallback"],
            "graceful_degradation_enabled": _config["graceful_degradation"],
            "strict_mode": _config["strict_mode"],
        },
    }


def check_translation_alerts() -> List[Dict[str, Any]]:
    """
    Check for conditions that should trigger alerts.
    Returns list of alert conditions.
    """
    alerts = []
    health = get_i18n_health_status()

    # Critical alerts
    if health["status"] == "failed":
        alerts.append(
            {
                "level": "critical",
                "type": "system_failure",
                "message": "I18n system failed completely",
                "details": health["issues"],
            }
        )

    if not health["loaded_languages"]:
        alerts.append(
            {
                "level": "critical",
                "type": "no_translations",
                "message": "No translations loaded",
                "details": "System running without any translation data",
            }
        )

    # Warning alerts
    if health["health_score"] < 70:
        alerts.append(
            {
                "level": "warning",
                "type": "degraded_performance",
                "message": f"I18n system health degraded (score: {health['health_score']})",
                "details": health["issues"],
            }
        )

    if health["missing_keys_count"] > 100:
        alerts.append(
            {
                "level": "warning",
                "type": "missing_keys",
                "message": f"High number of missing translation keys: {health['missing_keys_count']}",
                "details": list(
                    list(_stats.get("missing_keys", set()))[:10]
                ),  # Show first 10
            }
        )

    if health["recent_error_count"] > 0:
        alerts.append(
            {
                "level": "warning",
                "type": "recent_errors",
                "message": f"{health['recent_error_count']} translation errors in the last hour",
                "details": health["recent_errors"],
            }
        )

    # Info alerts
    if _config["fallback_language"] not in health["loaded_languages"]:
        alerts.append(
            {
                "level": "info",
                "type": "fallback_missing",
                "message": f'Fallback language "{_config["fallback_language"]}" not loaded',
                "details": f"Available languages: {health['loaded_languages']}",
            }
        )

    return alerts


def log_health_metrics():
    """
    Log health metrics for monitoring systems.
    Should be called periodically by monitoring systems.
    """
    health = get_i18n_health_status()
    alerts = check_translation_alerts()

    # Log overall health
    logger.info(f"I18n Health: {health['status']} (score: {health['health_score']})")

    # Log key metrics
    logger.info(
        f"I18n Metrics: {health['total_translations']} translations, "
        f"{len(health['loaded_languages'])} languages, "
        f"{health['missing_keys_count']} missing keys, "
        f"{health['error_count']} total errors"
    )

    # Log alerts
    for alert in alerts:
        level = alert["level"]
        message = alert["message"]
        if level == "critical":
            logger.error(f"I18n Alert [CRITICAL]: {message}")
        elif level == "warning":
            logger.warning(f"I18n Alert [WARNING]: {message}")
        else:
            logger.info(f"I18n Alert [INFO]: {message}")

    return health


__all__ = [
    "_",
    "t",
    "set_language",
    "get_current_language",
    "get_i18n_list",
    "load_translations",
    "reload_translations",
    "get_translation_stats",
    "get_supported_languages",
    "get_i18n_health_status",
    "check_translation_alerts",
    "log_health_metrics",
]
