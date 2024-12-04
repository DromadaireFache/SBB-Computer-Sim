from sbb_grammar import *
from time import perf_counter
from asm import run_program

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
for i in range(enum()):
    if i in GRAMMAR and type(GRAMMAR[i]) == list:
        for variation in GRAMMAR[i]:
            add_keywords_and_operators(variation, KEYWORDS, OPERATORS)

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

def tk_name(token: tuple) -> str:
    return token[0]

def tk_type(token: tuple) -> int|str:
    return token[1]

def parser(program: str, tokens: list[tuple[str, str|int]]) -> list:
    '''
    Syntax analysis ensures that tokens generated from lexical analysis are
    arranged according to SBB lang grammar.
    '''
    syntax_tree = []
    token_index = 0
    max_index = 0

    def add_func_arg(scope: dict, var_size: int):
        for i in range(len(scope.keys())-1, -1, -1):
            var = list(scope.keys())[i]
            if scope[var][0] != None:
                scope[var][0].append(var_size)
                return
    
    def count_real_tokens(tokens) -> int:
        count = 0
        for token in tokens:
            if type(token) == str or token in GRAMMAR:
                count += 1
        return count
    
    def is_recursive(variation: tuple, grammar: list, root_index: int) -> bool:
        # 1. find the grammar type (eg: EXPR)
        # 2. if there is no token of that type in the variation, return False
        # 3. otherwise, find the index of the variation in the grammar
        # 4. if the index of the variation is greater that the index of the root variation return True
        # 5. otherwise return False

        #find grammar type (eg: EXPR)
        grammar_type = -1
        for type in GRAMMAR:
            if GRAMMAR[type] == grammar:
                grammar_type = type
                break
        
        # if there is no token of that type in the variation, return False
        if grammar_type == -1 or grammar_type != variation[0]:
            return False
        
        # print(f"{variation = }")
        # print(f"{TOKEN_TYPE_STR[grammar_type] = }")
        # print(f"{root_index = }")

        # find the index of the variation in the grammar
        variation_index = grammar.index(variation)
        # print(f"{variation_index = }")
        # print(f"{variation_index <= root_index = }")

        return variation_index <= root_index

    def make(grammar: list,
             syntax_tree: list,
             compound=False,
             decl=False,
             scope:dict={NEW_SCOPE:''},
             call=False,
             arg=False,
             set_size=False,
             root_index=-1,
             md=['',0,1]) -> bool:
        #md: function call name, function argument counter, var size
        nonlocal token_index, max_index
        if type(grammar) == int:
            if grammar == tk_type(tokens[token_index]):
                syntax_tree.append(tokens[token_index])
                if grammar == IDENTIFIER:
                    var_name = tokens[token_index][0]
                    bol = tokens[token_index][2]
                    i = tokens[token_index][3]
                    next_line = program.find('\n', bol)
                    # print(var_name, decl, set_size)
                    if decl:
                        # print('declaration:', var_name, '| size:', md[2], '| size size?:', set_size)
                        # if set_size:
                        #     md[2] = 1
                        if var_name in scope:
                            throw_error(
                                line_nb= program.count('\n', 0, bol),
                                msg= f"Declaration error; already in scope '{var_name}'",
                                line= program[bol:next_line],
                                ind= i-bol-len(var_name),
                            )

                        scope[var_name] = [[], md[2]] if call else [None, md[2]]
                        if arg:
                            add_func_arg(scope, md[2])
                        elif call:
                            md[0] = var_name
                        # print(scope)
                    elif var_name not in scope:
                        throw_error(
                            line_nb= program.count('\n', 0, bol),
                            msg= f"Name error; out of scope '{var_name}'",
                            line= program[bol:next_line],
                            ind= i-bol-len(var_name),
                        )
                    elif call and scope[var_name][0] == None:
                        # throw_error(
                        #     line_nb= program.count('\n', 0, bol),
                        #     msg= f"Type error; uncallable '{var_name}'",
                        #     line= program[bol:next_line],
                        #     ind= i-bol-len(var_name),
                        # )
                        return False
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
                            if scope[md[0]][0][md[1]] != tk_type(scope[var_name]):
                                throw_error(
                                    line_nb= program.count('\n', 0, bol),
                                    msg= f"Type error; in '{md[0]}' call, "\
                                         f"incorrect argument type of '{var_name}'\n"\
                                         f"Expected {scope[md[0]][0][md[1]]} "\
                                         f"byte(s), instead got {tk_type(scope[var_name])} byte(s)",
                                    line= program[bol:next_line],
                                    ind= i-bol-len(var_name),
                                )
                            md[1] += 1
                elif grammar == INT_LIT and set_size:
                    # print('set size at:', tokens[token_index][0])
                    md[2] = int(tokens[token_index][0])
                    if md[2] < 1:
                        bol = tokens[token_index][2]
                        i = tokens[token_index][3]
                        next_line = program.find('\n', bol)
                        throw_error(
                            line_nb= program.count('\n', 0, bol),
                            msg= f"Declaration error; variable cannot have zero size",
                            line= program[bol:next_line],
                            ind= i-bol-len(str(md[2])),
                        )
                token_index += 1
                max_index = max(max_index, token_index)
                return True
            else:
                return False
            
        return_index = token_index
        # print('grammar', grammar, '| root token:', tokens[root_index][0])
        for i, variation in enumerate(grammar):
            valid = True
            decl = call = arg = set_size = False

            #Ensure to skip if left-most token is same grammar
            if is_recursive(variation, grammar, root_index): continue

            # print('variation:', variation, '| looked at token:', tokens[token_index][0])
            token_index = return_index
            syntax_tree.clear() #THIS MAY BE PRONE TO FUCKING UP IDK
            for token in variation:
                # print(tokens[token_index][0], token)
                temp_tree = []

                if token in GRAMMAR and GRAMMAR[token] == grammar:
                    next_root_index = i
                else:
                    next_root_index = -1

                if token == NEW_SCOPE:
                    scope = dict(scope)
                    if scope[NEW_SCOPE] == '':
                        scope[NEW_SCOPE] = 'global'
                    elif decl and call:
                        scope[NEW_SCOPE] += '_' + md[0]
                    else:
                        scope[NEW_SCOPE] += '_' + str(random())[2:]
                    syntax_tree.append((scope, NEW_SCOPE))
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
                    while make([token], temp_tree, True, decl, scope, call, arg, set_size, next_root_index):
                        syntax_tree.extend(temp_tree)
                        temp_tree = []
                    if len(temp_tree) == count_real_tokens(token) - 1:
                        syntax_tree.extend(temp_tree)
                elif type(token) == str and token == tk_type(tokens[token_index]):
                    # syntax_tree.append(tokens[token_index])
                    token_index += 1
                    max_index = max(max_index, token_index)
                elif type(token) == int and \
                    make(GRAMMAR[token], temp_tree, compound, decl, scope, call, arg, set_size, next_root_index):
                    if len(temp_tree) == 1 and token == tk_type(temp_tree[0]) or \
                        token == ARG_DECL:
                        syntax_tree.append(temp_tree[0])
                    else:
                        syntax_tree.append((temp_tree, token))
                else:
                    valid = False
                    break
            if valid: break
        
        if not (compound or valid):
            bol = tokens[max_index][2]
            i = tokens[max_index][3]
            next_line = program.find('\n', bol)
            throw_error(
                line_nb= program.count('\n', 0, bol),
                msg= f"Syntax error; unexpected '{tokens[max_index][0]}'",
                line= program[bol:next_line],
                ind= i-bol-len(tokens[max_index][0]),
            )
        return valid


    make(GRAMMAR[PROGRAM], syntax_tree)
    
    return syntax_tree

def print_parsed_code(syntax_tree: list[tuple], indent=0) -> None:
    for branch in syntax_tree:
        if type(branch[0]) == list:
            try:
                print(' ' * indent + TOKEN_TYPE_STR[tk_type(branch)] + ': ')
            except KeyError:
                print(' ' * indent + "/!\\ Undefined behavior: ")
            print_parsed_code(branch[0], indent+2)

        elif type(branch[0]) == dict:
            scope = branch[0]
            print(' ' * indent + "SCOPE:")
            for var in scope:
                if var == NEW_SCOPE:
                    print(' ' * indent + f"  USING: {scope[var]}")
                elif scope[var][0] == None:
                    print(' ' * indent + f"  '{var}': {str(tk_type(scope[var]))} byte(s)")
                else:
                    print(' ' * indent + f"  '{var}': ({str(scope[var][0])[1:-1]})" \
                          f" -> {str(tk_type(scope[var]))} byte(s)")

        else:
            try:
                print(' ' * indent + TOKEN_TYPE_STR[tk_type(branch)] + ': ' + str(branch[0]))
            except KeyError:
                print(' ' * indent + f"/!\\ Undefined behavior: " + str(branch[0]))

def no_output(_type):
    return _type == STATEMENT or \
           _type == EXPR or \
           _type == BOOL_EXPR or \
           _type == PROG_BODY or \
           _type == PROGRAM or \
           _type == END_OF_FILE or \
           _type == NEW_SCOPE

def get_expr(expr: list, namespace: str):
    if tk_type(expr[0]) == INT_LIT:
        return ['    ldi ', tk_name(expr[0])]
    elif tk_type(expr[0]) == IDENTIFIER:
        if len(expr) == 1:
            return ['    lda ', namespace, '_', tk_name(expr[0])]
    else:
        raise NotImplementedError("Expr not implemented")


def generate_code(syntax_tree: list, _type: int, namespace: str,
    lines: list[list[str]] = [['/ SBB COMPILER OUTPUT compiler.py\n']]) -> str:

    if no_output(_type):
        for branch in syntax_tree:
            if tk_type(branch) == END_OF_FILE:
                lines += [['\nstart:'],
                          ['    jsr ', namespace, '_main'],
                          ['    hlta']]
                for i in range(len(lines)):
                    lines[i] = ''.join(lines[i])
                return '\n'.join(lines)
            elif tk_type(branch) == NEW_SCOPE:
                pass
            else:
                generate_code(tk_name(branch), tk_type(branch), namespace, lines)

    elif _type == FUNCTION:
        func_id = tk_name(syntax_tree[0])
        scope = tk_name(syntax_tree[1])
        arg_names = []
        arg_sizes = []
        for i in range(2, len(syntax_tree)):
            if tk_type(syntax_tree[i]) != ARG_DECL: break

            arg = tk_name(syntax_tree[i])
            if tk_type(arg[0]) == INT_LIT:
                arg_sizes.append(int(tk_name(arg[0])))
                arg_names.append(tk_name(arg[1]))
            else:
                arg_sizes.append(1)
                arg_names.append(tk_name(arg[0]))

        #TODO: arg support
        lines.append([namespace, '_', func_id, ':'])
        generate_code(tk_name(syntax_tree[-1]), tk_type(syntax_tree[-1]), scope[NEW_SCOPE], lines)
    
    elif _type == RETURN_ST:
        lines.extend([
            get_expr(tk_name(syntax_tree[0]), namespace),
            ['    ret']
        ])
    
    elif _type == VAR_EQ:
        var_id = tk_name(syntax_tree[0])
        expr = tk_name(syntax_tree[1])
        lines.extend([
            get_expr(expr, namespace),
            ['    sta ', namespace, '_', var_id]
        ])
        

def optimise():
    pass

    #LEVEL 1 OPTIMISATIONS:
        # sta x
        # lda x
        # -> delete lda x

        # ...
        # sta x
        # ...
        # sta x
        # -> delete the first sta x

        # ldi a
        # ldi b
        # -> delete ldi a

        # lda x
        # lda y
        # -> delete lda x

if __name__ == '__main__':
    with open('./sbb_lang_files/program.sbb') as program:
        program = program.read()

        start = perf_counter()
        tokens = lexer(program)
        print(f'Generated tokens in {(perf_counter()-start)*1000:.2f}ms')

        start = perf_counter()
        syntax_tree = parser(program, tokens)
        print(f'Parsed in {(perf_counter()-start)*1000:.2f}ms')
        print_parsed_code(syntax_tree)

        start = perf_counter()
        lines = generate_code(syntax_tree, PROGRAM, syntax_tree[0][0][NEW_SCOPE])
        special_mode = [False] * 7 + [True]
        ini_program_size = run_program(lines.split('\n'), *special_mode)
        print(f'Generated draft code in {(perf_counter()-start)*1000:.2f}ms ({ini_program_size} bytes)')

        with open("./sbbasm_program_files/program.sbbasm", 'w') as asm_file:
            asm_file.write(lines)