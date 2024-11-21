my_program = """/program.sbbasm
x = 1

start:
    ldi     7       *loop
    dec
    sta     &&loop
    jmpn    &&&end
    lda     x
    lsh
    sta     x
    jump    &loop   *end
    lda     x
    hlta

/repeat 7 times
/    ldi 7 *loop
/    dec
/    sta &&loop
/    jmpn &&&end
/    
/    code goes here...
/
/    jump &loop *end
"""

#make so functions can call themselves

x = 5

import asm
asm.run_program(
    my_program.splitlines(True),
    d = False,
    r = False,
    m = False,
    f = False,
    s = False,
    t = True
    )

with open("program.sbbasm", 'w') as program:
    program.flush()
    program.write(my_program)