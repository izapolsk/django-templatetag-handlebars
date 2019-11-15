import django
from django.conf import settings
from django.template import Context, Engine
from django.test import TestCase
from django.test.utils import override_settings

settings.configure(DATABASES={"default": {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}})
django.setup()
libs = {
    "templatetag_handlebars": "templatetag_handlebars.templatetags.templatetag_handlebars",
    "i18n": "django.templatetags.i18n"
    }
engine = Engine(libraries=libs)


class TemplateTagTest(TestCase):
    # Set the Ember style settings to true here
    @override_settings(USE_EMBER_STYLE_ATTRS=False)
    def test_rendering(self):
        """
        Tests that {{}} tags are well escaped.
        """
        t = engine.from_string("""
            {% load i18n templatetag_handlebars %}

            <head>
                {% handlebars_js %}
            </head>

            {% tplhandlebars "tpl-testing" %}
                {% trans "with translation" %}
                {{name}}
                <p>{{{rawname}}}</p>
                {# works with comments too #}
            {% endtplhandlebars %}
            """)
        c = Context()
        rendered = t.render(c)
        print(rendered)

        self.assertFalse(settings.USE_EMBER_STYLE_ATTRS)
        self.assertTrue('handlebars.js"></script>' in rendered)
        self.assertTrue('<script type="text/x-handlebars-template" id="tpl-testing">' in rendered)
        self.assertTrue('{{name}}' in rendered)
        self.assertTrue('{{{rawname}}}' in rendered)
        self.assertTrue('with translation' in rendered)
        # Those should not be rendered :
        self.assertTrue('{% trans %}' not in rendered)
        self.assertTrue('comments' not in rendered)
        # HTML should not be escaped
        self.assertTrue('<p>' in rendered)
        self.assertTrue('</p>' in rendered)

    # Set the Ember style settings to true here
    @override_settings(USE_EMBER_STYLE_ATTRS=True)
    def test_emberjs_rendering(self):
        """
        Duplicate the previous test, except this time turn
        EMBERJS rendering ON
        Tests that {{}} tags are well escaped.
        """
        t = engine.from_string("""
            {% load i18n templatetag_handlebars %}

            <head>
                {% handlebars_js %}
            </head>

            {% tplhandlebars "tpl-testing" %}
                {% trans "with translation" %}
                <p>{{name}}</p>
                {{{rawname}}}
                {# works with comments too #}
            {% endtplhandlebars %}
            """)
        c = Context()
        rendered = t.render(c)
        print(rendered)

        self.assertTrue(settings.USE_EMBER_STYLE_ATTRS)
        self.assertTrue('handlebars.js"></script>' in rendered)
        self.assertTrue('<script type="text/x-handlebars" data-template-name="tpl-testing">' in rendered)
        self.assertTrue('{{name}}' in rendered)
        self.assertTrue('{{{rawname}}}' in rendered)
        self.assertTrue('with translation' in rendered)
        # Those should not be rendered :
        self.assertTrue('{% trans %}' not in rendered)
        self.assertTrue('comments' not in rendered)
        # HTML should not be escaped
        self.assertTrue('<p>' in rendered)
        self.assertTrue('</p>' in rendered)
