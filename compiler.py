KEYWORDS = ('while', 'if', 'return', 'var', 'func')
OPERATORS = ('=', '+', '+=', '++', '-', '-=', '--', '!', '!=', '&', '&&', '==', '*', '||')
IDENTIFIER  = 200
INT_LIT     = 205
STR_LIT     = 210
END_OF_FILE = 215
FUNCTION    = 220
STATEMENT   = 225
EXPR        = 230

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
    
    tokens.append(('', END_OF_FILE))
    return tokens

class Grammar:
    FUNCTION = ()

def parser(tokens: list[tuple[str, str|int]]):
    '''
    Syntax analysis ensures that tokens generated from lexical analysis are
    arranged according to SBB lang grammar.
    '''
    syntax_tree = []
    token_index = 0

    def function():
        nonlocal token_index
        if tokens[token_index][1] == END_OF_FILE:
            return tokens[token_index]
        token_index += 1

    syntax_tree.append(function())
    while syntax_tree[-1][1] != END_OF_FILE:
        syntax_tree.append(function())
    
    return syntax_tree

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
        print(tokens)
        syntax_tree = parser(tokens)
        print(syntax_tree)