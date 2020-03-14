#!/usr/bin/env python

import re
import shutil
import sys
from abc import abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

import yaml


@dataclass
class Template:
    name: str
    template_dir: Path
    files_to_format: List[Path]


class Command:
    @abstractmethod
    def run(self) -> None:
        ...


class TemError(Exception):
    pass


class TemplateDoesNotExist(TemError):
    def __init__(self, template_name: str) -> None:
        super().__init__(f'No such template: {template_name}')


class TemdirDoesNotExist(TemError):
    def __init__(self) -> None:
        super().__init__('`TEMplates` directory does not exist on the current or any upper level')


class InvalidTemplateError(TemError):
    pass


def find_temdir(search_path: Path) -> Path:
    search_path = search_path.resolve()
    temdir_path = search_path / 'TEMplates'

    if temdir_path.is_dir():
        return temdir_path

    # No `TEMplates` dir on the current level
    if search_path == Path('/'):
        # We've looked for `TEMplates` at the highest possible level
        raise TemdirDoesNotExist()
    return find_temdir(search_path / '..')



def find_template(template_name: str, search_path: Path) -> Path:
    temdir_path = find_temdir(search_path)

    template_path = temdir_path / template_name
    if template_path.is_dir():
        return template_path
    raise TemplateDoesNotExist(template_name)


def read_template(path: Path) -> 'Template':
    temfile_path = path / 'Temfile.yml'
    with temfile_path.open() as f:
        template_data = yaml.safe_load(f)

    if not isinstance(template_data, dict):
        raise InvalidTemplateError('Root element must be a dict')

    filenames_to_format = template_data.get('format', [])
    if not isinstance(filenames_to_format, list):
        raise InvalidTemplateError('`format` property must be a list')

    files_to_format: List[Path] = []
    for filename in filenames_to_format:
        if not isinstance(filename, str):
            raise InvalidTemplateError('Each member of `format` property must be a string')
        files_to_format.append(Path(filename))

    return Template(
        name = path.name,
        template_dir = path,
        files_to_format = files_to_format,
    )


def copy_template_files(template_dir: Path, destination: Path) -> None:
    # Files not to copy
    excluded_files = {'Temfile.yml'}

    # TODO: Maybe scan the destination directory for existence of files/dirs
    # to be copied before any copying is actually done. This will ensure that
    # failed (for this reason) copying does not break template's consistency

    for filepath in template_dir.iterdir():
        if filepath.name in excluded_files:
            continue
        if filepath.is_dir():
            shutil.copytree(
                filepath,
                destination / filepath.name,
                symlinks = True,
                ignore_dangling_symlinks = True,
            )
        else:
            shutil.copy(filepath, destination, follow_symlinks=False)


def format_file(filepath: Path, arguments: Dict[str, str]) -> None:
    data = filepath.read_text()
    for key, value in arguments.items():
        replaced_string = f'@@tem:{key}@@'
        replacement = value
        data = data.replace(replaced_string, replacement)
    filepath.write_text(data)


class UseCommand(Command):
    def __init__(self, template_name: str, arguments: Dict[str, str]) -> None:
        self.template_name = template_name
        self.arguments = arguments


    def run(self) -> None:
        template_path = find_template(self.template_name, Path('.'))
        template = read_template(template_path)
        copy_template_files(template.template_dir, Path('.'))
        for filepath in template.files_to_format:
            format_file(filepath, self.arguments)


class ListCommand(Command):
    def run(self) -> None:
        temdir_path = find_temdir(Path('.'))
        for template_path in temdir_path.iterdir():
            template = read_template(template_path)
            print(template.name)


class HelpCommand(Command):
    def run(self) -> None:
        print('Usage: tem <command> [args...]')
        print('Available commands with their accepted options:')
        print('    use <template> [key1=value1 [...]]   -- Use a template')
        print('    list                                 -- List available templates')
        print('    help                                 -- Display this help message')


class UsageError(TemError):
    def __init__(self, message: str, offer_help: bool = False) -> None:
        self.message = message
        self.offer_help = offer_help


    def __str__(self) -> str:
        if self.offer_help:
            return self.message + '\nFor the list of available commands see `tem help`'
        return self.message


def parse_use_command(args: List[str]) -> UseCommand:
    if len(args) < 1:
        raise UsageError('Template name must be specified')

    template_name, *raw_kv_pairs = args

    for char in ['/', '\\', '\x00']:
        if char in template_name:
            raise UsageError(f'Invalid template name: `{template_name}`')

    key_value_args: Dict[str, str] = {}
    for raw_kv_pair in raw_kv_pairs:
        # raw_kv_pair represents a single command line argument that should
        # have the form `key=value`. If it is not so, raise an exception
        key, separator, value = raw_kv_pair.partition('=')
        if separator == '':
            raise UsageError('Template arguments must be `key=value` pairs')

        if re.fullmatch(r'[a-zA-Z0-9_-]+', key) is None:
            raise UsageError(f'Invalid key `{key}`')

        key_value_args[key] = value   # TODO: maybe check for duplicate keys
    return UseCommand(template_name=template_name, arguments=key_value_args)



def parse_command(cmdline_args: List[str]) -> Command:
    if len(cmdline_args) < 2:
        raise UsageError('You must specify a command to run', offer_help=True)
    argv0, command, *args = cmdline_args
    del argv0
    if command == 'use':
        return parse_use_command(args)
    if command == 'list':
        return ListCommand()
    if command == 'help':
        return HelpCommand()
    raise UsageError(f'Invalid command: `{command}`', offer_help=True)


def main():
    try:
        command = parse_command(sys.argv)
        command.run()
    except TemError as e:
        print('Error:', e, file=sys.stderr)
        sys.exit(1)

if __name__ == '__main__':
    main()
