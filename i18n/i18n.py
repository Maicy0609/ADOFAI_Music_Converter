# -*- coding: utf-8 -*-
"""
国际化模块 - i18n控制
支持多语言切换
"""

import json
import os
from typing import Dict, Any, Optional

# 支持的语言列表
SUPPORTED_LANGUAGES = {
    'zh_CN': '简体中文',
    'en_US': 'English'
}

# 默认语言
DEFAULT_LANGUAGE = 'zh_CN'

# 当前语言
_current_language: str = DEFAULT_LANGUAGE
_translations: Dict[str, Any] = {}


def get_i18n_dir() -> str:
    """获取i18n目录路径"""
    return os.path.dirname(os.path.abspath(__file__))


def load_language(lang_code: str) -> bool:
    """
    加载指定语言的翻译文件
    
    Args:
        lang_code: 语言代码，如 'zh_CN', 'en_US'
    
    Returns:
        bool: 是否加载成功
    """
    global _translations, _current_language
    
    if lang_code not in SUPPORTED_LANGUAGES:
        print(f"Warning: Unsupported language '{lang_code}', using default '{DEFAULT_LANGUAGE}'")
        lang_code = DEFAULT_LANGUAGE
    
    lang_file = os.path.join(get_i18n_dir(), f'{lang_code}.json')
    
    try:
        with open(lang_file, 'r', encoding='utf-8') as f:
            _translations = json.load(f)
        _current_language = lang_code
        return True
    except FileNotFoundError:
        print(f"Warning: Language file not found: {lang_file}")
        if lang_code != DEFAULT_LANGUAGE:
            return load_language(DEFAULT_LANGUAGE)
        return False
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in language file: {e}")
        return False


def get_current_language() -> str:
    """获取当前语言代码"""
    return _current_language


def set_language(lang_code: str) -> bool:
    """
    设置当前语言
    
    Args:
        lang_code: 语言代码
    
    Returns:
        bool: 是否设置成功
    """
    return load_language(lang_code)


def t(key: str, **kwargs) -> str:
    """
    翻译函数 - Translate
    
    Args:
        key: 翻译键，支持点分隔的嵌套键，如 'app.title'
        **kwargs: 格式化参数
    
    Returns:
        str: 翻译后的文本
    """
    global _translations
    
    # 如果还没有加载翻译，先加载默认语言
    if not _translations:
        load_language(DEFAULT_LANGUAGE)
    
    # 解析嵌套键
    keys = key.split('.')
    value = _translations
    
    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            # 键不存在，返回键本身
            return key
    
    # 如果不是字符串，转换为字符串
    if not isinstance(value, str):
        value = str(value)
    
    # 格式化参数
    try:
        return value.format(**kwargs)
    except KeyError:
        return value
    except ValueError:
        return value


def get_supported_languages() -> Dict[str, str]:
    """获取支持的语言列表"""
    return SUPPORTED_LANGUAGES.copy()


def select_language() -> str:
    """
    交互式选择语言
    
    Returns:
        str: 选择的语言代码
    """
    print()
    print("-" * 60)
    print(t('ui.language_title') if t('ui.language_title') != 'ui.language_title' else "Language Selection / 语言选择")
    print("-" * 60)
    
    langs = get_supported_languages()
    for i, (code, name) in enumerate(langs.items(), 1):
        current = " (current)" if code == get_current_language() else ""
        print(f"  {i}. {name}{current}")
    
    print("-" * 60)
    
    while True:
        try:
            choice = input(f"Select [1-{len(langs)}] (default 1): ").strip()
            
            if choice == "":
                choice = "1"
            
            idx = int(choice) - 1
            lang_codes = list(langs.keys())
            
            if 0 <= idx < len(lang_codes):
                selected = lang_codes[idx]
                set_language(selected)
                return selected
            else:
                print(f"Error: Please enter a number between 1 and {len(langs)}")
        except ValueError:
            print("Error: Please enter a valid number")


# 模块加载时初始化默认语言
load_language(DEFAULT_LANGUAGE)
