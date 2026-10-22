from django import template
from django.template.defaultfilters import urlize
from django.utils.safestring import mark_safe


register = template.Library()


@register.filter
def urlize_new_tab(value):
    """Превращает адреса в тексте в ссылки, открывающиеся в новой вкладке."""
    # Сохраняем экранирование текста и nofollow стандартного фильтра Django.
    linked_text = urlize(value, autoescape=True)
    return mark_safe(
        linked_text.replace('<a href=', '<a target="_blank" href=').replace(
            'rel="nofollow"', 'rel="nofollow noopener noreferrer"'
        )
    )
