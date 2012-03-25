
"""
Copyright (C) 2009-2011 EdenWall Technologies

This file is part of NuFirewall. 
 
 NuFirewall is free software: you can redistribute it and/or modify 
 it under the terms of the GNU General Public License as published by 
 the Free Software Foundation, version 3 of the License. 
 
 NuFirewall is distributed in the hope that it will be useful, 
 but WITHOUT ANY WARRANTY; without even the implied warranty of 
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the 
 GNU General Public License for more details. 
 
 You should have received a copy of the GNU General Public License 
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>
"""

from PyQt4.QtCore import Qt
from ufwi_rpcd.common.tools import minmax
import re

def stripHTMLTags(html):
    r"""
    Strip HTML tags. Examples:

    >>> stripHTMLTags(u'<p>Text</p>')
    u'Text\n\n'
    >>> stripHTMLTags(u'<b>bold</b> <i>italic</i>')
    u'bold italic'
    >>> stripHTMLTags(u'a<br>b')
    u'a\nb'
    >>> stripHTMLTags(u'<ul><li>a</li><li>b</li></ul>')
    u' - a\n - b\n\n'
    >>> stripHTMLTags(u'&lt;func&gt;')
    u'<func>'
    >>> stripHTMLTags(u'Error: &quot;oops&apos;.')
    u'Error: "oops\'.'
    """
    text = html
    text = re.sub(ur'<li>', u' - ', text)
    text = re.sub(ur'</(li|ul)>', u'\n', text)
    text = re.sub(ur'</(p|pre)>', u'\n\n', text)
    text = re.sub(ur'<br[^>]*>', u'\n', text)
    text = re.sub(ur'<.*?>', u'', text)
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&nbsp;", " ")
    text = text.replace("&quot;", '"')
    text = text.replace("&apos;", "'")
    return text

def escapeHTML(text, nl2br=True):
    r"""
    Escape HTML to be used in a widget displaying HMTL code.
    Example:

    >>> escapeHTML('<a>text</a>')
    u'&lt;a&gt;text&lt;/a&gt;'
    >>> print escapeHTML('one\ntwo')
    one<br />two
    """
    text = Qt.escape(text)
    text = unicode(text)
    if nl2br:
        text = text.replace("\n", "<br />")
    return text

class Html:
    def __init__(self, value=None, escape=True):
        if value is None:
            self.html = u''
        elif isinstance(value, Html):
            self.html = value.html
        else:
            value = unicode(value)
            if escape:
                if not value:
                    value = u"(none)"
                value = escapeHTML(value)
            self.html = value

    def __add__(self, text):
        if not isinstance(text, Html):
            html = self.html + escapeHTML(text)
        else:
            html = self.html + text.html
        return Html(html, escape=False)

    def __radd__(self, text):
        if not isinstance(text, Html):
            html = escapeHTML(text) + self.html
        else:
            html = text.html + self.html
        return Html(html, escape=False)

    def __len__(self):
        return len(self.html)

    def __unicode__(self):
        return self.html

    def __repr__(self):
        return u"<Html %r>" % self.html

    def join(self, items):
        html = None
        for item in items:
            item = Html(item)
            if html:
                html += self + item
            else:
                html = item
        return html

BR = Html(u'<br />', escape=False)
NBSP = Html(u'&nbsp;', escape=False)

def _htmlTag(tag, content, attr=None):
    html = u"<%s" % tag
    if attr:
        for key, value in attr.iteritems():
            html += u' %s="%s"' % (key, Html(value))
    if content is not None:
        html += u">"
        html += unicode(Html(content))
        html += u"</%s>" % tag
    else:
        # Eg. "<img src="image.gif" />"
        html += u" />"
    return Html(html, escape=False)

def htmlTag(text, content, **attr):
    """
    >>> htmlTag('p', 'text', align="center")
    <Html u'<p align="center">text</p>'>
    """
    return _htmlTag(text, content, attr)

def htmlBold(text, escape=True, **attr):
    """
    >>> htmlBold('text')
    <Html u'<b>text</b>'>
    >>> htmlBold('text', align="center")
    <Html u'<b align="center">text</b>'>
    """
    return _htmlTag('b', Html(text, escape=escape), attr)

def htmlItalic(text, escape=True, **attr):
    """
    >>> htmlItalic('text')
    <Html u'<i>text</i>'>
    >>> htmlItalic('text', align="center")
    <Html u'<i align="center">text</i>'>
    """
    return _htmlTag('i', Html(text, escape=escape), attr)

def htmlSpan(html, **attr):
    """
    >>> htmlSpan('text', title='tooltip')
    <Html u'<span title="tooltip">text</span>'>
    >>> htmlSpan('text', style='color: red;')
    <Html u'<span style="color: red;">text</span>'>
    >>> htmlSpan('text', style='color: red;', align="center")
    <Html u'<span style="color: red;" align="center">text</span>'>
    """
    return _htmlTag('span', html, attr)

def htmlParagraph(text, escape=True, **attr):
    """
    >>> htmlParagraph('text')
    <Html u'<p>text</p>'>
    >>> htmlParagraph('text', align="center")
    <Html u'<p align="center">text</p>'>
    """
    return _htmlTag('p', Html(text, escape=escape), attr)

def htmlPre(text, escape=True, **attr):
    r"""
    >>> htmlPre('a\nb')
    <Html u'<pre>a\nb</pre>'>
    >>> htmlPre('a\nb', title='tooltip')
    <Html u'<pre title="tooltip">a\nb</pre>'>
    """
    if escape:
        html = escapeHTML(text, nl2br=False)
    else:
        html = text
    html = Html(html, escape=False)
    return _htmlTag('pre', html, attr)

def htmlLink(href, text, **attr):
    """
    >>> htmlLink('http://www.edenwall.com', 'EdenWall')
    <Html u'<a href="http://www.edenwall.com">EdenWall</a>'>
    """
    attr['href'] = href
    return _htmlTag('a', text, attr)

def htmlImage(src, **attr):
    """
    >>> htmlImage('image.gif')
    <Html u'<img src="image.gif" />'>
    >>> htmlImage('image.gif', width=32)
    <Html u'<img width="32" src="image.gif" />'>
    >>> htmlImage('image.gif', align="top")
    <Html u'<img src="image.gif" align="top" />'>
    """
    attr['src'] = src
    return _htmlTag('img', None, attr)

def htmlHeader(level, text, escape=True, **attr):
    r"""
    Level have to be in [1; 6].

    >>> htmlHeader(1, 'Document')
    <Html u'<h1>Document</h1>'>
    >>> htmlHeader(7, 'Subsection')
    <Html u'<h6>Subsection</h6>'>
    """
    tag = 'h%s' % minmax(1, level, 6)
    return _htmlTag(tag, Html(text, escape=escape), attr)

def htmlList(items):
    """
    >>> htmlList(['a', 'b'])
    <Html u'<ul><li>a</li><li>b</li></ul>'>
    """
    html = Html(u'<ul>', escape=False)
    for item in items:
        html += _htmlTag('li', item)
    html += Html(u'</ul>', escape=False)
    return html

def htmlTable(options):
    """
    >>> htmlTable([('key1', 'value1'), ('key2', 'value2')])
    <Html u'<table border-color="black" border="1" cellpadding="5" cellspacing="0" valign="middle"><tr><td border-color="black" border-style="solid"><i>key1</i></td><td>value1</td></tr><tr><td border-color="black" border-style="solid"><i>key2</i></td><td>value2</td></tr></table>'>
    """
    html = Html(u'<table border-color="black" border="1" cellpadding="5" cellspacing="0" valign="middle">', escape=False)
    for key, value in options:
        key = htmlItalic(key, escape=False)
        if isinstance(value, (list, tuple)):
            value = BR.join(value)
        else:
            value = Html(value)
        html += Html(u'<tr>', escape=False)
        html += Html(u'<td border-color="black" border-style="solid">%s</td>' % key, escape=False)
        html += Html(u'<td>%s</td>' % value, escape=False)
        html += Html(u'</tr>', escape=False)
    html += Html(u'</table>', escape=False)
    return Html(html, escape=False)

def htmlColor(html, color):
    return htmlSpan(html, style="color: %s;" % color)

