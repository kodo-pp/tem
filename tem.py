#!/usr/bin/env python

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict
from abc import abstractmethod


@dataclass
class Template:
    template_dir: Path


class Command:
    @abstractmethod
    def run(self) -> None:
        ...


class UseCommand(Command):
    def __init__(self, template_name: str, arguments: Dict[str, str]) -> None:
        self.template_name = template_name
        self.arguments = arguments


    def run(self) -> None:
        # TODO: write the actual code
        ...


class HelpCommand(Command):
    def run(self) -> None:
        print('Usage: tem <command> [args...]')
        print('Available commands with their accepted options:')
        print('    use <template> [key1=value1 [...]]   -- Use a template')
        print('    help                                 -- Display this help message')


class UsageError(Exception):
    def __init__(self, message: str, offer_help: bool = False) -> None:
        self.message = message
        self.offer_help = offer_help


    def __str__(self) -> str:
        if self.offer_help:
            return self.message + '\nFor the list of available commands see `tem help`'
        return self.message


def parse_use_command(args: List[str]) -> UseCommand:
    # TODO: write the actual code
    raise NotImplementedError()


def parse_command(cmdline_args: List[str]) -> Command:
    if len(cmdline_args) < 2:
        raise UsageError('You must specify a command to run', offer_help=True)
    argv0, command, *args = cmdline_args
    del argv0
    if command == 'use':
        return parse_use_command(args)
    if command == 'help':
        return HelpCommand()
    raise UsageError(f'Invalid command: `{command}`', offer_help=True)


def main():
    try:
       command = parse_command(sys.argv)
    except UsageError as e:
        print(e, file=sys.stderr)
        sys.exit(1)

    command.run()


if __name__ == '__main__':
    main()
