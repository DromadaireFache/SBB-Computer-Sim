enum_count = 0
def enum():
    global enum_count
    enum_count += 1
    return enum_count - 1

KEYWORDS = ('while', 'if', 'return', 'var', 'func')
OPERATORS = ('=', '+', '+=', '++', '-', '-=', '--', '!', '!=', '&', '&&', '==', '*', '||')
PROGRAM     = enum()
IDENTIFIER  = enum()
INT_LIT     = enum()
STR_LIT     = enum()
END_OF_FILE = enum()
FUNCTION    = enum()
STATEMENT   = enum()
EXPR        = enum()

TOKEN_TYPE_STR = {
    PROGRAM     : "PROGRAM",
    IDENTIFIER  : "IDENTIFIER",
    INT_LIT     : "INT_LIT",
    STR_LIT     : "STR_LIT",
    END_OF_FILE : "END_OF_FILE",
    FUNCTION    : "FUNCTION",
    STATEMENT   : "STATEMENT",
    EXPR        : "EXPR"
}

def throw_error(line_nb: int, msg: str, line: str, ind: int | None = None):
    print(f"[Line {line_nb+1}] {msg}")
    print(f"{line_nb+1}: {line}")
    if ind != None:
        print('^~~'.rjust(ind + len(str(line_nb+1)) + 5))
    exit()

def lexer(program: str) -> list[tuple[str, str|int]]:
    '''
    Lexical analysis breaks the source code into tokens like keywords, 
    identifiers, operators, and punctuation.
    '''
    TYPE_NULL = 0
    TYPE_WORD = 1
    TYPE_OPER = 2
    TYPE_STR  = 3
    CHARS_NULL = ' \t\n'
    CHARS_OPER = '*&|+-/^=<>'
    CHARS_WORD = '_'

    tokens = []
    token = ''
    token_type = TYPE_NULL
    line_nb = 0

    def add_token(token: str):
        if token != '':
            if token.isidentifier() and token not in KEYWORDS:
                tokens.append((token, IDENTIFIER))
            elif token[0] == token[-1] == '"':
                tokens.append((token, STR_LIT))
            elif token.isnumeric():
                tokens.append((token, INT_LIT))
            else:
                try:
                    tokens.append((str(int(token, base=2)), INT_LIT))
                except ValueError:
                    try:
                        tokens.append((str(int(token, base=16)), INT_LIT))
                    except ValueError:
                        if token_type == TYPE_WORD and not token.isidentifier():
                            line = program.split('\n')[line_nb]
                            index = line.find(token)
                            throw_error(
                                line_nb= line_nb,
                                msg= f"Syntax error; invalid identifier <{token}>",
                                line= line,
                                ind= index
                            )
                        else:
                            tokens.append((token, token))

    #make a list of tokens and their type
    for c in program:
        if token == '//':
            if c == '\n':
                token = ''
                token_type = TYPE_NULL
            continue

        if token_type == TYPE_STR:
            if c == '"':
                if token[-1] == '\\' and \
                    not (len(token) > 2 and token[-2] == '\\'):
                    token = token[:-1] + c
                else:
                    add_token(token + c)
                    token = ''
                    token_type = TYPE_NULL
            elif c == '\n':
                line = program.split('\n')[line_nb]
                throw_error(
                    line_nb= line_nb,
                    msg= "Syntax error; missing terminatig <\"> character",
                    line= line,
                    ind= len(line)
                )
            else:
                token += c
            continue

        if c in CHARS_NULL:
            if token != '':
                add_token(token)
                token = ''
                token_type = TYPE_NULL
            if c == '\n':
                line_nb += 1
            continue
        
        if c == '"':
            char_type = TYPE_STR
        elif c in CHARS_OPER:
            char_type = TYPE_OPER
        elif c.isalnum() or c in CHARS_WORD:
            char_type = TYPE_WORD
        else:
            if token != '':
                add_token(token)
            token_type = TYPE_NULL
            token = ''
            add_token(c)
            continue

        if char_type == token_type or token_type == TYPE_NULL:
            if char_type == TYPE_OPER and (len(token) == 2 or (token+c) not in OPERATORS):
                add_token(token)
                token = c

            else:
                token += c

        else:
            add_token(token)
            token = c

        token_type = char_type
    
    tokens.append((':)', END_OF_FILE))
    return tokens

GRAMMAR = {
    IDENTIFIER: IDENTIFIER,
    INT_LIT: INT_LIT,
    STR_LIT: STR_LIT,
    END_OF_FILE: END_OF_FILE,
    PROGRAM: [
        (FUNCTION, END_OF_FILE)
    ],
    EXPR: [
        (IDENTIFIER,),
        (INT_LIT,),
        (STR_LIT,)
    ],
    STATEMENT: [
        ('return', EXPR, ';'),
        ('{', STATEMENT, '}'),
        (';',)
    ],
    FUNCTION: [
        ('func', IDENTIFIER, '(', IDENTIFIER, ')', STATEMENT)
    ],
}

def parser(tokens: list[tuple[str, str|int]]):
    '''
    Syntax analysis ensures that tokens generated from lexical analysis are
    arranged according to SBB lang grammar.
    '''
    syntax_tree = []
    token_index = 0

    def make(grammar: list, syntax_tree: list) -> bool:
        nonlocal token_index
        if type(grammar) == int:
            if grammar == tokens[token_index][1]:
                syntax_tree.append(tokens[token_index])
                token_index += 1
                return True
            else:
                return False
        
        for variation in grammar:
            # if len(kind) == 0: raise ValueError(f"Invalid grammar kind {grammar}")
            valid = True
            for token in variation:
                temp_tree = []
                if type(token) == tuple:
                    raise ValueError("tuple not implemented yet")
                elif type(token) == str and token == tokens[token_index][1]:
                    syntax_tree.append(tokens[token_index])
                    token_index += 1
                elif type(token) == int and make(GRAMMAR[token], temp_tree):
                    if len(temp_tree) == 1 and token == temp_tree[0][1]:
                        syntax_tree.append(temp_tree[0])
                    else:
                        syntax_tree.append((temp_tree, token))
                else:
                    valid = False
                    break
            
            if valid: break
        
        return valid


    make(GRAMMAR[PROGRAM], syntax_tree)
    
    return syntax_tree

def print_parsed_code(syntax_tree: list[tuple], indent=0) -> None:
    for branch in syntax_tree:
        if type(branch[0]) == list:
            try:
                print(' ' * indent + TOKEN_TYPE_STR[branch[1]] + ': ')
            except KeyError:
                print(' ' * indent + f"'{branch[1]}': ")
            print_parsed_code(branch[0], indent+4)

        else:
            try:
                print(' ' * indent + TOKEN_TYPE_STR[branch[1]] + ': ' + str(branch[0]))
            except KeyError:
                print(' ' * indent + f"'{branch[1]}': " + str(branch[0]))

def semantic():
    pass

def optimise():
    pass

def generate_code():
    pass


if __name__ == '__main__':
    with open('sbb_lang_files/program.sbb') as program:
        program = program.read()
        tokens = lexer(program)
        syntax_tree = parser(tokens)
        print_parsed_code(syntax_tree)