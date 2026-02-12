#!/usr/bin/env python3

import re

COMMAND_PREFIX = "gettextmath"


def generate_command_call(name, prefix, *args):
    return "\\" + prefix + name + "{" + "}{".join(args) + "}"


class Parser:
    class Token:
        function = False

        def process(self, stack, output):
            output.append(self)

        def consume(self, stack):
            stack.append(self)

        def __repr__(self):
            return str(self)

    class Number(Token):
        def __init__(self, number):
            self.number = int(number)

        def generate(self):
            return str(self.number)

        def __eq__(self, other):
            return isinstance(other, Parser.Number) and self.number == other.number

        def __str__(self):
            return f"Number({self.number})"

    class Identifier(Token):
        def __init__(self, identifier):
            self.identifier = identifier

        def generate(self):
            return self.identifier

        def __eq__(self, other):
            return (
                isinstance(other, Parser.Identifier)
                and self.identifier == other.identifier
            )

        def __str__(self):
            return f'Identifier("{self.identifier}")'

    class Operator(Token):
        function = True

        def __init__(self, operation):
            self.operation = operation

        def process(self, stack, output):
            while len(stack) > 0 and stack[len(stack) - 1].priority < self.priority:
                output.append(stack.pop())
            stack.append(self)

        def __eq__(self, other):
            return type(self) is type(other) and self.operation == other.operation

        def __str__(self):
            return f'Operator("{self.operation}")'

    class BinaryOperator(Operator):
        def consume(self, stack):
            self.arg2 = stack.pop()
            self.arg1 = stack.pop()
            stack.append(self)

        def generate(self):
            return generate_command_call(
                self.command, COMMAND_PREFIX, self.arg1.generate(), self.arg2.generate()
            )

    class OperatorEqual(BinaryOperator):
        priority = 7
        command = "equal"

    class OperatorNotEqual(BinaryOperator):
        priority = 7
        command = "notequal"

    class OperatorGreaterEqual(BinaryOperator):
        priority = 6
        command = "greaterequal"

    class OperatorLesserEqual(BinaryOperator):
        priority = 6
        command = "lesserequal"

    class OperatorGreaterThan(BinaryOperator):
        priority = 6
        command = "greaterthan"

    class OperatorLesserThan(BinaryOperator):
        priority = 6
        command = "lesserthan"

    class OperatorAnd(BinaryOperator):
        priority = 11
        command = "and"

    class OperatorOr(BinaryOperator):
        priority = 12
        command = "or"

    class OperatorModulo(BinaryOperator):
        priority = 3
        command = "modulo"

    class OperatorTernaryStart(Operator):
        priority = 100
        function = False

        def consume(self, stack):
            self.arg_truefalse = stack.pop()
            self.arg_condition = stack.pop()
            if not isinstance(self.arg_truefalse, Parser.OperatorTernaryMiddle):
                raise Exception(
                    f'Operator "?" must have matching ":", but "{self.arg_truefalse}" found'  # noqa: E501
                )
            stack.append(self)

        def generate(self):
            return generate_command_call(
                "ifthenelse",
                COMMAND_PREFIX,
                self.arg_condition.generate(),
                self.arg_truefalse.true.generate(),
                self.arg_truefalse.false.generate(),
            )

    class OperatorTernaryMiddle(Operator):
        priority = 100
        function = False

        def consume(self, stack):
            self.false = stack.pop()
            self.true = stack.pop()
            stack.append(self)

    class OpenParenthesis(Token):
        priority = 100

        def process(self, stack, output):
            stack.append(self)

        def __str__(self):
            return "OpenParenthesis"

    class CloseParenthesis(Token):
        priority = 100

        def process(self, stack, output):
            while len(stack) > 0 and not isinstance(
                stack[len(stack) - 1], Parser.OpenParenthesis
            ):
                x = stack.pop()
                output.append(x)
            open = stack.pop()
            if not isinstance(open, Parser.OpenParenthesis):
                raise Exception("Could not find matching left parenthesis")
            if len(stack) > 0 and stack[len(stack) - 1].function:
                output.append(stack.pop())

        def __str__(self):
            return "CloseParenthesis"

    def __init__(self, source):
        self.source = source
        self.overriden_identifiers = {}
        self.tokens = [
            # boolean operations
            (re.compile(r"^(==)"), self.OperatorEqual),
            (re.compile(r"^(!=)"), self.OperatorNotEqual),
            (re.compile(r"^(>=)"), self.OperatorGreaterEqual),
            (re.compile(r"^(<=)"), self.OperatorLesserEqual),
            (re.compile(r"^(>)"), self.OperatorGreaterThan),
            (re.compile(r"^(<)"), self.OperatorLesserThan),
            (re.compile(r"^(&&)"), self.OperatorAnd),
            (re.compile(r"^(\|\|)"), self.OperatorOr),
            (re.compile(r"^(\?)"), self.OperatorTernaryStart),
            (re.compile(r"^(:)"), self.OperatorTernaryMiddle),
            # arithmentic operations
            (re.compile(r"^(%)"), self.OperatorModulo),
            # parenthesis
            (re.compile(r"^\("), self.OpenParenthesis),
            (re.compile(r"^\)"), self.CloseParenthesis),
            # others
            (re.compile(r"^([0-9]+)"), self.Number),
            (re.compile(r"^([_A-Za-z][_A-Za-z0-9]*)"), self.Identifier),
            (re.compile(r"^\s+"), None),
        ]

    def override_identifier(self, old_identifier, new_identifier):
        self.overriden_identifiers[old_identifier] = new_identifier

    def parse(self):
        source = self.source
        output = []
        stack = []
        while len(source) > 0:
            for i in self.tokens:
                m = i[0].match(source)
                if m:
                    break
            if not m:
                raise Exception(f'No token matches "{source[:10]}<...>"')

            source = source[len(m.group(0)) :]
            token = i[1]
            if not token:
                continue
            args = m.groups()
            token = token(*args)
            token = token.process(stack, output)
        while len(stack) > 0:
            output.append(stack.pop())
        o = []
        for i in output:
            if isinstance(i, Parser.Identifier):
                o.append(
                    Parser.Identifier(
                        self.overriden_identifiers.get(i.identifier, i.identifier)
                    )
                )
            else:
                o.append(i)
        output = o
        return output


class Generator:
    def __init__(self, queue):
        self.queue = queue

    def generate(self):
        stack = []
        for i in self.queue:
            i.consume(stack)
        if len(stack) != 1:
            raise Exception(f"RPN processing problem, stack size is not 1 ({stack!r})")
        r = stack[0]
        r = r.generate()
        return r


def generate_command(name, source, new_command=True):
    s = "\\newcommand" if new_command else "\\renewcommand"
    s += "{" + name + "}[1]{"
    parser = Parser(source)
    parser.override_identifier("n", "#1")
    s += Generator(parser.parse()).generate()
    s += "}"
    return s
