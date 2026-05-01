import os
import json
from django.conf import settings
from django.utils.translation import get_language

# Cache the loaded translations
_TRANSLATIONS = {}

def load_translations():
    global _TRANSLATIONS
    if _TRANSLATIONS and not getattr(settings, 'DEBUG', False):
        return _TRANSLATIONS
    
    locale_dir = os.path.join(settings.BASE_DIR, 'locale')
    langs = ['uz', 'ru', 'en']
    
    for lang in langs:
        file_path = os.path.join(locale_dir, f'{lang}.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                try:
                    _TRANSLATIONS[lang] = json.load(f)
                except json.JSONDecodeError:
                    _TRANSLATIONS[lang] = {}
        else:
            _TRANSLATIONS[lang] = {}
            
    return _TRANSLATIONS

def t(key, lang=None, **kwargs):
    if not lang:
        lang = get_language()
        if not lang:
            lang = 'uz' 
    
    translations = load_translations()
    lang_dict = translations.get(lang, translations.get('uz', {}))
    
    text = lang_dict.get(key)
    
    # Strictly return the exact match. If missing, return the key to make it obvious during testing.
    # No fallback to UZ unless strictly asked, and prompt says: "No fallback to Uzbek unless explicitly missing"
    if text is None:
        return f"[{key}]"  # Missing translation marker
        
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
            
    return text
