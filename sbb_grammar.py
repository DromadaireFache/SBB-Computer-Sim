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
DECL        = enum()
NEW_SCOPE   = enum()
CALL        = enum()
ARG         = enum()
END_OF_ARGS = enum()
SET_SIZE    = enum()
ARG_DECL    = enum()
BOOL_EXPR   = enum()

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
    BOOL_EXPR   : "BOOL_EXPR"
}

GRAMMAR = {
    IDENTIFIER: IDENTIFIER,
    INT_LIT: INT_LIT,
    STR_LIT: STR_LIT,
    END_OF_FILE: END_OF_FILE,
    PROGRAM: [
        (NEW_SCOPE, (FUNCTION,), END_OF_FILE)
    ],
    EXPR: [
        ('(', EXPR, ')'),
        ('-', EXPR),
        ('~', EXPR),
        (EXPR, '*', EXPR),
        (EXPR, '+', EXPR),
        (EXPR, '-', EXPR),
        (EXPR, '<<', EXPR),
        (EXPR, '>>', EXPR),
        ('bool', '(', BOOL_EXPR, ')'),
        (EXPR, '&', EXPR),
        (EXPR, '|', EXPR),
        (IDENTIFIER,),
        (INT_LIT,),
        (STR_LIT,),
        (EXPR, '[', EXPR, ']'),
        (CALL, IDENTIFIER, '(', (ARG, IDENTIFIER, ','), END_OF_ARGS, ')')
    ],
    STATEMENT: [
        ('if', '(', BOOL_EXPR, ')', STATEMENT),
        ('while', '(', BOOL_EXPR, ')', STATEMENT),
        ('var', '[', SET_SIZE, INT_LIT, ']', DECL, IDENTIFIER, ';'), #var[5] x;
        ('var', SET_SIZE, DECL, IDENTIFIER, ';'), #var x;
        (CALL, IDENTIFIER, '(', (ARG, IDENTIFIER, ','), END_OF_ARGS, ')', ';'), #func(x,y);
        ('return', EXPR, ';'), #return x;
        ('{', (STATEMENT,), '}'), #{var x;}
        (';',),
        (EXPR, '=', EXPR, ';')
    ],
    FUNCTION: [
        ('func', DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT),
        ('func', '[', SET_SIZE, INT_LIT, ']', DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT)
    ],
    ARG_DECL: [
        ('var', '[', SET_SIZE, INT_LIT, ']', DECL, ARG, IDENTIFIER),
        ('var', SET_SIZE, DECL, ARG, IDENTIFIER)
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

for i in range(enum_count):
    if i in GRAMMAR and type(GRAMMAR[i]) == list:
        for variation in GRAMMAR[i]:
            add_keywords_and_operators(variation, KEYWORDS, OPERATORS)