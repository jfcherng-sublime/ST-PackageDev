import json
import os
import plistlib
import uuid

import sublime_plugin

from sublime_lib.path import root_at_packages
from sublime_lib.view import has_file_ext, in_one_edit


JSON_TMLANGUAGE_SYNTAX = 'Packages/AAAPackageDev/Support/Sublime JSON Syntax Definition.tmLanguage'


# XXX: Move this to a txt file. Let user define his own under User too.
def get_syntax_def_boilerplate():
    JSON_TEMPLATE = """{ "name": "${1:Syntax Name}",
  "scopeName": "source.${2:syntax_name}",
  "fileTypes": ["$3"],
  "patterns": [$0
  ],
  "uuid": "%s"
}"""

    actual_tmpl = JSON_TEMPLATE % str(uuid.uuid4())
    return actual_tmpl


class NewSyntaxDefCommand(sublime_plugin.WindowCommand):
    """Creates a new syntax definition file for Sublime Text in JSON format
    with some boilerplate text.
    """
    def run(self):
        target = self.window.new_file()

        target.settings().set('default_dir', root_at_packages('User'))
        target.settings().set('syntax', JSON_TMLANGUAGE_SYNTAX)

        target.run_command('insert_snippet',
                           {'contents': get_syntax_def_boilerplate()})


class NewSyntaxDefFromBufferCommand(sublime_plugin.TextCommand):
    """Inserts boilerplate text for syntax defs into current view.
    """
    def is_enabled(self):
        # Don't mess up a non-empty buffer.
        return self.view.size() == 0

    def run(self, edit):
        self.view.settings().set('default_dir', root_at_packages('User'))
        self.view.settings().set('syntax', JSON_TMLANGUAGE_SYNTAX)

        with in_one_edit(self.view):
            self.view.run_command('insert_snippet',
                                  {'contents': get_syntax_def_boilerplate()})


# XXX: Why is this a WindowCommand? Wouldn't it work otherwise in build-systems?
class MakeTmlanguageCommand(sublime_plugin.WindowCommand):
    """Generates a ``.tmLanguage`` file from a ``.JSON-tmLanguage`` syntax def.
    Should be used from a ``.build-system only``.
    """
    # XXX: We whould prevent this from working except if called in a build system.
    # XXX: find out whether .is_enabled() affects build systems at all and
    # make this return always False if it doesn't.
    def is_enabled(self):
        v = self.window.active_view()
        return (v and (has_file_ext(v, '.JSON-tmLanguage')))

    def run(self, **kwargs):
        v = self.window.active_view()
        path = v.file_name()
        if not (os.path.exists(path) and has_file_ext(v, 'JSON-tmLanguage')):
            print "[AAAPackageDev] Not a valid JSON-tmLanguage file. (%s)" % path
            return

        assert os.path.exists(path), "Need a path to a .JSON-tmLanguage file."
        self.make_tmlanguage_grammar(path)

    def make_tmlanguage_grammar(self, json_grammar):
        path, fname = os.path.split(json_grammar)
        grammar_name, ext = os.path.splitext(fname)
        file_regex = r"Error:\s+'(.*?)'\s+.*?\s+line\s+(\d+)\s+column\s+(\d+)"

        if not hasattr(self, 'output_view'):
            # Try not to call get_output_panel until the regexes are assigned
            self.output_view = self.window.get_output_panel("aaa_package_dev")

        # FIXME: Can't get error navigation to work.
        self.output_view.settings().set("result_file_regex", file_regex)
        self.output_view.settings().set("result_base_dir", path)

        # Call get_output_panel a second time after assigning the above
        # settings, so that it'll be picked up as a result buffer
        self.window.get_output_panel("aaa_package_dev")

        with in_one_edit(self.output_view) as edit:
            try:
                with open(json_grammar) as grammar_in_json:
                    tmlanguage = json.load(grammar_in_json)
            except ValueError, e:
                self.output_view.insert(edit, 0, "Error: '%s' %s" % (json_grammar, str(e)))
            else:
                target = os.path.join(path, grammar_name + '.tmLanguage')
                self.output_view.insert(edit, 0, "Writing tmLanguage... (%s)" % target)
                plistlib.writePlist(tmlanguage, target)

        self.window.run_command("show_panel", {"panel": "output.aaa_package_dev"})
