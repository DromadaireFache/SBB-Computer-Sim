from random import random

enum_count = 0
def enum():
    global enum_count
    enum_count += 1
    return enum_count - 1

class Var:
    def __init__(self, gm, rp='') -> None:
        self.gm = gm
        self.code = rp
    def get_code(self):
        code = ''
        for chunk in self.code:
            if chunk == RANDOM:
                code += str(random())[2:]
            else:
                code += chunk
        return code
                

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
    VAR_DECL    : "VAR_DECL"
}

GRAMMAR: dict[int, Var|int] = {
    IDENTIFIER: IDENTIFIER,
    INT_LIT: INT_LIT,
    STR_LIT: STR_LIT,
    END_OF_FILE: END_OF_FILE,
    PROGRAM: [
        (NEW_SCOPE, (FUNCTION,), END_OF_FILE),
    ],
    EXPR: [
        ('(', EXPR, ')'), # (x)
        ('-', EXPR), # -x
        (EXPR, '*', EXPR), # x*y
        (EXPR, '+', EXPR), # x+y
        (EXPR, '-', EXPR), # x-y
        ('int', '(', BOOL_EXPR, ')'), # int(x > y)
        (IDENTIFIER,), # x
        (INT_LIT,), # 5
        (STR_LIT,), # "Hey"
        (IDENTIFIER, '[', EXPR, ']'), # my_array[5]
        (CALL, IDENTIFIER, '(', (ARG, IDENTIFIER, ','), END_OF_ARGS, ')'), # foo(x)
    ],
    STATEMENT: [
        (IF_ST,),
        (WHILE_ST,),
        (VAR_DECL,),
        (IDENTIFIER, '=', EXPR, ';'),
        (CALL, IDENTIFIER, '(', (ARG, IDENTIFIER, ','), END_OF_ARGS, ')', ';'), #func(x,y);
        (RETURN_ST,),
        ('{', (STATEMENT,), '}'), #{var x;}
        (';',),
    ],
    VAR_DECL: [
        ('var', '[', SET_SIZE, INT_LIT, ']', DECL, IDENTIFIER, ';'), #var[5] x;
        ('var', SET_SIZE, DECL, IDENTIFIER, ';'), #var x;
    ],
    IF_ST: [
        ('if', NEW_SCOPE, '(', BOOL_EXPR, ')', STATEMENT),
    ],
    WHILE_ST: [
        ('while', NEW_SCOPE, '(', BOOL_EXPR, ')', STATEMENT),
    ],
    RETURN_ST: [
        ('return', EXPR, ';'),
    ],
    FUNCTION: [
        ('func', DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT),
        ('func', '[', SET_SIZE, INT_LIT, ']', DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT),
    ],
    ARG_DECL: [
        ('var', '[', SET_SIZE, INT_LIT, ']', DECL, ARG, IDENTIFIER),
        ('var', SET_SIZE, DECL, ARG, IDENTIFIER),
    ],
    BOOL_EXPR: [
        ('(', BOOL_EXPR,')'),
        ('!', BOOL_EXPR),
        (EXPR, '<', EXPR),
        (EXPR, '>', EXPR),
        (EXPR, '<=', EXPR),
        (EXPR, '>=', EXPR),
        (EXPR, '&&', EXPR),
        (EXPR, '||', EXPR),
        (EXPR, '==', EXPR),
        (EXPR, '!=', EXPR),
    ]
}

KEYWORDS = []
OPERATORS = ['//']

def add_keywords_and_operators(variation, kw: list[str], op: list[str]):
    for token in variation:
        if type(token) == tuple:
            add_keywords_and_operators(token, kw, op)
        elif type(token) == str:
            if token.isalpha():
                if token not in kw: kw.append(token)
            else:
                if token not in op: op.append(token)

#get keywords and operators from grammar
for i in range(enum_count):
    if i in GRAMMAR and type(GRAMMAR[i]) == list:
        for variation in GRAMMAR[i]:
            add_keywords_and_operators(variation, KEYWORDS, OPERATORS)

#make a duplicate of each grammar type backwards
# for gm_type in GRAMMAR:
#     if type(GRAMMAR[gm_type]) == list:
#         GRAMMAR[gm_type].extend(GRAMMAR[gm_type][:-1][::-1])
#         # print(GRAMMAR[gm_type])