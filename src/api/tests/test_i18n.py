"""
Unit tests for the i18n internationalization system.
Tests error handling, fallback mechanisms, translation loading, and monitoring.
"""

import pytest
import time
from unittest.mock import patch
from threading import Thread

from flaskr.i18n import (
    _,
    t,
    set_language,
    get_current_language,
    load_translations,
    reload_translations,
    get_translation_stats,
    get_i18n_health_status,
    check_translation_alerts,
    log_health_metrics,
    _safe_file_operation,
    _validate_translation_file,
    _load_emergency_translations,
    _try_fallback_directories,
    _interpolate_variables,
    _translations,
    _stats,
    _config,
)
from flaskr.i18n.exceptions import (
    TranslationNotFoundError,
    InvalidTranslationFormatError,
    InterpolationError,
)


class TestI18nBasicFunctionality:
    """Test basic i18n functions."""

    def setup_method(self):
        """Clear translations before each test."""
        _translations.clear()
        _stats.clear()
        _stats.update(
            {
                "translations_loaded": 0,
                "missing_keys": set(),
                "load_errors": [],
                "last_reload": None,
            }
        )
        set_language("en-US")

    def test_set_and_get_language(self):
        """Test setting and getting current language."""
        set_language("zh-CN")
        assert get_current_language() == "zh-CN"

        set_language("en-US")
        assert get_current_language() == "en-US"

    def test_basic_translation_function(self):
        """Test basic translation with _ function."""
        # Setup test translations
        _translations["en-US"]["TEST.KEY"] = "Test Value"
        _translations["zh-CN"]["TEST.KEY"] = "测试值"

        # Test English
        set_language("en-US")
        result = _("TEST.KEY")
        assert result == "Test Value"

        # Test Chinese
        set_language("zh-CN")
        result = _("TEST.KEY")
        assert result == "测试值"

    def test_enhanced_translation_function(self):
        """Test enhanced t() function with variable interpolation."""
        # Setup test translations with variables
        _translations["en-US"]["GREETING"] = "Hello {{name}}!"
        _translations["en-US"]["COUNT"] = "You have {{count}} items"

        set_language("en-US")

        # Test simple translation
        result = t("GREETING", name="World")
        assert result == "Hello World!"

        # Test with multiple variables
        result = t("COUNT", count=5)
        assert result == "You have 5 items"

        # Test with default value
        result = t("NONEXISTENT.KEY", default="Default Value")
        assert result == "Default Value"

    def test_fallback_language_mechanism(self):
        """Test fallback to configured fallback language."""
        # Setup translations only in fallback language
        _translations["en-US"]["FALLBACK.KEY"] = "Fallback Value"

        # Request from non-existent language
        set_language("fr-FR")
        result = _("FALLBACK.KEY")
        assert result == "Fallback Value"

    def test_emergency_translations(self):
        """Test emergency translation fallback."""
        # Clear all translations
        _translations.clear()

        set_language("en-US")
        result = _("COMMON.ERROR")
        assert result == "An error occurred"  # From emergency translations

        set_language("zh-CN")
        result = _("COMMON.ERROR")
        assert result == "发生错误"  # From emergency translations


class TestTranslationLoading:
    """Test translation loading functionality."""

    def setup_method(self):
        """Clear translations before each test."""
        _translations.clear()
        _stats.clear()
        _stats.update(
            {
                "translations_loaded": 0,
                "missing_keys": set(),
                "load_errors": [],
                "last_reload": None,
            }
        )

    def test_safe_file_operation_success(self):
        """Test successful file operation with retry logic."""

        def mock_operation(arg):
            return f"success_{arg}"

        result = _safe_file_operation(mock_operation, "test")
        assert result == "success_test"

    def test_safe_file_operation_retry(self):
        """Test file operation with retry on failure."""
        call_count = 0

        def mock_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise IOError("Temporary failure")
            return "success"

        result = _safe_file_operation(mock_operation, max_retries=3)
        assert result == "success"
        assert call_count == 3

    def test_safe_file_operation_max_retries_exceeded(self):
        """Test file operation failing after max retries."""

        def mock_operation():
            raise IOError("Persistent failure")

        with pytest.raises(IOError):
            _safe_file_operation(mock_operation, max_retries=2)

    def test_validate_translation_file_valid(self):
        """Test validation of valid translation file."""
        valid_content = {
            "user": {"login": {"title": "Login"}},
            "common": {"error": "Error occurred"},
        }

        # Should not raise any exception
        _validate_translation_file("test.json", valid_content)

    def test_validate_translation_file_invalid_root(self):
        """Test validation fails for non-dict root."""
        invalid_content = ["not", "a", "dict"]

        with pytest.raises(InvalidTranslationFormatError) as exc:
            _validate_translation_file("test.json", invalid_content)
        assert "Root level must be a dictionary" in str(exc.value)

    def test_validate_translation_file_empty(self):
        """Test validation fails for empty file."""
        empty_content = {}

        with pytest.raises(InvalidTranslationFormatError) as exc:
            _validate_translation_file("test.json", empty_content)
        assert "Translation file is empty" in str(exc.value)

    def test_validate_translation_file_invalid_value_type(self):
        """Test validation fails for non-string values."""
        invalid_content = {
            "user": {
                "login": {
                    "title": 123  # Should be string
                }
            }
        }

        with pytest.raises(InvalidTranslationFormatError) as exc:
            _validate_translation_file("test.json", invalid_content)
        assert "must be a string" in str(exc.value)

    @patch("os.path.exists")
    @patch("os.access")
    @patch("os.listdir")
    def test_try_fallback_directories_success(
        self, mock_listdir, mock_access, mock_exists
    ):
        """Test successful fallback directory discovery."""
        mock_exists.return_value = True
        mock_access.return_value = True
        mock_listdir.return_value = ["en-US.json", "zh-CN.json"]

        result = _try_fallback_directories()
        assert result is not None
        assert isinstance(result, str)

    @patch("os.path.exists")
    def test_try_fallback_directories_not_found(self, mock_exists):
        """Test fallback directory discovery when none exist."""
        mock_exists.return_value = False

        result = _try_fallback_directories()
        assert result is None

    def test_load_emergency_translations(self):
        """Test loading emergency translations."""
        _translations.clear()

        result = _load_emergency_translations()
        assert result is True
        assert "en-US" in _translations
        assert "zh-CN" in _translations
        assert _translations["en-US"]["COMMON.ERROR"] == "An error occurred"
        assert _translations["zh-CN"]["COMMON.ERROR"] == "发生错误"


class TestVariableInterpolation:
    """Test variable interpolation functionality."""

    def test_interpolate_variables_basic(self):
        """Test basic variable interpolation."""
        result = _interpolate_variables(
            "Hello {{name}}!", {"name": "World"}, "test.key"
        )
        assert result == "Hello World!"

    def test_interpolate_variables_multiple(self):
        """Test multiple variable interpolation."""
        result = _interpolate_variables(
            "{{user}} has {{count}} {{item}}",
            {"user": "John", "count": 5, "item": "books"},
            "test.key",
        )
        assert result == "John has 5 books"

    def test_interpolate_variables_missing(self):
        """Test behavior with missing variables."""
        result = _interpolate_variables(
            "Hello {{name}}, you have {{count}} messages",
            {"name": "John"},  # Missing 'count'
            "test.key",
        )
        assert result == "Hello John, you have {{count}} messages"

    def test_interpolate_variables_empty_dict(self):
        """Test interpolation with empty variables dict."""
        text = "Hello {{name}}!"
        result = _interpolate_variables(text, {}, "test.key")
        assert result == text

    def test_interpolate_variables_non_string_text(self):
        """Test interpolation with non-string text."""
        result = _interpolate_variables(None, {"name": "World"}, "test.key")
        assert result is None

        result = _interpolate_variables(123, {"name": "World"}, "test.key")
        assert result == 123


class TestErrorHandling:
    """Test comprehensive error handling."""

    def setup_method(self):
        """Setup for error handling tests."""
        _translations.clear()
        _stats.clear()
        _stats.update(
            {
                "translations_loaded": 0,
                "missing_keys": set(),
                "load_errors": [],
                "last_reload": None,
            }
        )

    def test_translation_not_found_graceful(self):
        """Test graceful degradation when translation not found."""
        # Enable graceful degradation
        original_config = _config["graceful_degradation"]
        _config["graceful_degradation"] = True

        try:
            set_language("en-US")
            result = _("NONEXISTENT.KEY")
            assert result == "NONEXISTENT.KEY"  # Should return key itself
        finally:
            _config["graceful_degradation"] = original_config

    def test_translation_not_found_strict_mode(self):
        """Test strict mode raises exception for missing translation."""
        original_config = _config["strict_mode"]
        _config["strict_mode"] = True

        try:
            set_language("en-US")
            with pytest.raises(TranslationNotFoundError):
                _("NONEXISTENT.KEY")
        finally:
            _config["strict_mode"] = original_config

    def test_interpolation_error_strict_mode(self):
        """Test interpolation error in strict mode."""
        original_config = _config["strict_mode"]
        _config["strict_mode"] = True

        try:
            # This should trigger an interpolation error in strict mode
            with patch(
                "flaskr.i18n._interpolate_variables",
                side_effect=Exception("Test error"),
            ):
                with pytest.raises(InterpolationError):
                    t("TEST.KEY", default="Hello {{name}}", name="World")
        finally:
            _config["strict_mode"] = original_config


class TestMonitoringAndHealth:
    """Test monitoring and health check functionality."""

    def setup_method(self):
        """Setup for monitoring tests."""
        _translations.clear()
        _stats.clear()
        _stats.update(
            {
                "translations_loaded": 0,
                "missing_keys": set(),
                "load_errors": [],
                "last_reload": time.time(),
            }
        )

    def test_get_translation_stats(self):
        """Test translation statistics."""
        _translations["en-US"].update({"KEY1": "Value1", "KEY2": "Value2"})
        _translations["zh-CN"].update({"KEY1": "值1"})

        stats = get_translation_stats()
        assert stats["en-US"] == 2
        assert stats["zh-CN"] == 1

    def test_get_i18n_health_status_healthy(self):
        """Test health status when system is healthy."""
        # Setup healthy state
        _translations["en-US"].update({"KEY1": "Value1", "KEY2": "Value2"})
        _translations["zh-CN"].update({"KEY1": "值1", "KEY2": "值2"})
        _stats["translations_loaded"] = 4

        health = get_i18n_health_status()
        assert health["status"] == "healthy"
        assert health["health_score"] >= 90
        assert len(health["loaded_languages"]) == 2
        assert health["total_translations"] == 4

    def test_get_i18n_health_status_failed(self):
        """Test health status when system has failed."""
        # No translations loaded
        health = get_i18n_health_status()
        assert health["status"] == "failed"
        assert health["health_score"] == 0
        assert "No translations loaded" in health["issues"]

    def test_get_i18n_health_status_degraded(self):
        """Test health status when system is degraded."""
        # Setup degraded state
        _translations["en-US"].update({"KEY1": "Value1"})
        _stats["translations_loaded"] = 1
        _stats["missing_keys"] = set(
            [f"en-US:MISSING_{i}" for i in range(60)]
        )  # Many missing keys
        _stats["load_errors"] = [{"error": "test", "timestamp": time.time()}]

        health = get_i18n_health_status()
        assert health["status"] in ["warning", "critical"]
        assert health["health_score"] < 90
        assert health["missing_keys_count"] == 60

    def test_check_translation_alerts_critical(self):
        """Test critical alerts are generated."""
        # Setup failed state
        alerts = check_translation_alerts()

        critical_alerts = [a for a in alerts if a["level"] == "critical"]
        assert len(critical_alerts) > 0
        assert any(
            "No translations loaded" in alert["message"] for alert in critical_alerts
        )

    def test_check_translation_alerts_warning(self):
        """Test warning alerts are generated."""
        # Setup warning conditions
        _translations["en-US"].update({"KEY1": "Value1"})
        _stats["missing_keys"] = set(
            [f"en-US:MISSING_{i}" for i in range(150)]
        )  # Many missing keys

        alerts = check_translation_alerts()
        warning_alerts = [a for a in alerts if a["level"] == "warning"]
        assert len(warning_alerts) > 0

    def test_log_health_metrics(self):
        """Test health metrics logging."""
        _translations["en-US"].update({"KEY1": "Value1"})
        _stats["translations_loaded"] = 1

        with patch("flaskr.i18n.logger") as mock_logger:
            health = log_health_metrics()

            # Should have called logger.info at least once
            mock_logger.info.assert_called()
            assert health is not None
            assert "status" in health


class TestThreadSafety:
    """Test thread safety of i18n functions."""

    def test_concurrent_language_setting(self):
        """Test setting language concurrently from different threads."""
        results = {}

        def set_and_get_language(thread_id, language):
            set_language(language)
            time.sleep(0.1)  # Small delay to simulate processing
            results[thread_id] = get_current_language()

        # Setup test translations
        _translations["en-US"]["TEST"] = "English"
        _translations["zh-CN"]["TEST"] = "Chinese"

        # Create threads with different languages
        threads = []
        for i in range(4):
            lang = "en-US" if i % 2 == 0 else "zh-CN"
            thread = Thread(target=set_and_get_language, args=(i, lang))
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify each thread got the correct language
        assert len(results) == 4
        for thread_id, language in results.items():
            expected = "en-US" if thread_id % 2 == 0 else "zh-CN"
            assert language == expected


class TestConfigurationIntegration:
    """Test integration with Flask app configuration."""

    def test_load_translations_with_app(self, app):
        """Test loading translations within Flask app context."""
        with app.app_context():
            # This should not raise any exceptions
            load_translations(app)

            # Basic functionality should work
            result = _("COMMON.ERROR")
            assert result is not None

    def test_reload_translations_with_app(self, app):
        """Test reloading translations within Flask app context."""
        with app.app_context():
            # Initial load
            load_translations(app)
            initial_count = len(_translations)

            # Reload
            reload_translations(app)

            # Should still have translations
            assert len(_translations) >= initial_count


class TestLegacyCompatibility:
    """Test backward compatibility with existing system."""

    def test_uppercase_key_compatibility(self):
        """Test that uppercase keys still work for backward compatibility."""
        _translations["en-US"]["USER.LOGIN.TITLE"] = "Login"

        set_language("en-US")

        # Both should work
        result1 = _("USER.LOGIN.TITLE")
        result2 = t("user.login.title")  # Should be converted to uppercase internally

        assert result1 == "Login"
        assert result2 == "Login"

    def test_mixed_case_key_handling(self):
        """Test handling of mixed case keys."""
        _translations["en-US"]["USER.LOGIN.TITLE"] = "Login"
        _translations["en-US"]["user.profile.name"] = "Profile Name"

        set_language("en-US")

        # Test various case combinations
        result1 = t("USER.LOGIN.TITLE")
        result2 = t("user.login.title")
        result3 = t("user.profile.name")
        result4 = t("USER.PROFILE.NAME")

        assert result1 == "Login"
        assert result2 == "Login"
        assert result3 == "Profile Name"
        assert result4 == "Profile Name"
