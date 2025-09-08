"""
Test fixtures and data for i18n testing.
"""

import tempfile
import os
import json
import shutil


class I18nTestDataFixtures:
    """Fixtures for i18n test data."""

    @staticmethod
    def get_sample_translations():
        """Get sample translation data for testing."""
        return {
            "en-US": {
                "user": {
                    "login": {
                        "title": "Login",
                        "username": "Username",
                        "password": "Password",
                        "button": "Sign In",
                        "forgot_password": "Forgot password?",
                    },
                    "register": {
                        "title": "Register",
                        "email": "Email Address",
                        "confirm_password": "Confirm Password",
                        "button": "Create Account",
                    },
                    "profile": {
                        "title": "My Profile",
                        "name": "Full Name",
                        "bio": "Biography",
                    },
                },
                "common": {
                    "error": "An error occurred",
                    "success": "Operation completed successfully",
                    "loading": "Loading...",
                    "save": "Save",
                    "cancel": "Cancel",
                    "delete": "Delete",
                    "edit": "Edit",
                    "close": "Close",
                    "greeting": "Hello {{name}}!",
                    "item_count": "You have {{count}} items",
                    "time_remaining": "{{minutes}} minutes remaining",
                },
                "navigation": {
                    "home": "Home",
                    "about": "About",
                    "contact": "Contact",
                    "settings": "Settings",
                    "help": "Help",
                },
                "error": {
                    "404": "Page not found",
                    "500": "Internal server error",
                    "403": "Access denied",
                    "network": "Network connection failed",
                    "timeout": "Request timeout",
                },
                "validation": {
                    "required": "This field is required",
                    "email_invalid": "Please enter a valid email address",
                    "password_too_short": "Password must be at least 8 characters",
                    "passwords_dont_match": "Passwords do not match",
                },
            },
            "zh-CN": {
                "user": {
                    "login": {
                        "title": "登录",
                        "username": "用户名",
                        "password": "密码",
                        "button": "登录",
                        "forgot_password": "忘记密码？",
                    },
                    "register": {
                        "title": "注册",
                        "email": "电子邮箱",
                        "confirm_password": "确认密码",
                        "button": "创建账户",
                    },
                    "profile": {"title": "我的资料", "name": "姓名", "bio": "个人简介"},
                },
                "common": {
                    "error": "发生错误",
                    "success": "操作成功完成",
                    "loading": "加载中...",
                    "save": "保存",
                    "cancel": "取消",
                    "delete": "删除",
                    "edit": "编辑",
                    "close": "关闭",
                    "greeting": "你好 {{name}}！",
                    "item_count": "您有 {{count}} 个项目",
                    "time_remaining": "剩余 {{minutes}} 分钟",
                },
                "navigation": {
                    "home": "首页",
                    "about": "关于",
                    "contact": "联系",
                    "settings": "设置",
                    "help": "帮助",
                },
                "error": {
                    "404": "页面未找到",
                    "500": "内部服务器错误",
                    "403": "访问被拒绝",
                    "network": "网络连接失败",
                    "timeout": "请求超时",
                },
                "validation": {
                    "required": "此字段是必需的",
                    "email_invalid": "请输入有效的电子邮箱地址",
                    "password_too_short": "密码必须至少8个字符",
                    "passwords_dont_match": "密码不匹配",
                },
            },
        }

    @staticmethod
    def get_invalid_translation_data():
        """Get invalid translation data for error testing."""
        return {
            "empty_dict": {},
            "non_dict_root": ["not", "a", "dict"],
            "invalid_value_types": {
                "user": {
                    "login": {
                        "title": 123,  # Should be string
                        "valid_key": "Valid value",
                    }
                }
            },
            "nested_invalid_types": {
                "user": {
                    "login": ["should", "be", "dict"],
                    "valid_section": {"title": "Valid"},
                }
            },
        }

    @staticmethod
    def create_temp_translation_files():
        """Create temporary translation files for testing."""
        temp_dir = tempfile.mkdtemp(prefix="i18n_test_")
        translations = I18nTestDataFixtures.get_sample_translations()

        file_paths = {}
        for lang, data in translations.items():
            file_path = os.path.join(temp_dir, f"{lang}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            file_paths[lang] = file_path

        # Create languages.json
        languages_config = {
            "supportedLanguages": [
                {"code": "en-US", "name": "English (US)"},
                {"code": "zh-CN", "name": "中文 (简体)"},
            ]
        }

        languages_file = os.path.join(temp_dir, "languages.json")
        with open(languages_file, "w", encoding="utf-8") as f:
            json.dump(languages_config, f, indent=2, ensure_ascii=False)

        file_paths["languages"] = languages_file
        file_paths["temp_dir"] = temp_dir

        return file_paths

    @staticmethod
    def create_invalid_translation_files():
        """Create invalid translation files for error testing."""
        temp_dir = tempfile.mkdtemp(prefix="i18n_invalid_test_")
        invalid_data = I18nTestDataFixtures.get_invalid_translation_data()

        file_paths = {}

        # Create files with different types of errors
        for error_type, data in invalid_data.items():
            file_path = os.path.join(temp_dir, f"{error_type}.json")
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            file_paths[error_type] = file_path

        # Create a file with invalid JSON syntax
        invalid_json_file = os.path.join(temp_dir, "invalid_json.json")
        with open(invalid_json_file, "w", encoding="utf-8") as f:
            f.write('{"invalid": json syntax missing quote}')
        file_paths["invalid_json"] = invalid_json_file

        # Create an empty file
        empty_file = os.path.join(temp_dir, "empty.json")
        with open(empty_file, "w", encoding="utf-8") as f:
            f.write("")
        file_paths["empty"] = empty_file

        file_paths["temp_dir"] = temp_dir

        return file_paths

    @staticmethod
    def cleanup_temp_files(file_paths):
        """Clean up temporary test files."""
        if "temp_dir" in file_paths:
            try:
                shutil.rmtree(file_paths["temp_dir"])
            except Exception:
                pass  # Ignore cleanup errors


class I18nTestScenarios:
    """Common test scenarios for i18n testing."""

    @staticmethod
    def get_translation_completeness_scenarios():
        """Get scenarios for testing translation completeness."""
        return {
            "complete_match": {
                "en-US": ["key1", "key2", "key3"],
                "zh-CN": ["key1", "key2", "key3"],
            },
            "partial_match": {
                "en-US": ["key1", "key2", "key3", "key4"],
                "zh-CN": ["key1", "key2"],
            },
            "no_match": {"en-US": ["key1", "key2"], "zh-CN": ["key3", "key4"]},
            "empty_secondary": {"en-US": ["key1", "key2", "key3"], "zh-CN": []},
        }

    @staticmethod
    def get_error_scenarios():
        """Get scenarios for testing error conditions."""
        return {
            "file_not_found": {
                "description": "Translation file does not exist",
                "error_type": "TranslationLoadError",
                "setup": lambda: "/nonexistent/path/translations.json",
            },
            "permission_denied": {
                "description": "No permission to read translation file",
                "error_type": "TranslationDirectoryError",
                "setup": None,  # Would need special setup
            },
            "invalid_json": {
                "description": "Translation file contains invalid JSON",
                "error_type": "InvalidTranslationFormatError",
            },
            "wrong_format": {
                "description": "Translation file has wrong structure",
                "error_type": "InvalidTranslationFormatError",
            },
        }

    @staticmethod
    def get_interpolation_scenarios():
        """Get scenarios for testing variable interpolation."""
        return {
            "simple_variable": {
                "template": "Hello {{name}}!",
                "variables": {"name": "World"},
                "expected": "Hello World!",
            },
            "multiple_variables": {
                "template": "{{user}} has {{count}} {{item}}",
                "variables": {"user": "John", "count": 5, "item": "books"},
                "expected": "John has 5 books",
            },
            "missing_variable": {
                "template": "Hello {{name}}, you have {{count}} messages",
                "variables": {"name": "John"},
                "expected": "Hello John, you have {{count}} messages",
            },
            "no_variables": {
                "template": "Hello world!",
                "variables": {},
                "expected": "Hello world!",
            },
            "extra_variables": {
                "template": "Hello {{name}}!",
                "variables": {"name": "John", "extra": "unused"},
                "expected": "Hello John!",
            },
            "numeric_variables": {
                "template": "Price: {{currency}}{{amount}}",
                "variables": {"currency": "$", "amount": 99.99},
                "expected": "Price: $99.99",
            },
        }


# Mock objects for testing
class MockFlaskApp:
    """Mock Flask app for testing."""

    def __init__(self):
        self.logger = MockLogger()

    def app_context(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class MockLogger:
    """Mock logger for testing."""

    def __init__(self):
        self.logs = {"info": [], "warning": [], "error": [], "debug": []}

    def info(self, message):
        self.logs["info"].append(message)

    def warning(self, message):
        self.logs["warning"].append(message)

    def error(self, message):
        self.logs["error"].append(message)

    def debug(self, message):
        self.logs["debug"].append(message)

    def get_logs(self, level=None):
        if level:
            return self.logs.get(level, [])
        return self.logs
