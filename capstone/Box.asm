// Box.asm - Nand to Tetris capstone, Part C. My K = 88.
//
// While any key is pressed, a black box appears on the screen. When the key
// is released the box disappears (the area is cleared to white).
//
// My box for K = 88:
//   starts at row K = 88
//   20 rows tall                 -> rows 88 .. 107
//   16 * ((K mod 4) + 1) =
//   16 * ((88 mod 4) + 1) =
//   16 * 1 = 16 pixels = 1 word  wide, from the left edge
//
// Screen facts: one row = 32 words, one word = 16 pixels.
// Row r starts at address SCREEN + 32*r.
// The box start address is SCREEN + 32*88 = 16384 + 2816 = 19200.
//
// To change the box, edit only the three SETUP values:
//   @88 = first row, @20 = height in rows, @1 = width in words.

// ------------------------------------------------------------------
// SETUP: keep the geometry in variables so it is easy to change.
// ------------------------------------------------------------------
@88
D=A
@row
M=D             // row = 88 (first row of the box)
@20
D=A
@height
M=D             // height = 20 rows
@1
D=A
@width
M=D             // width = 1 word = 16 pixels

// ------------------------------------------------------------------
// Main infinite loop: look at the keyboard, then (re)paint the box.
// ------------------------------------------------------------------
(INFINITE_LOOP)
    @KBD
    D=M
    @KEY_DOWN
    D;JNE           // if KBD != 0 a key is pressed
    @colour
    M=0             // no key -> colour = white (clear the box)
    @DRAW
    0;JMP
(KEY_DOWN)
    @colour
    M=-1            // key pressed -> colour = black

(DRAW)
    // addr = SCREEN + 32*row.
    // 32*row is computed by doubling `row` five times (32 = 2^5).
    @row
    D=M
    @addr
    M=D             // addr = row
    @k
    M=0             // k = number of doublings done
(DOUBLE)
    @addr
    D=M
    M=D+M           // addr = addr * 2
    @k
    M=M+1
    D=M
    @5
    D=D-A
    @DOUBLE
    D;JLT           // while k < 5 keep doubling (32*row)
    @SCREEN
    D=A
    @addr
    M=D+M           // addr = SCREEN + 32*row  (first box row)

    // outer loop: for each of `height` rows
    @height
    D=M
    @r
    M=D             // r = rows left to draw
(ROWLOOP)
    @r
    D=M
    @DONE
    D;JEQ           // no rows left -> finished drawing

    // paint `width` words on this row starting at addr
    @width
    D=M
    @w
    M=D             // w = words left on this row
    @addr
    D=M
    @cur
    M=D             // cur = current screen address
(WORDLOOP)
    @w
    D=M
    @NEXTROW
    D;JEQ           // this row done

    @colour
    D=M
    @cur
    A=M
    M=D             // RAM[cur] = colour

    @cur
    M=M+1           // next word
    @w
    M=M-1
    @WORDLOOP
    0;JMP
(NEXTROW)
    @addr
    D=M
    @32
    D=D+A
    @addr
    M=D             // addr = addr + 32 (next screen row)
    @r
    M=M-1
    @ROWLOOP
    0;JMP

(DONE)
    @INFINITE_LOOP
    0;JMP