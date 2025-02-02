from django import template
from django.conf import settings
from django.utils import safestring, six

# Token type constants moved in Django 2.1
try:
    from django.template.base import TokenType
except ImportError:

    class TokenType(object):
        TEXT = template.base.TOKEN_TEXT
        VAR = template.base.TOKEN_VAR
        BLOCK = template.base.TOKEN_BLOCK
        COMMENT = template.base.TOKEN_COMMENT


register = template.Library()

"""

    Most of this code was written by Miguel Araujo
    https://gist.github.com/893408

"""


def verbatim_tags(parser, token, endtagname):
    """
    Javascript templates (jquery, handlebars.js, mustache.js) use constructs like:

    ::

        {{if condition}} print something{{/if}}

    This, of course, completely screws up Django templates,
    because Django thinks {{ and }} means something.

    The following code preserves {{ }} tokens.

    This version of verbatim template tag allows you to use tags
    like url {% url name %}. {% trans "foo" %} or {% csrf_token %} within.
    """
    text_and_nodes = []
    while 1:
        token = parser.tokens.pop(0)
        if token.contents == endtagname:
            break

        if token.token_type == TokenType.VAR:
            text_and_nodes.append('{{')
            text_and_nodes.append(token.contents)

        elif token.token_type == TokenType.TEXT:
            text_and_nodes.append(token.contents)

        elif token.token_type == TokenType.BLOCK:
            try:
                command = token.contents.split()[0]
            except IndexError:
                parser.empty_block_tag(token)

            try:
                compile_func = parser.tags[command]
            except KeyError:
                parser.invalid_block_tag(token, command, None)
            try:
                node = compile_func(parser, token)
            except template.TemplateSyntaxError as e:
                if not parser.compile_function_error(token, e):
                    raise
            text_and_nodes.append(node)

        if token.token_type == TokenType.VAR:
            text_and_nodes.append('}}')

    return text_and_nodes


class VerbatimNode(template.Node):
    """
    Wrap {% verbatim %} and {% endverbatim %} around a
    block of javascript template and this will try its best
    to output the contents with no changes.

    ::

        {% verbatim %}
            {% trans "Your name is" %} {{first}} {{last}}
        {% endverbatim %}
    """
    def __init__(self, text_and_nodes):
        self.text_and_nodes = text_and_nodes

    def render(self, context):
        output = ""
        # If its text we concatenate it, otherwise it's a node and we render it
        for bit in self.text_and_nodes:
            if isinstance(bit, six.string_types):
                output += bit
            else:
                output += bit.render(context)
        return output


@register.tag
def verbatim(parser, token):
    text_and_nodes = verbatim_tags(parser, token, 'endverbatim')
    return VerbatimNode(text_and_nodes)


@register.simple_tag
def handlebars_js():
    out = """<script src="%shandlebars.js"></script>""" % settings.STATIC_URL
    return safestring.mark_safe(out)


class HandlebarsNode(VerbatimNode):
    """
    A Handlebars.js block is a *verbatim* block wrapped inside a
    named (``template_id``) <script> tag.

    ::

        {% tplhandlebars "tpl-popup" %}
            {{#ranges}}
                <li>{{min}} < {{max}}</li>
            {{/ranges}}
        {% endtplhandlebars %}

    """
    def __init__(self, template_id, text_and_nodes):
        super(HandlebarsNode, self).__init__(text_and_nodes)
        self.template_id = template_id

    def render(self, context):
        output = super(HandlebarsNode, self).render(context)
        if getattr(settings, 'USE_EMBER_STYLE_ATTRS', False) is True:
            id_attr, script_type = 'data-template-name', 'text/x-handlebars'
        else:
            id_attr, script_type = 'id', 'text/x-handlebars-template'
        head_script = '<script type="%s" %s="%s">' % (script_type, id_attr,
                                                      self.template_id)
        return """
        %s
        %s
        </script>""" % (head_script, output)


def stripquote(s):
    return s[1:-1] if s[:1] == '"' else s


@register.tag
def tplhandlebars(parser, token):
    text_and_nodes = verbatim_tags(parser, token, endtagname='endtplhandlebars')
    # Extract template id from token
    tokens = token.split_contents()
    try:
        tag_name, template_id = map(stripquote, tokens[:2])
    except ValueError:
        raise template.TemplateSyntaxError(
            "%s tag requires exactly one argument" % token.split_contents()[0])
    return HandlebarsNode(template_id, text_and_nodes)
