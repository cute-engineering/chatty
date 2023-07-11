import sys
import hashlib

# === Utils ================================================================== #


class ScanError(Exception):
    where: int
    what: str

    def __init__(self, where: int, what: str):
        self.where = where
        self.what = what


class Tok:
    start: int
    end: int
    text: str

    def __init__(self, start: int, end: int, text: str):
        self.start = start
        self.end = end
        self.text = text


class Scan:
    _src: str
    _start: int
    _off: int
    _save: list[int]

    def __init__(self, src: str, off: int = 0):
        self._src = src
        self._off = 0
        self._start = 0
        self._save = []

    def curr(self) -> str:
        if self.eof():
            return '\0'
        return self._src[self._off]

    def next(self) -> str:
        if self.eof():
            return '\0'
        self._off += 1
        return self.curr()

    def rev(self, off: int = 1) -> str:
        if self._off - off < 0:
            return '\0'
        self._off -= off
        return self.curr()

    def peek(self, off: int = 1) -> str:
        if self._off + off >= len(self._src):
            return '\0'
        return self._src[self._off + off]

    def eof(self) -> bool:
        return self._off >= len(self._src)

    def skipStr(self, s: str) -> bool:
        if self._src[self._off:].startswith(s):
            self._off += len(s)
            return True
        return False

    def isStr(self, s: str) -> bool:
        self.save()
        if self.skipStr(s):
            self.restore()
            return True
        self.restore()
        return False

    def save(self) -> None:
        self._save.append(self._off)

    def restore(self) -> None:
        self._off = self._save.pop()

    def begin(self) -> None:
        self._start = self._off

    def end(self) -> Tok:
        return Tok(self._start, self._off, self._src[self._start:self._off])

    def skipWhitespace(self) -> bool:
        result = False
        while not self.eof() and self.curr().isspace():
            self.next()
            result = True
        return result

    def skipSeparator(self, sep: str) -> bool:
        self.save()
        self.skipWhitespace()
        if self.skipStr(sep):
            self.skipWhitespace()
            return True
        self.restore()
        return False

    def isSeparator(self, sep: str) -> bool:
        self.save()
        self.skipWhitespace()
        if self.skipStr(sep):
            self.skipWhitespace()
            self.restore()
            return True
        self.restore()
        return False

    def expectSeparator(self, sep: str) -> None:
        if not self.skipSeparator(sep):
            self.error(f"Expected separator '{sep}'")

    def skipKeyword(self, keyword: str) -> bool:
        self.save()
        self.skipWhitespace()
        if self.skipStr(keyword) and not self.curr().isalnum():
            self.skipWhitespace()
            return True
        self.restore()
        return False

    def isKeyword(self, keyword: str) -> bool:
        self.save()
        self.skipWhitespace()
        if self.skipStr(keyword) and not self.curr().isalnum():
            self.restore()
            return True
        self.restore()
        return False

    def expectKeyword(self, keyword: str) -> None:
        if not self.skipKeyword(keyword):
            self.error(f"Expected keyword '{keyword}'")

    def error(self, what: str) -> None:
        raise ScanError(self._off, what)

# === AST ==================================================================== #


class Node:
    pass


class Func(Node):
    name: str
    args: list[tuple[str, str]]
    res: str

    def id(self):
        return hashlib.md5(self.name.encode()).hexdigest()[0:16]


class Iface(Node):
    name: str
    funcs: dict[str, Func]

    def id(self):
        return hashlib.md5(self.name.encode()).hexdigest()[0:16]


class Module(Node):
    name: str
    includes: list[str]
    ifaces: dict[str, Iface]

# === Parser ================================================================= #


def parseIdent(s: Scan) -> Tok:
    """
    Exemple:
    foo
    """
    s.skipWhitespace()
    if not s.curr().isalpha():
        s.error("Expected identifier")
        assert False  # unreachable
    s.begin()
    while s.curr().isalnum() or s.curr() == '_' or s.curr() == ':' or s.curr() == '<' or s.curr() == '>':
        s.next()
    ident = s.end()
    s.skipWhitespace()
    return ident


def parseQuotes(s: Scan) -> tuple[str, bool]:
    """
    Exemple:
    'foo'
    '''foo'''
    "foo"
    ""Hello""
    """
    if not s.curr() in ['"', "'"]:
        s.error("Expected quotes")
        assert False  # unreachable
    s.begin()
    first = s.curr()
    while s.curr() == first:
        s.next()
    quotes: str = s.end().text
    return (quotes, len(quotes) > 1)


def parseString(s: Scan) -> Tok:
    """
    Exemple:
    'foo'
    '''foo'''
    "foo"
    ""Hello, "World"!""
    '\n'
    '\\'
    """
    quotes, raw = parseQuotes(s)
    s.begin()
    while not s.eof() and not s.isStr(quotes):
        if s.curr() == '\\' and not raw:
            s.next()
            if s.eof():
                s.error("Expected escape sequence")
                assert False  # unreachable
        s.next()
    t = s.end()
    s.skipStr(quotes)
    return t


def parseFunc(s: Scan) -> Func:
    f = Func()
    f.name = parseIdent(s).text
    s.expectSeparator("(")
    f.args = []
    while not s.skipSeparator(")"):
        f.args.append((parseIdent(s).text, parseIdent(s).text))
        s.skipSeparator(",")

    s.expectSeparator("->")
    f.res = parseIdent(s).text
    return f


def parseIface(s: Scan) -> Iface:
    iface = Iface()
    iface.name = parseIdent(s).text
    s.expectSeparator("{")
    iface.funcs = {}
    while not s.skipSeparator("}"):
        f = parseFunc(s)
        iface.funcs[f.name] = f
    return iface


def parseModule(s: Scan) -> Module:
    module = Module()
    s.expectKeyword("module")
    module.name = parseIdent(s).text
    module.includes = []
    while s.skipKeyword("include"):
        module.includes.append(parseString(s).text)
    module.ifaces = {}
    while not s.eof():
        iface = parseIface(s)

        module.ifaces[iface.name] = iface
    return module

# === C++ Codegen ============================================================ #


# --- Header ----------------------------------------------------------------- #

def genVirtualFunc(f: Func) -> str:
    return f"virtual {f.res} {f.name}({', '.join([f'{t} {n}' for t, n in f.args])}) = 0;"


def genVirtualFuncs(iface: Iface) -> str:
    return '\n'.join([genVirtualFunc(f) for f in iface.funcs.values()])


def genVirtualClass(iface: Iface) -> str:
    return f"""
struct I{iface.name}
{{
    static constexpr auto _UID = 0x{iface.id()};
    static constexpr auto _NAME = "{iface.name}";

    template <typename T>
    struct _Client;

    template <typename R>
    auto _dispatch(R &r);

    virtual ~I{iface.name}() = default;
    {genVirtualFuncs(iface)}
}};
"""


def genVirtualIfaces(ifaces: dict[str, Iface]) -> str:
    return '\n'.join([genVirtualClass(iface) for iface in ifaces.values()])


def genClientFunc(iface: Iface, f: Func) -> str:
    return f"""
{f.res} {f.name}({', '.join([f'{t} {n}' for t, n in f.args])})
{{
    return _t.template invoke<I{iface.name}, 0x{f.id()}, {f.res}({', '.join([t for t, _ in f.args])})>({', '.join([n for _, n in f.args])});
}}
"""


def genClientFuncs(iface: Iface) -> str:
    return '\n'.join([genClientFunc(iface, f) for f in iface.funcs.values()])


def genClientClass(iface: Iface) -> str:
    return f"""
template <typename T>
struct I{iface.name}::_Client : public I{iface.name}
{{
    T _t;

    _Client(T t) : _t{{t}} {{}}

    {genClientFuncs(iface)}
}};
"""


def genClientIfaces(ifaces: dict[str, Iface]) -> str:
    return '\n'.join([genClientClass(iface) for iface in ifaces.values()])


def genDispatchCase(iface: Iface, f: Func) -> str:
    return f"""
case 0x{f.id()}:
{{
    return r.reply({f.name}({', '.join([f'r.template get<{t}>()' for t, _ in f.args])}));
}}
"""


def genDispatchCases(iface: Iface) -> str:
    return '\n'.join([genDispatchCase(iface, f) for f in iface.funcs.values()])


def genDispatchFunc(iface: Iface) -> str:
    return f"""
template <typename R>
auto I{iface.name}::_dispatch(R &r)
{{
    switch (r.id())
    {{
        {genDispatchCases(iface)}
        default: return r.error();
    }}
}}
"""


def genDispatchFuncs(ifaces: dict[str, Iface]) -> str:
    return '\n'.join([genDispatchFunc(iface) for iface in ifaces.values()])


def genIncludes(includes: list[str]) -> str:
    return '\n'.join([f'#include <{i}>' for i in includes])

# === Main =================================================================== #


def main() -> int:
    with open(sys.argv[1], "r") as inFile:
        with open(sys.argv[2], "w") as outFile:
            s = Scan(inFile.read())
            module = parseModule(s)
            print(f"#pragma once", file=outFile)
            print(f"// {sys.argv[1]}", file=outFile)
            print(genIncludes(module.includes), file=outFile)
            print(genVirtualIfaces(module.ifaces), file=outFile)
            print(genClientIfaces(module.ifaces), file=outFile)
            print(genDispatchFuncs(module.ifaces), file=outFile)

    return 0
