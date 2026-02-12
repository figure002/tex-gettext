import re
import subprocess
import sys
import unittest

from tex_gettext.tex_math import Parser, generate_command


class TestMath(unittest.TestCase):
    def test_parser(self):
        exprs = [
            (
                "0",
                [
                    Parser.Number(0),
                ],
            ),
            (
                "1",
                [
                    Parser.Number(1),
                ],
            ),
            (
                "01",
                [
                    Parser.Number(1),
                ],
            ),
            ("0 1", [Parser.Number(0), Parser.Number(1)]),
            (
                "0 == 1",
                [Parser.Number(0), Parser.Number(1), Parser.OperatorEqual("==")],
            ),
            (
                "0%2 == 1",
                [
                    Parser.Number(0),
                    Parser.Number(2),
                    Parser.OperatorModulo("%"),
                    Parser.Number(1),
                    Parser.OperatorEqual("=="),
                ],
            ),
            (
                "0 == 1%2",
                [
                    Parser.Number(0),
                    Parser.Number(1),
                    Parser.Number(2),
                    Parser.OperatorModulo("%"),
                    Parser.OperatorEqual("=="),
                ],
            ),
            (
                "0 ? 1 : 2",
                [
                    Parser.Number(0),
                    Parser.Number(1),
                    Parser.Number(2),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                ],
            ),
            (
                "3 ? 4 : 5 ? 1 : 2",
                [
                    Parser.Number(3),
                    Parser.Number(4),
                    Parser.Number(5),
                    Parser.Number(1),
                    Parser.Number(2),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                ],
            ),
            (
                "3%6 ? 4%7 : 5%8 ? 1%9 : 2%10",
                [
                    Parser.Number(3),
                    Parser.Number(6),
                    Parser.OperatorModulo("%"),
                    Parser.Number(4),
                    Parser.Number(7),
                    Parser.OperatorModulo("%"),
                    Parser.Number(5),
                    Parser.Number(8),
                    Parser.OperatorModulo("%"),
                    Parser.Number(1),
                    Parser.Number(9),
                    Parser.OperatorModulo("%"),
                    Parser.Number(2),
                    Parser.Number(10),
                    Parser.OperatorModulo("%"),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                ],
            ),
            (
                "n?0:a?1:2",
                [
                    Parser.Identifier("n"),
                    Parser.Number(0),
                    Parser.Identifier("a"),
                    Parser.Number(1),
                    Parser.Number(2),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                ],
            ),
            (
                "n?0:(a)?1:2",
                [
                    Parser.Identifier("n"),
                    Parser.Number(0),
                    Parser.Identifier("a"),
                    Parser.Number(1),
                    Parser.Number(2),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                ],
            ),
            (
                "n==1 ? 0 : (a || b) ? 1 : 2",
                [
                    Parser.Identifier("n"),
                    Parser.Number(1),
                    Parser.OperatorEqual("=="),
                    Parser.Number(0),
                    Parser.Identifier("a"),
                    Parser.Identifier("b"),
                    Parser.OperatorOr("||"),
                    Parser.Number(1),
                    Parser.Number(2),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                    Parser.OperatorTernaryMiddle(":"),
                    Parser.OperatorTernaryStart("?"),
                ],
            ),
        ]

        for i in exprs:
            parser = Parser(i[0])
            self.assertEqual(
                i[1], parser.parse(), f'expression parsed incorrectly: "{i[0]}"'
            )

    def test_calculations(self):
        functions = [
            ("0", lambda _: 0),
            ("n != 1", lambda n: int(n != 1)),
            ("n>1", lambda n: int(n > 1)),
            ("n>1 ? 1 : 0", lambda n: 1 if n > 1 else 0),
            (
                "n==0 ? 10 : n==1 ? 11 : 12",
                lambda n: 10 if n == 0 else (11 if n == 1 else 12),
            ),
            (
                "n%10==1 && n%100!=11 ? 0 : n != 0 ? 1 : 2",
                lambda n: 0 if n % 10 == 1 and n % 100 != 11 else (1 if n != 0 else 2),
            ),
            (
                "n==1 ? 0 : n==2 ? 1 : 2",
                lambda n: 0 if n == 1 else (1 if n == 2 else 2),
            ),
            (
                "n==1 ? 0 : (n==0 || (n%100 > 0 && n%100 < 20)) ? 1 : 2",
                lambda n: (
                    0
                    if n == 1
                    else (1 if (n == 0 or (n % 100 > 0 and n % 100 < 20)) else 2)
                ),
            ),
            (
                "n%10==1 && n%100!=11 ? 0 :  n%10>=2 && (n%100<10 || n%100>=20) ? 1 : 2",  # noqa: E501
                lambda n: (
                    0
                    if n % 10 == 1 and n % 100 != 11
                    else (1 if n % 10 >= 2 and (n % 100 < 10 or n % 100 >= 20) else 2)
                ),
            ),
            (
                "n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2",  # noqa: E501
                lambda n: (
                    0
                    if n % 10 == 1 and n % 100 != 11
                    else (
                        1
                        if n % 10 >= 2
                        and n % 10 <= 4
                        and (n % 100 < 10 or n % 100 >= 20)
                        else 2
                    )
                ),
            ),
            (
                "(n==1) ? 0 : (n>=2 && n<=4) ? 1 : 2",
                lambda n: 0 if n == 1 else (1 if n >= 2 and n <= 4 else 2),
            ),
            (
                "n==1 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2",
                lambda n: (
                    0
                    if n == 1
                    else (
                        1
                        if n % 10 >= 2
                        and n % 10 <= 4
                        and (n % 100 < 10 or n % 100 >= 20)
                        else 2
                    )
                ),
            ),
            (
                "n%100==1 ? 0 : n%100==2 ? 1 : n%100==3 || n%100==4 ? 2 : 3",
                lambda n: (
                    0
                    if n % 100 == 1
                    else (
                        1
                        if n % 100 == 2
                        else (2 if n % 100 == 3 or n % 100 == 4 else 3)
                    )
                ),
            ),
        ]

        re_text = re.compile(r"<text(.*?)>(.*?)</text>", re.DOTALL)
        re_tspan = re.compile(r"</?tspan(.*?)>", re.DOTALL)

        TEST_FILE_PREFIX = "_test"

        for i in functions:
            sys.stderr.write("*")
            sys.stderr.flush()
            for n in range(0, 3):
                sys.stderr.write(".")
                sys.stderr.flush()
                with open(TEST_FILE_PREFIX + ".tex", "w") as f:
                    f.write("\\documentclass{article}\n")
                    f.write("\\usepackage{tipa}\n")
                    f.write("\\usepackage{gettext}\n")
                    f.write(generate_command("\\testfn", i[0]))
                    f.write("\n")
                    f.write("\\begin{document}\n")
                    f.write("\\testfn{")
                    f.write(str(n))
                    f.write("}\n")
                    f.write("\\end{document}")
                kwargs = dict(stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                subprocess.check_call(["latex", TEST_FILE_PREFIX + ".tex"], **kwargs)
                subprocess.check_call(["dvisvgm", TEST_FILE_PREFIX + ".dvi"], **kwargs)
                with open(TEST_FILE_PREFIX + ".svg") as f:
                    f = f.read()
                    f = f.replace("\n", "")
                    f = re_text.findall(f)
                    f = [re_tspan.sub(" ", i[1]) for i in f]
                    f = "".join(f)
                    f = f.strip()
                    if f.endswith("1"):  # strip page number
                        f = f[:-1]
                    f = f.strip()
                    f = int(f)

                expected = i[1](n)
                actual = f
                self.assertEqual(expected, actual)
