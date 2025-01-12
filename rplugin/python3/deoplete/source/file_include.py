#=============================================================================
# FILE: file_include.py
# AUTHOR:  Shougo Matsushita <Shougo.Matsu at gmail.com>
# MODIFIED: LittleBird
# License: MIT license
#=============================================================================

import jedi
import os
import re
import sys

from deoplete.base.source import Base


class Source(Base):
    def __init__(self, vim):
        Base.__init__(self, vim)

        self.name = 'include'
        self.mark = '[I]'
        self.events = None
        self.is_bytepos = True
        self.min_pattern_length = 0
        self.rank = 500

        self.ignore_dirs = set(['.git'])

        self.clang_includes = dict()
        self.clang_pattern = re.compile(r'^\s*#\s*include\s*[<"]([^>"]*)')
        self.clangregex = re.compile(r'^\s*#\s*include\s*[<"]')
        self.clangregex_ignore = re.compile(r'^\s*#\s*include\s*[<"].*[>"].*$')

        self.pyregex = re.compile(r'(^\s*import\s+|^\s*from\s+)')
        self.pyregex_ignore = re.compile('('
                r'^\s*import\s+\S+\s+$' '|'
                r'^\s*from\s+\S+\s+$' '|'
                r'^\s*from\s+\S+\s+import\s+\S+\s+$' '|'
                r'^\s*import\s+\S+\s+\S+.*$' '|'
                r'^\s*from\s+\S+\s+import\s+\S+\s+\S+.*$' ')')

    def on_init(self, context):
        self.vim.call('neoinclude#initialize')

    def on_event(self, context):
        if context['filetype'] == 'python':
            current_filepath = self.vim.call('expand', '%:p')
            try:
                script = jedi.Script('import ', 1, len('import '), current_filepath)
                script.completions()
            except:
                pass

        elif context['filetype'] in ['c', 'cpp', 'cuda']:
            self.vim.call('neoinclude#set_filetype_paths', context['bufnr'], context['filetype'])

            relative_paths = [self.vim.call('getcwd'), self.vim.call('expand', '%:p:h')]
            paths = self.vim.call('neoinclude#get_path', context['bufnr'], context['filetype'])
            paths = [x for x in paths.split(',') if x != '' and x != '.' and x != '*' and x != '**']
            paths = relative_paths + paths

            ft = context['filetype']
            exts = {
                'c': ['.h'],
                'cpp': ['', '.h', '.hpp', '.hxx'],
                'cuda': ['', '.h', '.hpp', '.hxx']
            }

            self.build_clang_cache(ft, exts[ft], paths)

        else:
            pass

    def build_clang_cache(self, filetype, exts, paths):
        if self.clang_includes:
            return

        self.clang_includes = dict()
        self.clang_includes[''] = list()
        for path in paths:
            visited = set()
            for root, dirs, files in os.walk(path, followlinks=True):
                if root in visited:
                    continue
                visited.add(root)

                ignored = False
                for split in root.split('/'):
                    if split in self.ignore_dirs:
                        ignored = True
                        break
                if ignored:
                    continue

                for fn in files:
                    ext = os.path.splitext(fn)[1]
                    if ext not in exts:
                        continue

                    fp = os.path.join(root, fn)
                    fp = fp.replace(path, '', 1)
                    if fp.startswith('/'):
                        fp = fp[1:]

                    tokens = fp.split('/')
                    node = self.clang_includes
                    for token in tokens[:-1]:
                        if token not in node:
                            node[token] = dict()
                            node[token][''] = list()
                        node = node[token]
                    node[''].append(tokens[-1])

    def get_complete_position(self, context):
        if context['filetype'] == 'python':
            return len(context['input'])
        elif context['filetype'] in ['c', 'cpp', 'cuda']:
            pos = context['input'].rfind('/')
            if pos != -1:
                return pos + 1
            matches = self.clangregex.match(context['input'])
            if matches:
                return len(matches.group(0))
            else:
                return -1
        else:
            return self.vim.call(
                'neoinclude#file_include#get_complete_position', context['input'])

    def gather_candidates(self, context):
        if context['filetype'] == 'python':
            return self.gather_python_candidates(context)
        elif context['filetype'] in ['c', 'cpp', 'cuda']:
            return self.gather_clang_candidates(context)
        else:
            return self.vim.call(
                'neoinclude#file_include#get_include_files', context['input'])

    def gather_python_candidates(self, context):
        current_line = context.get('input', None)

        if current_line is None:
            return list()
        if not self.pyregex.match(current_line):
            return list()
        if self.pyregex_ignore.match(current_line):
            return list()

        current_filepath = self.vim.call('expand', '%:p')
        try:
            script = jedi.Script(current_line, 1, len(current_line), current_filepath)
            completions = script.completions()
        except:
            completions = list()

        candidates = list()
        for completion in completions:
            candidates.append({
                'word': completion.name,
                'kind': 'jedi'})
        candidates = sorted(candidates, key=lambda x: x['word'].swapcase())

        return candidates

    def gather_clang_candidates(self, context):
        current_line = context.get('input', None)

        if current_line is None:
            return list()
        if not self.clangregex.match(current_line):
            return list()
        if self.clangregex_ignore.match(current_line):
            return list()

        matches = self.clang_pattern.match(current_line)
        if not matches:
            return list()

        candidates = list()
        tokens = matches.group(1).split('/')

        node = self.clang_includes
        for token in tokens[:-1]:
            if token in node and token != '':
                node = node[token]
            else:
                return list()
        files = sorted(list(node['']), key=lambda x: x.swapcase())
        dirs = sorted(list(node.keys()), key=lambda x: x.swapcase())[1:]

        for word in files:
            candidates.append({
                'word': word,
                'abbr': word,
                'kind': 'file'})
        for word in dirs:
            candidates.append({
                'word': word,
                'abbr': word + '/',
                'kind': 'dir'})

        return candidates
