#=============================================================================
# FILE: file_include.py
# AUTHOR:  Shougo Matsushita <Shougo.Matsu at gmail.com>
# License: MIT license
#=============================================================================

import os
import re

import jedi

from deoplete.base.source import Base


class Source(Base):
    def __init__(self, vim):
        Base.__init__(self, vim)

        self.name = 'file/include'
        self.mark = '[FI]'
        self.events = None
        self.is_bytepos = True
        self.min_pattern_length = 0
        self.rank = 500

        self.pyregex = re.compile('(^\s*import\s+|^\s*from\s+)')
        self.pyregex_ignore = re.compile('('
                '^\s*import\s+\S+\s+$' '|'
                '^\s*from\s+\S+\s+$' '|'
                '^\s*from\s+\S+\s+import\s+\S+\s+$' '|'
                '^\s*import\s+\S+\s+\S+.*$' '|'
                '^\s*from\s+\S+\s+import\s+\S+\s+\S+.*$' ')')

    def on_init(self, context):
        if context['filetype'] == 'python':
            script = jedi.Script('import ', 1, len('import '), '')
            script.completions()

    def get_complete_position(self, context):
        if context['filetype'] != 'python':
            return self.vim.call(
                'neoinclude#file_include#get_complete_position', context['input'])
        else:
            return len(context['input'])

    def gather_candidates(self, context):
        if context['filetype'] != 'python':
            return self.vim.call(
                'neoinclude#file_include#get_include_files', context['input'])
        else:
            return self.gather_python_candidates(context)

    def gather_python_candidates(self, context):
        current_line = context.get('input', None)

        if current_line is None:
            return []
        if not self.pyregex.match(current_line):
            return []
        if self.pyregex_ignore.match(current_line):
            return []

        script = jedi.Script(current_line, 1, len(current_line), '')
        completions = script.completions()

        candidates = []
        for completion in completions:
            candidates.append({
                'word': completion.name,
                'kind': 'jedi'})
        candidates = sorted(candidates, key=lambda x: x['word'].swapcase())

        return candidates
