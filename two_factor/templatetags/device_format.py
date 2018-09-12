import re

from django import template
from django.utils.translation import ugettext_lazy as _

register = template.Library()

BROWSERS = (
    (re.compile('Chrome'), _('Chrome')),
    (re.compile('Safari'), _('Safari')),
    (re.compile('Firefox'), _('Firefox')),
    (re.compile('Opera'), _('Opera')),
    (re.compile('IE'), _('Internet Explorer')),
)
DEVICES = (
    (re.compile('Android'), _('Android')),
    (re.compile('Linux'), _('Linux')),
    (re.compile('iPhone'), _('iPhone')),
    (re.compile('iPad'), _('iPad')),
    (re.compile('Mac OS X 10[._]9'), _('OS X Mavericks')),
    (re.compile('Mac OS X 10[._]10'), _('OS X Yosemite')),
    (re.compile('Mac OS X 10[._]11'), _('OS X El Capitan')),
    (re.compile('Mac OS X 10[._]12'), _('macOS Sierra')),
    (re.compile('Mac OS X 10[._]13'), _('macOS High Sierra')),
    (re.compile('Mac OS X'), _('OS X')),
    (re.compile('NT 5.1'), _('Windows XP')),
    (re.compile('NT 6.0'), _('Windows Vista')),
    (re.compile('NT 6.1'), _('Windows 7')),
    (re.compile('NT 6.2'), _('Windows 8')),
    (re.compile('NT 6.3'), _('Windows 8.1')),
    (re.compile('NT 10.0'), _('Windows 10')),
    (re.compile('Windows'), _('Windows')),
)


@register.filter
def agent_format(value):
    """
    Transform a User Agent into human readable text.

    Example output:

    * Safari on iPhone
    * Chrome on Windows 8.1
    * Safari on OS X
    * Firefox
    * Linux
    * None
    """

    browser = None
    for regex, name in BROWSERS:
        if regex.search(value):
            browser = name
            break

    device = None
    for regex, name in DEVICES:
        if regex.search(value):
            device = name
            break

    if browser and device:
        return _('%(browser)s on %(device)s') % {
            'browser': browser,
            'device': device
        }

    if browser:
        return browser

    if device:
        return device

    return None
