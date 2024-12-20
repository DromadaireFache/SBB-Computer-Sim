enum_count = 0
def enum(reset = False):
    global enum_count
    if reset:
        enum_count = 0
    else:
        enum_count += 1
        return enum_count - 1              

PROGRAM     = enum()

IDENTIFIER  = enum()
INT_LIT     = enum()
STR_LIT     = enum()
END_OF_FILE = enum()
FUNCTION    = enum()
STATEMENT   = enum()
EXPR        = enum()
ARG_DECL    = enum()
BOOL        = enum()
RETURN_ST   = enum()
IF_ST       = enum()
WHILE_ST    = enum()
VAR_DECL    = enum()
PROG_BODY   = enum()
VAR_EQ      = enum()
MULT_EX     = enum()
ADD_EX      = enum()
SUB_EX      = enum()
CMP_EX      = enum()
LONE_EX     = enum()
BOOL_EQ     = enum()
BOOL_NEQ    = enum()
BOOL_GTE    = enum()
BOOL_GT     = enum()
BOOL_LTE    = enum()
BOOL_LT     = enum()
SCOPED_ST   = enum()
BOOL_TRUE   = enum()
BOOL_FALSE  = enum()
LET_DECL  = enum()

DECL        = enum()
NEW_SCOPE   = enum()
CALL        = enum()
ARG         = enum()
END_OF_ARGS = enum()

SET_SIZE    = enum()

RANDOM      = enum()

TOKEN_TYPE_STR = {
    PROGRAM     : "PROGRAM",
    IDENTIFIER  : "IDENTIFIER",
    INT_LIT     : "INT_LIT",
    STR_LIT     : "STR_LIT",
    END_OF_FILE : "END_OF_FILE",
    FUNCTION    : "FUNCTION",
    STATEMENT   : "STATEMENT",
    EXPR        : "EXPR",
    ARG_DECL    : "ARG_DECL",
    BOOL        : "BOOL",
    RETURN_ST   : "RETURN",
    IF_ST       : "IF",
    WHILE_ST    : "WHILE",
    VAR_DECL    : "VAR_DECL",
    PROG_BODY   : "PROGRAM_BODY",
    VAR_EQ      : "VAR_EQ",
    MULT_EX     : "MULT_EX",
    ADD_EX      : "ADD_EX",
    SUB_EX      : "SUB_EX",
    LONE_EX     : "LONE_EX",
    BOOL_EQ     : "BOOL_EQ",
    SCOPED_ST   : "SCOPED_ST",
    BOOL_TRUE   : "BOOL_TRUE",
    BOOL_FALSE  : "BOOL_FALSE",
    BOOL_NEQ    : "BOOL_NEQ",
    BOOL_GTE    : "BOOL_GTE",
    BOOL_GT     : "BOOL_GT",
    BOOL_LTE    : "BOOL_LTE",
    BOOL_LT     : "BOOL_LT",
    LET_DECL    : "LET_DECL",
}

GRAMMAR: dict = {
    IDENTIFIER: IDENTIFIER,
    INT_LIT: INT_LIT,
    STR_LIT: STR_LIT,
    END_OF_FILE: END_OF_FILE,
    PROGRAM: [(NEW_SCOPE, (PROG_BODY,), END_OF_FILE)],
    PROG_BODY: [FUNCTION, VAR_DECL, LET_DECL],
    FUNCTION: [
        ('func', SET_SIZE, DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT),
        ('func', '[', SET_SIZE, INT_LIT, ']', DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT),
    ],
    VAR_DECL: [
        ('var', '[', SET_SIZE, INT_LIT, ']', (DECL, IDENTIFIER, ','), ';'), #var[5] x;
        ('var', SET_SIZE, (DECL, IDENTIFIER, ','), ';'), #var x, y, z;
    ],
    LET_DECL: [('var', 'let', SET_SIZE, DECL, IDENTIFIER, '=', INT_LIT, ';')], #var x = 5;
    STATEMENT: [
        IF_ST,
        WHILE_ST,
        VAR_DECL,
        (VAR_EQ, ';'),
        (CALL, IDENTIFIER, '(', (ARG, IDENTIFIER, ','), END_OF_ARGS, ')', ';'), #func(x,y);
        RETURN_ST,
        ('{', (STATEMENT,), '}'), #{var x;}
        (';',),
    ],
        IF_ST: [
            ('if', '(', BOOL, ')', SCOPED_ST, 'else', SCOPED_ST),
            ('if', '(', BOOL, ')', SCOPED_ST),
        ],
        WHILE_ST: [('while', '(', BOOL, ')', SCOPED_ST)],
        RETURN_ST: [
            ('return', EXPR, ';'),
            ('return', ';')
        ],
        VAR_EQ: [
            ('var', 'let', SET_SIZE, DECL, IDENTIFIER, '=', EXPR),
            (IDENTIFIER, '=', EXPR)
        ],
        SCOPED_ST: [(NEW_SCOPE, STATEMENT)],

    EXPR: [
        ('(', EXPR, ')'), # (x)
        ('-', EXPR), # -x
        (LONE_EX, MULT_EX), # x*y
        (LONE_EX, ADD_EX), # x+y
        (LONE_EX, SUB_EX), # x-y
        ('int', '(', BOOL, ')'), # int(x > y)
        LONE_EX
    ],
        LONE_EX: [
            (IDENTIFIER, '[', EXPR, ']'), # my_array[5]
            (CALL, IDENTIFIER, '(', (ARG, LONE_EX, ','), END_OF_ARGS, ')'), # foo(x)
            IDENTIFIER, # x
            INT_LIT, # 5
        ],
        MULT_EX: [('*', LONE_EX)],
        ADD_EX: [('+', LONE_EX)],
        SUB_EX: [('-', LONE_EX)],
        CMP_EX: [LONE_EX],
    
    ARG_DECL: [
        ('var', '[', SET_SIZE, INT_LIT, ']', DECL, ARG, IDENTIFIER),
        ('var', SET_SIZE, DECL, ARG, IDENTIFIER),
    ],
    
    BOOL: [
        ('(', BOOL,')'),
        BOOL_EQ,
        BOOL_NEQ,
        BOOL_GTE,
        BOOL_GT,
        BOOL_LTE,
        BOOL_LT,
        BOOL_TRUE,
        BOOL_FALSE,
        # ('!', BOOL),
        # (BOOL, '&&', BOOL),
        # (BOOL, '||', BOOL),
    ],
        BOOL_EQ: [(LONE_EX, '==', LONE_EX), (EXPR, '==', EXPR)],
        BOOL_NEQ: [(LONE_EX, '!=', LONE_EX), (EXPR, '!=', EXPR)],
        BOOL_GTE: [(LONE_EX, '>=', LONE_EX), (EXPR, '>=', EXPR)],
        BOOL_GT: [(LONE_EX, '>', LONE_EX), (EXPR, '>', EXPR)],
        BOOL_LTE: [(LONE_EX, '<=', LONE_EX), (EXPR, '<=', EXPR)],
        BOOL_LT: [(LONE_EX, '<', LONE_EX), (EXPR, '<', EXPR)],
        BOOL_TRUE: [('True',)],
        BOOL_FALSE: [('False',)],
}