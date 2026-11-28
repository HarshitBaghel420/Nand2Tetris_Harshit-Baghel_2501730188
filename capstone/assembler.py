#!/usr/bin/env python3
"""
assembler.py - A Hack assembler in Python (Nand2Tetris capstone, Part B).

Turns a Hack program (.asm) into machine code (.hack).

Two-pass design:
  Pass 1 - strip comments and blank lines, and record every label (LOOP)
           with the ROM address of its (LOOP) declaration.
  Pass 2 - translate each line into 16 bits. New variable names get
           RAM addresses 16, 17, 18, ...

Extra feature (my K = 88; K mod 3 = 1):
  A wrong line prints a clear message with the line number
  (e.g. "Line 7: invalid instruction 'D;JMX'") and assembly aborts with an
  error code, instead of the program crashing.

Usage:
  python assembler.py Prog.asm                 # writes Prog.hack
  python assembler.py Prog.asm Out.hack        # writes to Out.hack
"""

import sys
import re

# ---------------------------------------------------------------------------
# C-instruction tables (comp, dest, jump).
# comp is stored with the a-bit as the first character.
# ---------------------------------------------------------------------------
COMP_TABLE = {
    "0":   "0101010", "1":   "0111111", "-1":  "0111010",
    "D":   "0001100", "A":   "0110000", "!D":  "0001101",
    "!A":  "0110001", "-D":  "0001111", "-A":  "0110011",
    "D+1": "0011111", "A+1": "0110111", "D-1": "0001110",
    "A-1": "0110010", "D+A": "0000010", "D-A": "0010011",
    "A-D": "0000111", "D&A": "0000000", "D|A": "0010101",
    # with a-bit = 1 (y = M)
    "M":   "1110000", "!M":  "1110001", "-M":  "1110011",
    "M+1": "1110111", "M-1": "1110010", "D+M": "1000010",
    "D-M": "1010011", "M-D": "1000111", "D&M": "1000000",
    "D|M": "1010101",
}

DEST_TABLE = {
    "":   "000", "M":   "001", "D":   "010", "MD":  "011",
    "A":  "100", "AM":  "101", "AD":  "110", "AMD": "111",
}

JUMP_TABLE = {
    "":    "000", "JGT": "001", "JEQ": "010", "JGE": "011",
    "JLT": "100", "JNE": "101", "JLE": "110", "JMP": "111",
}

# ---------------------------------------------------------------------------
# Symbol table: predefined symbols plus labels and variables collected below.
# ---------------------------------------------------------------------------
SYMBOL_TABLE = {
    "SP":        0, "LCL":       1, "ARG":       2, "THIS":      3,
    "THAT":      4, "R0":        0, "R1":        1, "R2":        2,
    "R3":        3, "R4":        4, "R5":        5, "R6":        6,
    "R7":        7, "R8":        8, "R9":        9, "R10":      10,
    "R11":      11, "R12":      12, "R13":      13, "R14":      14,
    "R15":      15, "SCREEN": 16384, "KBD":    24576,
}

# ---------------------------------------------------------------------------
# Helpers for the error feature: we print the whole line for context.
# ---------------------------------------------------------------------------
class AssembleError(Exception):
    """Raised when a line cannot be assembled. Carries the 1-based source
    line number (counting non-blank, non-label program lines) and the text."""

    def __init__(self, line_no, message):
        super().__init__(message)
        self.line_no = line_no
        self.message = message


def clean(lines):
    """Strip comments and blank lines; keep labels with a marker.

    Returns a list of (kind, text, src_line) where kind is 'label' or
    'line' and src_line is the 1-based line number in the original source
    (used by the error feature), plus a list of label errors found.
    A '/' in a string is never a comment in Hack assembly, so we cut at the
    first "//".
    """
    clean_lines = []
    label_errors = []
    for i, raw in enumerate(lines, start=1):
        hash_idx = raw.find("//")
        if hash_idx != -1:
            raw = raw[:hash_idx]
        text = raw.strip()
        if not text:
            continue
        if text.startswith("(") and text.endswith(")"):
            # A label declaration must be a valid symbol name.
            name = text[1:-1]
            if not re.match(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$", name):
                label_errors.append(
                    AssembleError(i, "invalid label '(%s)'" % name))
                continue
            clean_lines.append(("label", text, i))
        else:
            clean_lines.append(("line", text, i))
    return clean_lines, label_errors


def pass1(clean_lines):
    """Record the ROM address of every label in the symbol table."""
    rom = 0
    for kind, text, _src in clean_lines:
        if kind == "label":
            name = text[1:-1]
            if name in SYMBOL_TABLE:
                raise AssembleError(_src, "duplicate label '(%s)'" % name)
            SYMBOL_TABLE[name] = rom
        else:
            rom += 1


def a_instruction(text, line_no):
    """Assemble an @value / @symbol A-instruction to 16 bits."""
    value_s = text[1:].strip()
    if value_s.startswith("-"):
        raise AssembleError(line_no,
            "invalid instruction '%s' (negative A-address)" % text)
    if value_s.isdigit():
        value = int(value_s)
        if value > 32767:
            raise AssembleError(line_no,
                "number too large in '%s' (max %d)" % (text, 32767))
        return "{0:016b}".format(value)
    # A symbol: predefined, a label, or a new variable -> RAM 16, 17, ...
    if not re.match(r"^[A-Za-z_.$:][A-Za-z0-9_.$:]*$", value_s):
        raise AssembleError(line_no,
            "invalid A-instruction '%s'" % text)
    if value_s in SYMBOL_TABLE:
        value = SYMBOL_TABLE[value_s]
    else:
        # New variable. We look for the next free RAM slot.
        value = _next_variable()
        SYMBOL_TABLE[value_s] = value
    return "{0:016b}".format(value)


_next = [16]

def _next_variable():
    n = _next[0]
    _next[0] += 1
    return n


def c_instruction(text, line_no):
    """Assemble a C-instruction 'dest=comp;jump' to 16 bits."""
    dest = ""
    comp = ""
    jump = ""

    part = text
    if ";" in part:
        part, jump = part.split(";", 1)
        jump = jump.strip()
        if jump not in JUMP_TABLE:
            raise AssembleError(line_no,
                "invalid instruction '%s' (unknown jump '%s')" % (text, jump))
        jump = JUMP_TABLE[jump]
    else:
        jump = "000"

    if "=" in part:
        dest, comp = part.split("=", 1)
        dest = dest.strip()
        comp = comp.strip()
        if comp not in COMP_TABLE:
            raise AssembleError(line_no,
                "invalid instruction '%s' (unknown computation '%s')"
                % (text, comp))
        if dest not in DEST_TABLE:
            raise AssembleError(line_no,
                "invalid instruction '%s' (unknown destination '%s')"
                % (text, dest))
        dest = DEST_TABLE[dest]
    else:
        comp = part.strip()
        if comp not in COMP_TABLE:
            raise AssembleError(line_no,
                "invalid instruction '%s' (unknown computation '%s')"
                % (text, comp))
        dest = "000"

    bits = "111" + COMP_TABLE[comp] + dest + jump
    return bits


def assemble_line(text, line_no):
    if text.startswith("@"):
        return a_instruction(text, line_no)
    return c_instruction(text, line_no)


def assemble(source_text, out_path=None):
    """Assemble source_text. Returns the list of 16-bit lines, writing them
    to out_path when given.

    Extra feature (K mod 3 = 1): every bad line is reported (in source order)
    instead of stopping at the first; when there are any errors, no .hack
    file is written. Callers should check the error list returned.
    """
    global _next
    _next[0] = 16
    lines = source_text.splitlines()
    clean_lines, label_errors = clean(lines)

    # Pass 1: collect all labels.
    try:
        pass1(clean_lines)
    except AssembleError as e:
        label_errors.append(e)

    # Pass 2: assemble every line, collecting errors (not stopping).
    errors = list(label_errors)
    result = []
    for kind, text, src in clean_lines:
        if kind == "label":
            continue
        try:
            result.append(assemble_line(text, src))
        except AssembleError as e:
            errors.append(e)

    if errors:
        # Return the sorted errors; do not write anything.
        return sorted(errors, key=lambda e: e.line_no)

    if out_path:
        with open(out_path, "w") as f:
            for bits in result:
                f.write(bits + "\n")
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main(argv):
    if len(argv) < 2:
        print("usage: python assembler.py Prog.asm [Out.hack]")
        return 2
    in_path = argv[1]
    out_path = argv[2] if len(argv) > 2 else in_path[:-4] + ".hack"
    try:
        with open(in_path) as f:
            source = f.read()
    except OSError as e:
        print("error: cannot read '%s': %s" % (in_path, e.strerror))
        return 1

    result = assemble(source, out_path)
    if result and isinstance(result[0], AssembleError):
        # Extra feature: report every bad line, in source order.
        for e in result:
            print("Line %d: %s" % (e.line_no, e.message))
        print("%d error(s) found, %s was not written." % (len(result), out_path))
        return 1

    print("Wrote %d instructions to %s" % (len(result), out_path))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))