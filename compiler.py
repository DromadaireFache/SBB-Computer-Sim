enum_count = 0
def enum():
    global enum_count
    enum_count += 1
    return enum_count - 1

KEYWORDS = ('while', 'if', 'return', 'var', 'func')
OPERATORS = ('//',  '=',  '+', '+=',
             '++',  '-', '-=', '--',
             '!',  '!=',  '&', '&&',
             '==',  '*', '||')
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
    print(f"[{line_nb+1}:{ind+1}] {line}")
    if ind != None:
        print('^~~'.rjust(ind + len(str(line_nb+1)) + len(str(ind+1)) + 7))
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
    bol = 0

    def add_token(token: str):
        if token != '':
            if token.isidentifier() and token not in KEYWORDS:
                tokens.append((token, IDENTIFIER, bol, i))
            elif token[0] == token[-1] == '"':
                tokens.append((token, STR_LIT, bol, i))
            elif token.isnumeric():
                tokens.append((token, INT_LIT, bol, i))
            else:
                try:
                    tokens.append((str(int(token, base=2)), INT_LIT, bol, i))
                except ValueError:
                    try:
                        tokens.append((str(int(token, base=16)), INT_LIT, bol, i))
                    except ValueError:
                        if token_type == TYPE_WORD and not token.isidentifier():
                            line = program[bol:].split('\n')[0]
                            throw_error(
                                line_nb= line_nb,
                                msg= f"Syntax error; invalid identifier '{token}'",
                                line= line,
                                ind= i-bol-len(token)
                            )
                        else:
                            tokens.append((token, token, bol, i))

    #make a list of tokens and their type
    for i, char in enumerate(program):
        if token == '//':
            if char == '\n':
                token = ''
                token_type = TYPE_NULL
            continue

        if token_type == TYPE_STR:
            if char == '"':
                if token[-1] == '\\' and \
                    not (len(token) > 2 and token[-2] == '\\'):
                    token = token[:-1] + char
                else:
                    add_token(token + char)
                    token = ''
                    token_type = TYPE_NULL
            elif char == '\n':
                line = program.split('\n')[line_nb]
                throw_error(
                    line_nb= line_nb,
                    msg= "Syntax error; missing terminating '\"' character",
                    line= line,
                    ind= len(line)
                )
            else:
                token += char
            continue

        if char in CHARS_NULL:
            if token != '':
                add_token(token)
                token = ''
                token_type = TYPE_NULL
            if char == '\n':
                line_nb += 1
                bol = i + 1
            continue
        
        if char == '"':
            char_type = TYPE_STR
        elif char in CHARS_OPER:
            char_type = TYPE_OPER
        elif char.isalnum() or char in CHARS_WORD:
            char_type = TYPE_WORD
        else:
            if token != '':
                add_token(token)
            token_type = TYPE_NULL
            token = ''
            add_token(char)
            continue

        if char_type == token_type or token_type == TYPE_NULL:
            if char_type == TYPE_OPER and (len(token) == 2 or (token+char) not in OPERATORS):
                add_token(token)
                token = char

            else:
                token += char

        else:
            add_token(token)
            token = char

        token_type = char_type
    
    tokens.append((':)', END_OF_FILE))
    return tokens

GRAMMAR = {
    IDENTIFIER: IDENTIFIER,
    INT_LIT: INT_LIT,
    STR_LIT: STR_LIT,
    END_OF_FILE: END_OF_FILE,
    PROGRAM: [
        (NEW_SCOPE, (FUNCTION,), END_OF_FILE)
    ],
    EXPR: [
        (IDENTIFIER,),
        (INT_LIT,),
        (STR_LIT,)
    ],
    STATEMENT: [
        ('var', '[', SET_SIZE, INT_LIT, ']', DECL, IDENTIFIER, ';'),
        ('var', SET_SIZE, DECL, IDENTIFIER, ';'),
        (CALL, IDENTIFIER, '(', (ARG, IDENTIFIER, ','), END_OF_ARGS, ')'),
        ('return', EXPR, ';'),
        ('{', (STATEMENT,), '}'),
        (';',)
    ],
    FUNCTION: [
        ('func', DECL, CALL, IDENTIFIER, NEW_SCOPE, '(', (DECL, ARG, IDENTIFIER, ','), ')', STATEMENT)
    ],
}

def parser(program: str, tokens: list[tuple[str, str|int]]) -> list:
    '''
    Syntax analysis ensures that tokens generated from lexical analysis are
    arranged according to SBB lang grammar.
    '''
    syntax_tree = []
    token_index = 0

    def add_func_arg(scope: dict, var_size: int):
        for i in range(len(scope.keys())-1, -1, -1):
            var = list(scope.keys())[i]
            if scope[var][0] != None:
                scope[var][0].append(var_size)
                return
    
    def count_real_tokens(tokens):
        count = 0
        for token in tokens:
            if type(token) == str or token in GRAMMAR:
                count += 1
        return count

    def make(grammar: list,
             syntax_tree: list,
             compound=False,
             decl=False,
             scope:dict={},
             call=False,
             arg=False,
             set_size=False,
             md=['',0,1]) -> bool:
        #md: function call name, function argument counter, var size
        nonlocal token_index
        if type(grammar) == int:
            if grammar == tokens[token_index][1]:
                syntax_tree.append(tokens[token_index])
                if grammar == IDENTIFIER:
                    var_name = tokens[token_index][0]
                    bol = tokens[token_index][2]
                    i = tokens[token_index][3]
                    next_line = program.find('\n', bol)
                    # print(var_name, decl, set_size)
                    if decl:
                        print('declaration:', var_name, '| size:', md[2], '| size size?:', set_size)
                        # if set_size:
                        #     md[2] = 1
                        scope[var_name] = [[], md[2]] if call else [None, md[2]]
                        if arg:
                            add_func_arg(scope, md[2])
                        # print(scope)
                    elif var_name not in scope:
                        throw_error(
                            line_nb= program.count('\n', 0, bol),
                            msg= f"Name error; out of scope '{var_name}'",
                            line= program[bol:next_line],
                            ind= i-bol-len(var_name),
                        )
                    elif call and scope[var_name][0] == None:
                        throw_error(
                            line_nb= program.count('\n', 0, bol),
                            msg= f"Type error; uncallable '{var_name}'",
                            line= program[bol:next_line],
                            ind= i-bol-len(var_name),
                        )
                    if not decl:
                        if call:
                            md[0] = tokens[token_index][0]
                            md[1] = 0
                        elif arg:
                            if len(scope[md[0]][0]) <= md[1]:
                                throw_error(
                                    line_nb= program.count('\n', 0, bol),
                                    msg= f"Argument error; in '{md[0]}' call, "\
                                         f"argument '{var_name}' not expected",
                                    line= program[bol:next_line],
                                    ind= i-bol-len(var_name),
                                )
                            if scope[md[0]][0][md[1]] != scope[var_name][1]:
                                throw_error(
                                    line_nb= program.count('\n', 0, bol),
                                    msg= f"Type error; in '{md[0]}' call, "\
                                         f"incorrect argument type of '{var_name}'\n"\
                                         f"Expected {scope[md[0]][0][md[1]]} "\
                                         f"byte(s), instead got {scope[var_name][1]} byte(s)",
                                    line= program[bol:next_line],
                                    ind= i-bol-len(var_name),
                                )
                            md[1] += 1
                elif grammar == INT_LIT and set_size:
                    print('set size at:', tokens[token_index][0])
                    md[2] = int(tokens[token_index][0])
                    if md[2] < 1:
                        bol = tokens[token_index][2]
                        i = tokens[token_index][3]
                        next_line = program.find('\n', bol)
                        throw_error(
                            line_nb= program.count('\n', 0, bol),
                            msg= f"Declaration error; zero size variable declaration '{md[2]}'",
                            line= program[bol:next_line],
                            ind= i-bol-len(str(md[2])),
                        )
                token_index += 1
                return True
            else:
                return False
            
        root_index = token_index
        # print('grammar', grammar, '| root token:', tokens[root_index][0])
        for variation in grammar:
            valid = True
            decl = call = arg = set_size = False
            # print('variation:', variation, '| looked at token:', tokens[token_index][0])
            token_index = root_index
            for token in variation:
                temp_tree = []
                if token == NEW_SCOPE:
                    scope = dict(scope)
                elif token == DECL:
                    decl = True
                elif token == CALL:
                    call = True
                elif token == ARG:
                    arg = True
                elif token == END_OF_ARGS:
                    if len(scope[md[0]][0]) != md[1]:
                        bol = tokens[token_index][2]
                        i = tokens[token_index][3]
                        next_line = program.find('\n', bol)
                        throw_error(
                            line_nb= program.count('\n', 0, bol),
                            msg= f"Arugment error; in '{md[0]}' call, "\
                                 f"too few arguments",
                            line= program[bol:next_line],
                            ind= i-bol-len(tokens[token_index][0]),
                        )
                elif token == SET_SIZE:
                    md[2] = 1
                    set_size = True
                elif type(token) == tuple:
                    while make([token], temp_tree, True, decl, scope, call, arg, set_size):
                        syntax_tree.extend(temp_tree)
                        temp_tree = []
                    if len(temp_tree) == count_real_tokens(token) - 1:
                        syntax_tree.extend(temp_tree)
                elif type(token) == str and token == tokens[token_index][1]:
                    syntax_tree.append(tokens[token_index])
                    token_index += 1
                elif type(token) == int and \
                    make(GRAMMAR[token], temp_tree, compound, decl, scope, call, arg, set_size):
                    if len(temp_tree) == 1 and token == temp_tree[0][1]:
                        syntax_tree.append(temp_tree[0])
                    else:
                        syntax_tree.append((temp_tree, token))
                else:
                    valid = False
                    break
            if valid: break
        
        if not (compound or valid):
            bol = tokens[token_index][2]
            i = tokens[token_index][3]
            next_line = program.find('\n', bol)
            throw_error(
                line_nb= program.count('\n', 0, bol),
                msg= f"Syntax error; unexpected '{tokens[token_index][0]}'",
                line= program[bol:next_line],
                ind= i-bol-len(tokens[token_index][0]),
            )
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

def optimise():
    pass

def generate_code():
    pass


if __name__ == '__main__':
    with open('sbb_lang_files/program.sbb') as program:
        program = program.read()
        tokens = lexer(program)
        syntax_tree = parser(program, tokens)
        print_parsed_code(syntax_tree)