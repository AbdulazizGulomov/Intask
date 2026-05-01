from django import template
from django.utils.safestring import mark_safe
from utils.translations import t as translate_func

register = template.Library()

@register.simple_tag(takes_context=True)
def t(context, key, **kwargs):
    request = context.get('request')
    lang = getattr(request, 'LANGUAGE_CODE', 'uz') if request else 'uz'
    return mark_safe(translate_func(key, lang=lang, **kwargs))

@register.filter
def t_filter(key, arg=None):
    # This filter doesn't have access to context easily, but we can try to get language
    from django.utils.translation import get_language
    lang = get_language() or 'uz'
    return mark_safe(translate_func(key, lang=lang))
