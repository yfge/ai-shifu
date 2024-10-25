from flask import Flask
import os
import importlib.util
from collections import defaultdict
import threading

# init translations
_translations = defaultdict(lambda: defaultdict(dict))

_thread_local = threading.local()


def load_translations(app: Flask):
    translations_dir = os.path.join(os.path.dirname(__file__))
    for lang in os.listdir(translations_dir):
        lang_dir = os.path.join(translations_dir, lang)
        app.logger.info(f"load_translations lang: {lang}")
        if os.path.isdir(lang_dir):
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
                                        module_name.upper() + "." + var_name
                                    ] = getattr(module, var_name)


def _(text):
    language = "en-US"
    if hasattr(_thread_local, "language"):
        language = _thread_local.language
    return _translations.get(language, _translations.get("en-US", {})).get(text, text)


def set_language(language):
    _thread_local.language = language


__all__ = ["_", "set_language"]
