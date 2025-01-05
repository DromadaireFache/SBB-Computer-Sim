enum_count = 0
def enum(reset = False):
    global enum_count
    if reset:
        enum_count = 0
    else:
        enum_count += 1
        return enum_count - 1              

PROGRAM     = enum()

#literals
IDENTIFIER  = enum(); INT_LIT     = enum(); STR_LIT     = enum(); END_OF_FILE = enum()
INVALID_TK  = enum(); BUILTIN     = enum()

#expandables
FUNCTION    = enum(); STATEMENT   = enum(); EXPR        = enum(); ARG_DECL    = enum()
BOOL        = enum(); RETURN_ST   = enum(); IF_ST       = enum(); WHILE_ST    = enum()
VAR_DECL    = enum(); PROG_BODY   = enum(); VAR_EQ      = enum(); MULT_EX     = enum()
ADD_EX      = enum(); SUB_EX      = enum(); CMP_EX      = enum(); LONE_EX     = enum()
BOOL_EQ     = enum(); BOOL_NEQ    = enum(); BOOL_GTE    = enum(); BOOL_GT     = enum()
BOOL_LTE    = enum(); BOOL_LT     = enum(); SCOPED_ST   = enum(); BOOL_TRUE   = enum()
BOOL_FALSE  = enum(); LET_DECL    = enum(); PREPROCESS  = enum(); NEG_EX      = enum()
FCT_CALL    = enum(); ARG_EX      = enum(); LITERAL     = enum(); NEG_INT     = enum()
NEGATIVE    = enum(); ARG_LIT     = enum(); CAST_EX     = enum(); ASSERT_RET  = enum()
FCT_EX      = enum(); ARRAY_GET   = enum(); BOOL_SIZE   = enum()

#modifiers
DECL        = enum(); NEW_SCOPE   = enum(); CALL        = enum(); ARG         = enum()
END_OF_ARGS = enum(); SET_SIZE    = enum(); ASSERT_TYPE = enum()

def namestr(obj, namespace):
    return [name for name in namespace if namespace[name] is obj][0]

def istokentype(obj, namespace):
    return len([name for name in namespace if namespace[name] is obj]) != 0

GRAMMAR = {
    IDENTIFIER: IDENTIFIER,
    INT_LIT: INT_LIT,
    STR_LIT: STR_LIT,
    END_OF_FILE: END_OF_FILE,
    PREPROCESS: ['import', 'define'],
    PROGRAM: [(NEW_SCOPE, (PROG_BODY,), END_OF_FILE)],
    PROG_BODY: [FUNCTION, VAR_DECL, LET_DECL],
    FUNCTION: [
        ('func', '[', SET_SIZE, INT_LIT,']', DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT),
        ('func', SET_SIZE, DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (ARG_DECL, ','), ')', STATEMENT),
    ],
    VAR_DECL: [
        ('var', DECL, SET_SIZE, IDENTIFIER, ';'),
        ('var', DECL, '[', SET_SIZE, INT_LIT,']', IDENTIFIER, ';')
    ],
    LET_DECL: [
        ('let', 'var', DECL, SET_SIZE, IDENTIFIER, '=', LITERAL, ';'),
        ('let', 'var', DECL, '[', SET_SIZE, INT_LIT,']', IDENTIFIER, '=', LITERAL, ';')
    ],
    LITERAL: [
        ('-', ASSERT_TYPE, NEGATIVE, INT_LIT),
        (ASSERT_TYPE, INT_LIT),
        (ASSERT_TYPE, STR_LIT)
    ],
    STATEMENT: [
        IF_ST,
        WHILE_ST,
        VAR_DECL,
        (FCT_CALL, ';'),
        (VAR_EQ, ';'),
        RETURN_ST,
        ('{', (STATEMENT,), '}'),
        ';',
    ],
        IF_ST: [
            ('if', '(', BOOL, ')', SCOPED_ST, 'else', SCOPED_ST),
            ('if', '(', BOOL, ')', SCOPED_ST),
        ],
        WHILE_ST: [('while', '(', BOOL, ')', SCOPED_ST)],
        RETURN_ST: [
            ('return', ';'),
            ('return', ASSERT_RET, EXPR, ';')
        ],
        VAR_EQ: [
            ('let', 'var', DECL, SET_SIZE, IDENTIFIER, '=', EXPR),
            ('let', 'var', DECL, '[', SET_SIZE, INT_LIT,']', IDENTIFIER, '=', EXPR),
            (SET_SIZE, IDENTIFIER, '=', EXPR)
        ],
        ARRAY_GET: [
            (IDENTIFIER, '[', INT_LIT, ']'),
            (IDENTIFIER, '[', IDENTIFIER, ']')
        ],
        SCOPED_ST: [(NEW_SCOPE, STATEMENT)],

    EXPR: [
        ('(', EXPR, ')'), # (x)
        (LONE_EX, MULT_EX), # x*y
        (LONE_EX, ADD_EX), # x+y
        (LONE_EX, SUB_EX), # x-y
        # ('int', '(', BOOL, ')'), # int(x > y)
        ARRAY_GET,
        LONE_EX,
        SUB_EX, # -x
    ],
        LONE_EX: [
            CAST_EX,
            FCT_EX, # foo(x)
            (ASSERT_TYPE, IDENTIFIER), # x
            LITERAL, # 5
        ],
        CAST_EX: [('(', 'cast', ')', FCT_CALL), ('(', 'cast', ')', IDENTIFIER),],
        FCT_CALL: [(CALL, IDENTIFIER, '(', (ARG_EX, ','), END_OF_ARGS, ')')],
        FCT_EX: [(CALL, ASSERT_TYPE, IDENTIFIER, '(', (ARG_EX, ','), END_OF_ARGS, ')')],
        MULT_EX: [('*', LONE_EX)],
        ADD_EX: [('+', LONE_EX)],
        SUB_EX: [('-', LONE_EX)],
        CMP_EX: [LONE_EX],
        ARG_EX: [(ARG, IDENTIFIER), ARG_LIT],
        ARG_LIT: [('-', NEGATIVE, ARG, INT_LIT), (ARG, INT_LIT), (ARG, STR_LIT)],

    # EXPR: [
    #     (TERM, '+', EXPR),
    #     (TERM, '-', EXPR),
    #     TERM
    # ],
    # TERM: [MULT_EX, FACTOR],
    # FACTOR: [
    #     IDENTIFIER,
    #     INT_LIT,
    #     ('(', EXPR, ')'),
    #     ('-', FACTOR)
    # ],
    #     MULT_EX: [(FACTOR, '*', TERM)],
    #     ADD_EX: [('+', LONE_EX)],
    #     SUB_EX: [('-', LONE_EX)],
    #     CMP_EX: [LONE_EX],
    #     NEG_EX: [('-', FACTOR)],
    
    ARG_DECL: [
        ('var', '[', SET_SIZE, INT_LIT,']', DECL, ARG, IDENTIFIER),
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
        BOOL_EQ: [(BOOL_SIZE, LONE_EX, '==', LONE_EX), (BOOL_SIZE, EXPR, '==', EXPR)],
        BOOL_NEQ: [(BOOL_SIZE, LONE_EX, '!=', LONE_EX), (BOOL_SIZE, EXPR, '!=', EXPR)],
        BOOL_GTE: [(BOOL_SIZE, LONE_EX, '>=', LONE_EX), (BOOL_SIZE, EXPR, '>=', EXPR)],
        BOOL_GT: [(BOOL_SIZE, LONE_EX, '>', LONE_EX), (BOOL_SIZE, EXPR, '>', EXPR)],
        BOOL_LTE: [(BOOL_SIZE, LONE_EX, '<=', LONE_EX), (BOOL_SIZE, EXPR, '<=', EXPR)],
        BOOL_LT: [(BOOL_SIZE, LONE_EX, '<', LONE_EX), (BOOL_SIZE, EXPR, '<', EXPR)],
        BOOL_TRUE: ['True'],
        BOOL_FALSE: ['False'],
}

    # def is_recursive(variation: tuple, grammar: list, root_index: int) -> bool:
    #     # 1. find the grammar type (eg: EXPR)
    #     # 2. if there is no token of that type in the variation, return False
    #     # 3. otherwise, find the index of the variation in the grammar
    #     # 4. if the index of the variation is greater that the index of the root variation return True
    #     # 5. otherwise return False

    #     #find grammar type (eg: EXPR)
    #     grammar_type = -1
    #     for type in GRAMMAR:
    #         if GRAMMAR[type] == grammar:
    #             grammar_type = type
    #             break
        
    #     # if there is no token of that type in the variation, return False
    #     if grammar_type == -1 or grammar_type != variation[0]:
    #         return False
        
    #     # print(f"{variation = }")
    #     # print(f"{TOKEN_TYPE_STR[grammar_type] = }")
    #     # print(f"{root_index = }")

    #     # find the index of the variation in the grammar
    #     variation_index = grammar.index(variation)
    #     # print(f"{variation_index = }")
    #     # print(f"{variation_index <= root_index = }")

    #     return variation_index <= root_index