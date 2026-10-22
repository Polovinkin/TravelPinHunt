import re

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


@register.filter
def location_description_links(value):
    """Сокращает ссылки на фото Google Maps до номеров внутри одного описания."""
    linked_text = urlize_new_tab(value)
    photo_number = 0

    def number_photo_link(match):
        nonlocal photo_number
        photo_number += 1
        # Меняем только подпись уже экранированной ссылки, сохраняя полный адрес.
        return (
            f'{match.group(1)} aria-label="Photo {photo_number} on Google Maps '
            f'(opens in a new tab)">[{photo_number}]</a>'
        )

    return mark_safe(
        re.sub(
            r'(<a\b[^>]*\bhref="https?://maps\.app\.goo\.gl(?:[/?#][^"]*)?"[^>]*)>[^<]*</a>',
            number_photo_link,
            linked_text,
            flags=re.IGNORECASE,
        )
    )
