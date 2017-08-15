"""
Built-in span-level token classes.
"""

import re
import mistletoe.span_tokenizer as tokenizer

"""
The items and ordering of this __all__ matters to mistletoe (see
tokenize_inner). Don't mess with it unless you know what you are doing!
"""
__all__ = ['EscapeSequence', 'Emphasis', 'Strong', 'InlineCode',
           'Strikethrough', 'Image', 'FootnoteImage', 'Link',
           'FootnoteLink', 'AutoLink']

def tokenize_inner(content):
    """
    A wrapper around span_tokenizer.tokenize. Pass in all span-level token
    constructors as arguments to span_tokenizer.tokenize.

    Doing so (instead of importing span_token module in span_tokenizer)
    avoids cyclic dependency issues, and allows for future injections of
    custom token classes.

    See also: span_tokenizer.tokenize, block_token.tokenize.
    """
    token_types = [globals()[key] for key in __all__]
    fallback_token = RawText
    yield from tokenizer.tokenize(content, token_types, fallback_token)

def add_token(token_cls):
    globals()[token_cls.__name__] = token_cls
    __all__.insert(1, token_cls.__name__)

def remove_token(token_cls):
    del globals()[token_cls.__name__]
    __all__.remove(token_cls.__name__)

class SpanToken(object):
    """
    Base class for span-level tokens. Recursively parse inner tokens.

    Naming conventions:
        * raw denotes (possibly unparsed) input string, and is commonly used
          as the argument name for constructors.
        * self.children is a generator with all the inner tokens (thus if a
          token has children attribute, it is not a leaf node);
        * self.content denotes string stored (and later rendered) as-is,
          without need for extra parsing (thus if a token has content
          attribute, it is a leaf node).
        * pattern is a class variable (regex pattern) used by tokenize_inner
          to search for the next token. Match group 1 of the pattern gets
          passed in as raw into the constructor.  Every subclass of
          SpanToken must define its pattern (see span_tokenizer.tokenize).

    Attributes:
        children (generator object): inner tokens.
    """
    def __init__(self, match_obj):
        self._raw = match_obj.group(0)

def _first_not_none_group(match_obj):
    return next(group for group in match_obj.groups() if group is not None)

class Strong(SpanToken):
    """
    Strong tokens. ("**some text**")

    raw does not contain enclosing asterisks or underscores.
    """
    pattern = re.compile(r"\*\*(.+?)\*\*(?!\*)|__(.+)__(?!_)")
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.children = tokenize_inner(_first_not_none_group(match_obj))

class Emphasis(SpanToken):
    """
    Emphasis tokens. ("*some text*")

    raw does not contain enclosing asterisks or underscores.
    """
    pattern = re.compile(r"\*((?:\*\*|[^\*])+?)\*(?!\*)|_((?:__|[^_])+?)_")
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.children = tokenize_inner(_first_not_none_group(match_obj))

class InlineCode(SpanToken):
    """
    Inline code tokens. ("`some code`")

    raw does not contain enclosing apostrophes.
    """
    pattern = re.compile(r"`(.+?)`")
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.children = iter([RawText(match_obj.group(1))])

class Strikethrough(SpanToken):
    """
    Strikethrough tokens. ("~~some text~~")

    raw does not contain enclosing tildas.
    """
    pattern = re.compile(r"~~(.+)~~")
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.children = tokenize_inner(match_obj.group(1))

class Image(SpanToken):
    """
    Image tokens. ("![alt](src "title")")
    A leaf node.

    Attributes:
        alt (str): alternative text.
        src (str): image source.
        title (str): image title (default to empty).
    """
    pattern = re.compile(r'\!\[(.+?)\] *\((.+?)(?:"(.+?)")*\)')
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.alt = match_obj.group(1)
        self.src = match_obj.group(2)
        self.title = match_obj.group(3)

class FootnoteImage(SpanToken):
    """
    Footnote image tokens. ("![alt] [some key]")

    Attributes:
        alt (str): alternative text.
        src (FootnoteAnchor): could point to both src and title.
    """
    pattern = re.compile(r"\!\[(.+?)\] *\[(.+?)\]")
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.alt = match_obj.group(1)
        self.src = FootnoteAnchor(match_obj.group(2))

class Link(SpanToken):
    """
    Link tokens. ("[name](target)")

    Attributes:
        children (generator): link name still needs further parsing.
        target (str): link target.
    """
    pattern = re.compile(r"\[((?:!\[(?:.+?)\][\[\(](?:.+?)[\)\]])|(?:.+?))\] *\((.+?)\)")
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.children = tokenize_inner(match_obj.group(1))
        self.target = match_obj.group(2)

class FootnoteLink(SpanToken):
    """
    Footnote-style links. ("[name] [some target]")

    Attributes:
        children (generator): link name still needs further parsing.
        target (FootnoteAnchor): to be looked up when rendered.
    """
    pattern = re.compile(r"\[((?:!\[(?:.+?)\][\[\(](?:.+?)[\)\]])|(?:.+?))\] *\[(.+?)\]")
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.children = tokenize_inner(match_obj.group(1))
        self.target = FootnoteAnchor(match_obj.group(2))

class AutoLink(SpanToken):
    """
    Autolink tokens. ("<http://www.google.com>")
    A leaf node.

    Attributes:
        name (str): displayed name.
        target (str): link target.
    """
    pattern = re.compile(r"<(.+?)>")
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.name = match_obj.group(1)
        self.target = match_obj.group(1)

class EscapeSequence(SpanToken):
    """
    Escape sequences. ("\*")
    """
    pattern = re.compile(r"\\([\*\(\)\[\]\~])")
    def __init__(self, match_obj):
        super().__init__(match_obj)
        self.content = match_obj.group(1)

class RawText(SpanToken):
    """
    Raw text. A leaf node.
    """
    def __init__(self, raw):
        self.content = raw

class FootnoteAnchor(SpanToken):
    """
    Footnote anchor.
    To be replaced at render time.
    """
    def __init__(self, raw):
        self.key = raw
