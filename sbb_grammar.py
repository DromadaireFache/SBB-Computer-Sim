from random import random

enum_count = 0
def enum():
    global enum_count
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
BOOL_EXPR   = enum()
RETURN_ST   = enum()
IF_ST       = enum()
WHILE_ST    = enum()
VAR_DECL    = enum()
PROG_BODY   = enum()
VAR_EQ      = enum()
MULT_EX     = enum()
ADD_EX      = enum()
SUB_EX      = enum()

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
    BOOL_EXPR   : "BOOL_EXPR",
    RETURN_ST   : "RETURN",
    IF_ST       : "IF",
    WHILE_ST    : "WHILE",
    VAR_DECL    : "VAR_DECL",
    PROG_BODY   : "PROGRAM_BODY",
    VAR_EQ      : "VAR_EQ",
    MULT_EX     : "MULT_EX",
    ADD_EX      : "ADD_EX",
    SUB_EX      : "SUB_EX",
}

GRAMMAR: dict = {
    IDENTIFIER: IDENTIFIER,
    INT_LIT: INT_LIT,
    STR_LIT: STR_LIT,
    END_OF_FILE: END_OF_FILE,
    PROGRAM: [
        (NEW_SCOPE, (PROG_BODY,), END_OF_FILE),
    ],
    PROG_BODY: [
        (FUNCTION,),
        (VAR_DECL, ';'),
    ],
    FUNCTION: [
        ('func', DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT),
        ('func', '[', SET_SIZE, INT_LIT, ']', DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT),
    ],
    VAR_DECL: [
        ('var', '[', SET_SIZE, INT_LIT, ']', DECL, IDENTIFIER), #var[5] x;
        ('var', SET_SIZE, DECL, IDENTIFIER), #var x;
    ],
    STATEMENT: [
        (IF_ST,),
        (WHILE_ST,),
        (VAR_DECL, ';'),
        (VAR_EQ, ';'),
        (CALL, IDENTIFIER, '(', (ARG, IDENTIFIER, ','), END_OF_ARGS, ')', ';'), #func(x,y);
        (RETURN_ST,),
        ('{', (STATEMENT,), '}'), #{var x;}
        (';',),
    ],
        IF_ST: [
            ('if', NEW_SCOPE, '(', BOOL_EXPR, ')', STATEMENT),
        ],
        WHILE_ST: [
            ('while', NEW_SCOPE, '(', BOOL_EXPR, ')', STATEMENT),
        ],
        RETURN_ST: [
            ('return', EXPR, ';'),
            ('return', ';')
        ],
        VAR_EQ: [
            (IDENTIFIER, '=', EXPR)
        ],

    EXPR: [
        ('(', EXPR, ')'), # (x)
        ('-', EXPR), # -x
        (EXPR, MULT_EX), # x*y
        (EXPR, ADD_EX), # x+y
        (EXPR, SUB_EX), # x-y
        ('int', '(', BOOL_EXPR, ')'), # int(x > y)
        (IDENTIFIER, '[', EXPR, ']'), # my_array[5]
        (CALL, IDENTIFIER, '(', (ARG, IDENTIFIER, ','), END_OF_ARGS, ')'), # foo(x)
        (IDENTIFIER,), # x
        (INT_LIT,), # 5
        (STR_LIT,), # "Hey"
    ],
        MULT_EX: [
            ('*', EXPR), # x*y
        ],
        ADD_EX: [
            ('+', EXPR), # x+y
        ],
        SUB_EX: [
            ('-', EXPR), # x-y
        ],
    
    ARG_DECL: [
        ('var', '[', SET_SIZE, INT_LIT, ']', DECL, ARG, IDENTIFIER),
        ('var', SET_SIZE, DECL, ARG, IDENTIFIER),
    ],
    
    BOOL_EXPR: [
        ('(', BOOL_EXPR,')'),
        (EXPR, '<', EXPR),
        (EXPR, '>', EXPR),
        (EXPR, '<=', EXPR),
        (EXPR, '>=', EXPR),
        (EXPR, '==', EXPR),
        (EXPR, '!=', EXPR),
        ('!', BOOL_EXPR),
        (BOOL_EXPR, '&&', BOOL_EXPR),
        (BOOL_EXPR, '||', BOOL_EXPR),
    ]
}