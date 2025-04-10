from django import template
import re

register = template.Library()

@register.filter
def strip_html(value):
    clean = re.compile('<.*?>')
    return re.sub(clean, '', value)