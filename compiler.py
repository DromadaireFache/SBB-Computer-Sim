from sbb_grammar import *
from time import perf_counter, sleep
from asm import run_program
from copy import deepcopy
from os import system, path
from sys import argv

RT_COMPILE = False
MAX_LVL = 2
LVL = 2
# RUN THIS COMMAND:
# python compiler.py "./sbb_lang_files/program.sbb" "./sbbasm_program_files/program.sbbasm"

KEYWORDS = []
OPERATORS = ['//']

def add_keywords_and_operators(variation, kw: list[str], op: list[str]):
    if not isinstance(variation, tuple): variation = (variation,)
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

class Token:
    def __init__(self, value, typ, bol=0, i=0, program='', file='', line_nb=0):
        self.value = value
        self.type = typ
        ind = i-bol-len(self.value)
        self.loc = f"{file}:{line_nb+1}:{ind+1}:"
        self.target = program[bol:].split('\n')[0] + '\n' + (' ' * ind) + '^'.ljust(len(self.value), '~')
    
    def __str__(self):
        if isinstance(self.type, str):
            return f"{self.loc} '{self.value}'"
        elif istokentype(self.type, globals()):
            return f"{self.loc} {namestr(self.type, globals())}; '{self.value}'"
        else:
            return f"{self.loc} /!\\ Undefined token type; '{self.value}'"
    
    def error(self, msg='Unspecified error;'):
        print(self.loc, msg)
        print(self.target)
        if RT_COMPILE:
            raise SyntaxWarning
        else:
            exit(1)
    
    def get(self):
        return (self.value, self.type)

def throw_error(line_nb: int, msg: str, line: str, ind: int | None = None):
    print(f"{'missing path'}:{line_nb+1}:{ind+1}: {msg}")
    print(line)
    if ind != None:
        print('^~~'.rjust(ind+3))
    if RT_COMPILE:
        raise SyntaxWarning
    else:
        exit(1)

def lexer(program: str, filepath: str, define=False) -> list[Token]:
    '''
    Lexical analysis breaks the source code into tokens like keywords, 
    identifiers, operators, and punctuation.
    '''
    TYPE_NULL = 0
    TYPE_WORD = 1
    TYPE_OPER = 2
    TYPE_STR  = 3
    CHARS_NULL = ' \t\n'
    CHARS_OPER = '*&|+-/^=<>!'
    CHARS_WORD = '_'

    tokens: list[Token] = []
    token = ''
    token_type = TYPE_NULL
    line_nb = 0
    bol = 0

    def add_token(token: str):
        if token != '':
            if token.isidentifier() and token not in KEYWORDS:
                typ = IDENTIFIER
            elif token[0] == token[-1] == '"':
                typ = STR_LIT
            elif token.isnumeric():
                typ = INT_LIT
            else:
                try:
                    token = str(int(token, base=2))
                    typ = INT_LIT
                except ValueError:
                    try:
                        token = str(int(token, base=16))
                        typ = INT_LIT
                    except ValueError:
                        if token_type == TYPE_WORD and not token.isidentifier():
                            Token(token, -1, bol, i, program, filepath, line_nb)\
                            .error(f"Syntax error; invalid identifier '{token}'")
                        else:
                            typ = token
            tokens.append(Token(token, typ, bol, i, program, filepath, line_nb))

    #make a list of tokens and their type
    i = 0
    for i, char in enumerate(program):
        if token == '//':
            if char == '\n':
                token = ''
                token_type = TYPE_NULL
                line_nb += 1
                bol = i + 1
            continue

        if token_type == TYPE_STR:
            if char == '"':
                if token[-1] == '\\' and \
                    not (len(token) > 2 and token[-2] == '\\'):
                    token = token[:-1] + char
                else:
                    i += 1
                    add_token(token + char)
                    token = ''
                    token_type = TYPE_NULL
            elif char == '\n':
                Token(token, -1, bol, i, program, filepath, line_nb)\
                .error("Syntax error; missing terminating '\"' character")
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
            i += 1
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
    
    if token != '': add_token(token)
    if not define: tokens.append(Token('', END_OF_FILE, bol, i, program, filepath, line_nb))
    return preprocess(tokens, define)

def preprocess(tokens: list[Token], define=False) -> list[Token]:
    #imports
    setimport = False
    for i, token in enumerate(tokens):
        if setimport:
            if token.type == STR_LIT:
                importpath = token.value[1:-1]
                if path.isfile(importpath):
                    with open(importpath) as importprogram:
                        importprogram = lexer(importprogram.read(), importpath)[:-1]
                        tokens = tokens[:i-1] + importprogram + (tokens[i+1:] if i != len(tokens) else [])
                        return preprocess(tokens)
                elif not define:
                    token.error("Import error; provided file path does not exist")
            elif not define:
                token.error("Import error; expected file path as string")
        else:
            setimport = token.type == 'import'

    #define
    setdefine = 0
    for i, token in enumerate(tokens):
        if setdefine == 1:
            # print('define:', token)
            if token.type == IDENTIFIER:
                defineid = token
                setdefine = 2
            elif not define:
                token.error("Define error; expected identifier to define")
        elif setdefine == 2:
            if token.type == STR_LIT:
                defineto = lexer(token.value[1:-1], '', define=True)
                tokens = tokens[:i-2] + (tokens[i+1:] if i != len(tokens) else [])
                newtokens = []
                for token in tokens:
                    if token.value == defineid.value:
                        for thing in defineto:
                            thing.loc = token.loc
                            thing.target = token.target
                        newtokens.extend(defineto)
                    else:
                        newtokens.append(token)
                return preprocess(newtokens)
            elif not define:
                token.error("Define error; expected string as replacement")
        else:
            setdefine = int(token.type == 'define')

    return tokens

def tk_name(token: tuple) -> str:
    return token[0]

def tk_type(token: tuple) -> int|str:
    return token[1]

class Obj:
    def __init__(self, tk: Token, scope: dict, call=False, size=1, const=False):
        self.tk = tk
        self.id = scope[NEW_SCOPE] + '_' + tk.value
        self.callable = call
        self.size = size
        if call:
            self.args = []
        else:
            self.const = const
    
    def add_arg(self, size):
        if self.callable:
            self.args.append(size)
        else:
            self.tk.error()
    
    def __str__(self):
        if self.callable:
            return f"'{self.id}': {tuple(self.args)} -> {self.size} byte{'' if self.size == 1 else 's'}"
        else:
            return f"'{self.id}': {self.size} byte{'' if self.size == 1 else 's'}"

def parser(tokens: list[Token]) -> list:
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
            if grammar == tokens[token_index].type:
                syntax_tree.append(tokens[token_index].get())
                if grammar == IDENTIFIER:
                    namespace = scope[NEW_SCOPE] + '_'
                    var_name = tokens[token_index].value
                    # print(var_name, decl, set_size)
                    if decl:
                        # print('declaration:', var_name, '| size:', md[2], '| size size?:', set_size)
                        # if set_size:
                        #     md[2] = 1
                        scope_var_name = namespace+var_name
                        if scope_var_name in scope:
                            tokens[token_index].error(f"Declaration error; already in scope '{var_name}'")
                        if call and scope_var_name == 'global_main' and md[2] != 1:
                            tokens[token_index].error(f"Declaration error; invalid type for '{var_name}'")
                        scope[scope_var_name] = [[], md[2]] if call else [None, md[2]]
                        if arg:
                            add_func_arg(scope, md[2])
                        elif call:
                            md[0] = scope_var_name
                        # print(scope)
                    elif get_var_name(var_name, scope) == 0:
                        tokens[token_index].error(f"Name error; out of scope '{var_name}'")
                    elif call and scope[get_var_name(var_name,scope)][0] == None:
                        # tokens[token_index].error(f"Type error; uncallable '{var_name}'")
                        return False
                    
                    if not decl:
                        if call:
                            md[0] = get_var_name(var_name, scope)
                            md[1] = 0
                        elif arg:
                            if len(scope[md[0]][0]) <= md[1]:
                                tokens[token_index].error(f"Argument error; in '{md[0]}' call, "\
                                                          f"argument '{var_name}' not expected")
                            if scope[md[0]][0][md[1]] != tk_type(scope[var_name]):
                                tokens[token_index].error(f"Type error; in '{md[0]}' call, "\
                                                          f"incorrect argument type of '{var_name}'\n"\
                                                          f"Expected {scope[md[0]][0][md[1]]} "\
                                                          f"byte(s), instead got {tk_type(scope[var_name])} byte(s)")
                            md[1] += 1
                elif grammar == INT_LIT and set_size:
                    # print('set size at:', tokens[token_index][0])
                    md[2] = int(tokens[token_index].value)
                    if md[2] < 1:
                        tokens[token_index].error(f"Declaration error; variable cannot have zero size")
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
            if not isinstance(variation, tuple): variation = (variation,)

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
                    scope = deepcopy(scope)
                    if scope[NEW_SCOPE] == '':
                        scope[NEW_SCOPE] = 'global'
                    elif decl and call:
                        scope[NEW_SCOPE] = md[0]
                    else:
                        scope[NEW_SCOPE] = 'local' + str(enum())
                    syntax_tree.append((scope, NEW_SCOPE))
                elif token == DECL:
                    decl = True
                elif token == CALL:
                    call = True
                elif token == ARG:
                    arg = True
                elif token == END_OF_ARGS:
                    print(scope, md[0])
                    if len(scope[md[0]][0]) != md[1]:
                        tokens[token_index].error(f"Arugment error; in '{md[0]}' call, "\
                                                  f"too few arguments")
                elif token == SET_SIZE:
                    md[2] = 1
                    set_size = True
                elif type(token) == tuple:
                    while make([token], temp_tree, True, decl, scope, call, arg, set_size, next_root_index):
                        syntax_tree.extend(temp_tree)
                        temp_tree = []
                    if len(temp_tree) == count_real_tokens(token) - 1:
                        syntax_tree.extend(temp_tree)
                elif type(token) == str and token == tokens[token_index].type:
                    # syntax_tree.append(tokens[token_index])
                    token_index += 1
                    max_index = max(max_index, token_index)
                elif type(token) == int and \
                    make(GRAMMAR[token], temp_tree, compound, decl, scope, call, arg, set_size, next_root_index):
                    set_size = False
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
            tokens[max_index].error(f"Syntax error; unexpected '{tokens[max_index].value}'")
        return valid


    make(GRAMMAR[PROGRAM], syntax_tree)
    
    return syntax_tree

def print_parsed_code(syntax_tree: list[tuple], indent=0) -> None:
    for branch in syntax_tree:
        if type(branch[0]) == list:
            try:
                print(' ' * indent + namestr(tk_type(branch), globals()) + ': ')
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
                print(' ' * indent + namestr(tk_type(branch), globals()) + ': ' + str(branch[0]))
            except KeyError:
                print(' ' * indent + f"/!\\ Undefined behavior: " + str(branch[0]))

def no_output(_type):
    return _type == STATEMENT or \
           _type == EXPR or \
           _type == BOOL or \
           _type == PROG_BODY or \
           _type == PROGRAM or \
           _type == END_OF_FILE or \
           _type == NEW_SCOPE

def get_var_name(id: str, scope: dict):
    for key in reversed(scope):
        if key == NEW_SCOPE: continue

        if key.split('_')[-1] == id:
            return key
    
    return 0
    # raise LookupError(f"'{id}' not found within scope {list(scope)}")

def get_expr(expr: list, scope: dict):
    expr_type = tk_type(expr[0])
    if expr_type == INT_LIT:
        return [['    ldi ', tk_name(expr[0])]]
    elif expr_type == IDENTIFIER:
        if len(expr) == 1:
            return [['    lda ', get_var_name(tk_name(expr[0]), scope)]]
    elif expr_type == LONE_EX:
        if len(expr) == 1:
            return get_expr(tk_name(expr[0]), scope)
        
        a = tk_name(expr[0])[0]
        b = tk_name(tk_name(expr[1])[0])[0]
        op = tk_type(expr[1])

        if op == ADD_EX:
            op = '    add# ' if tk_type(b) == INT_LIT else '    add '
        elif op == SUB_EX:
            op = '    sub# ' if tk_type(b) == INT_LIT else '    sub '
        elif op == MULT_EX:
            op = '    multl# ' if tk_type(b) == INT_LIT else '    multl '
        elif op == CMP_EX:
            op = '    cmp# ' if tk_type(b) == INT_LIT else '    cmp '
        else:
            try:
                raise NotImplementedError(f"{namestr(tk_type(expr[0]), globals())} not implemented")
            except KeyError:
                raise NotImplementedError("Double expr not implemented")

        load = '    ldi ' if tk_type(a) == INT_LIT else '    lda '
        a = tk_name(a) if tk_type(a) == INT_LIT else get_var_name(tk_name(a), scope)
        b = tk_name(b) if tk_type(b) == INT_LIT else get_var_name(tk_name(b), scope)
        return [[load, a], [op, b]]
    elif expr_type == EXPR or expr_type == TERM or expr_type == FACTOR:
        return get_expr(tk_name(expr[0]), scope)
    else:
        try:
            raise NotImplementedError(f"{namestr(tk_type(expr[0]), globals())} not implemented")
        except KeyError:
            raise NotImplementedError("Expression not implemented")

def get_jump(type: int, scope_str: str) -> list[list[str]] | None:
    if type == BOOL_EQ:
        return [['    jpne ', '&' + scope_str]]
    if type == BOOL_NEQ:
        return [['    jpeq ', '&' + scope_str]]
    if type == BOOL_LTE:
        return [['    jpgt ', '&' + scope_str]]
    if type == BOOL_LT:
        return [['    jpgt ', '&' + scope_str], ['    jpeq ', '&' + scope_str]]
    if type == BOOL_GTE:
        return [['    jplt ', '&' + scope_str]]
    if type == BOOL_GT:
        return [['    jplt ', '&' + scope_str], ['    jpeq ', '&' + scope_str]]
    else:
        return None

def get_bool(expr: list, scope: dict, scope_str: str):
    expr_type = tk_type(expr[0])
    jump_op = get_jump(expr_type, scope_str)
    if jump_op != None:
        expr1 = tk_name(expr[0])[0]
        expr2 = tk_name(expr[0])[1]

        if tk_type(expr1) == tk_type(expr2) == LONE_EX:
            return [
                *get_expr([expr1, ([expr2], CMP_EX)], scope),
                *jump_op
            ]
        elif tk_type(expr1[0][0]) == LONE_EX or tk_type(expr2[0][0]) == LONE_EX:
            if tk_type(expr1[0][0]) == LONE_EX:
                expr1, expr2 = expr2, expr1
            cmp = get_expr(tk_name(expr2[0][0]), scope)
            cmp[0][0] = cmp[0][0].replace('ldi', 'cmp#')
            cmp[0][0] = cmp[0][0].replace('lda', 'cmp')
            return [
                *get_expr(tk_name(expr1), scope),
                *cmp,
                *jump_op
            ]
        else:
            return [
                *get_expr(tk_name(expr1), scope),
                ['    sta ', '__bool_temp__'],
                *get_expr(tk_name(expr2), scope),
                ['    cmp ', '__bool_temp__'],
                *jump_op
            ]
        
    elif expr_type == BOOL_TRUE:
        return []
    
    elif expr_type == BOOL_FALSE:
        return [['    jump ', '&' + scope_str]]

    else:
        try:
            raise NotImplementedError(f"{namestr(tk_type(expr[0]), globals())} not implemented")
        except KeyError:
            raise NotImplementedError("Expression not implemented")

def generate_code(syntax_tree: list, _type: int, scope: dict,
    lines: list[list[str]] = [['/ SBB COMPILER OUTPUT compiler.py']]):

    if no_output(_type):
        for branch in syntax_tree:
            if tk_type(branch) == END_OF_FILE:
                if scope[NEW_SCOPE] + '_main' in scope:
                    lines += [['\nstart:'],
                            ['    jsr ', scope[NEW_SCOPE] + '_main'],
                            ['    halt']]
                return lines
            elif tk_type(branch) == NEW_SCOPE:
                pass
            else:
                generate_code(tk_name(branch), tk_type(branch), scope, lines)

    elif _type == SCOPED_ST:
        assert len(syntax_tree) == 2, f"Unexpected behavior for {namestr(_type, globals())}"
        scope = tk_name(syntax_tree[0])
        generate_code(tk_name(syntax_tree[1]), tk_type(syntax_tree[1]), scope, lines)

    elif _type == FUNCTION:
        assert len(syntax_tree) >= 3, f"Unexpected behavior for {namestr(_type, globals())}"
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
        lines.append(['\n' + scope[NEW_SCOPE] + ':'])
        generate_code(tk_name(syntax_tree[-1]), tk_type(syntax_tree[-1]), scope, lines)
        if not ''.join(lines[-1]).strip().startswith('ret'):
            lines.append(['    ret# ', '0'])
    
    elif _type == RETURN_ST:
        if len(syntax_tree) > 0:
            lines.extend(get_expr(tk_name(syntax_tree[0]), scope))
        lines.append(['    ret'])
    
    elif _type == VAR_EQ:
        var_id = tk_name(syntax_tree[0])
        expr = tk_name(syntax_tree[1])
        lines.extend(get_expr(expr, scope))
        lines.append(['    sta ', get_var_name(var_id, scope)])
    
    elif _type == IF_ST:
        assert 2 <= len(syntax_tree) <= 3, f"Unexpected behavior for {namestr(_type, globals())}"
        scope_str = tk_name(tk_name(syntax_tree[1])[0])[NEW_SCOPE]
        lines.extend(get_bool(tk_name(syntax_tree[0]), scope, scope_str))
        generate_code(tk_name(syntax_tree[1]), SCOPED_ST, scope, lines)

        if len(syntax_tree) == 3 and len(syntax_tree[2][0][1][0]) > 0: #if-else
            lines.append(['    jump ', '&else_' + scope_str] )
            lines.append(['    *' + scope_str])
            generate_code(tk_name(syntax_tree[2]), SCOPED_ST, scope, lines)
            lines.append(['    *else_' + scope_str])

        else: #if-no-else
            lines.append(['    *' + scope_str])
    
    elif _type == WHILE_ST:
        assert len(syntax_tree) == 2, f"Unexpected behavior for {namestr(_type, globals())}"
        scope_str = tk_name(tk_name(syntax_tree[1])[0])[NEW_SCOPE]
        lines.append(['    *loop_' + scope_str])
        lines.extend(get_bool(tk_name(syntax_tree[0]), scope, scope_str))
        generate_code(tk_name(syntax_tree[1]), SCOPED_ST, scope, lines)
        lines.append(['    jump ', '&loop_' + scope_str] )
        lines.append(['    *' + scope_str])
    
    elif _type == LET_DECL:
        assert len(syntax_tree) == 2, f"Unexpected behavior for {namestr(_type, globals())}"
        name = get_var_name(tk_name(syntax_tree[0]), scope)
        value = tk_name(syntax_tree[1])
        lines.insert(1, [name, ' = ', value, '/NOTAB'])

def join_lines(lines):
    for i in range(len(lines)):
        if lines[i][-1] == '/NOTAB':
            lines[i] = ''.join(lines[i][:-1])
        else:
            lines[i] = '\t'.join(lines[i])
    new_lines = []
    for line in lines:
        if line != '/REMOVED':
            new_lines.append(line)
    return '\n'.join(new_lines)

def get_program_size(lines):
    temp_lines = deepcopy(lines)
    for i in range(len(temp_lines)):
        temp_lines[i] = ''.join(temp_lines[i])
    special_mode = [False] * 7 + [True]
    return run_program(temp_lines, *special_mode)

def skipable(line, excep: None|list[str]):
    join_line = ''.join(line)
    if '*' in join_line or ':' in join_line:
        return False
    stripped_line = line[0].strip()
    if excep == None and stripped_line != '':
        return stripped_line[0] == '/' or stripped_line == 'noop'
    else:
        return stripped_line not in excep

def binary_remove(lines:list[list[str]], pattern: tuple[str, str],
                  del_first=True, excep:list[str]|None=None, catch=True, mod=False):
    '''
    This is to remove binary instructions (eg: lda x)
    pattern: do something if instance of 2nd pattern found after instance of 1st
    del_first: True - delete 1st pattern instance, False - delete 2nd
    excep: None by default, otherwise will stop looking if an excep is found
    catch: True - operands need to match, False - only pattern needs to match
    mod: True - concat # and 1st pattern operand to 2nd pattern instance, False - nothing changes
    '''
    if catch:
        catch = pattern[0] != pattern[1] or excep != None
    for i in range(len(lines)):
        if len(lines[i]) != 2: continue #MIGHT NEED TO BE CHANGED IF eg: lda x *haha
        if lines[i][0].strip() == pattern[0]:
            if catch:
                operand = lines[i][1].strip()

            for j in range(i+1, len(lines)):
                if lines[j][0].strip() == pattern[1] and \
                    (mod or not catch or catch and lines[j][1].strip() == operand):
                    if del_first and '*' not in ''.join(lines[i]):
                        if mod:
                            #ldi 5, ret -> ret# 5
                            lines[i] = ['/REMOVED']
                            lines[j][0] += '# '
                            lines[j].insert(1, operand)
                        else:
                            lines[i] = ['/REMOVED']
                    #WARNING: this might break with *abc
                    else:
                        if pattern[0] != pattern[1]:
                            lines[i+1:j+1] = [['/REMOVED']] * (j-i)
                        else:
                            lines[j] = ['/REMOVED']

                elif not skipable(lines[j], excep):
                    break

def depend_remove(lines, dep: str, ind: list[str]):
    for i in range(len(lines)):
        if len(lines[i]) != 2: continue
        if lines[i][0].strip() == dep:
            operand = lines[i][1].strip()
            found = False
            for line in lines:
                if line[0].strip() in ind and line[1].strip() == operand:
                    found = True
            if not found:
                lines[i] = ['/REMOVED']

def is_jump(line: list[str]):
    if line == []: return False
    op = line[0].strip()
    return op == 'jpne' or op == 'jpeq' \
            or op == 'jplt' or op == 'jpgt' \
            or op == 'jump' or op == 'jmpz' \
            or op == 'jmpz' or op == 'jmpn'

def no_label(line, reverse_delete):
    if reverse_delete and (line[0].strip() == 'sta' or is_jump(line)): return False
    line = ''.join(line)
    return '*' not in line and ':' not in line

def remove_to_label(lines, pattern: str, reverse_delete=False):
    for i in range(len(lines)):
        if lines[i][0].strip() == pattern:
            if reverse_delete:
                i -= 1
                while i>=0 and no_label(lines[i], reverse_delete):
                    lines[i] = ['/REMOVED']
                    i -= 1
            else:
                i += 1
                while i<len(lines) and no_label(lines[i], reverse_delete):
                    lines[i] = ['/REMOVED']
                    i += 1

def remove_useless_labels(lines: list[list[str]]):
    #find the labels that are used for jumps
    used_labels = []
    for line in lines:
        if is_jump(line):
            if line[1].strip()[0] == '&':
                used_labels.append(line[1].strip('&'))
    
    #remove the labels that are not used for jumps
    for i in range(len(lines)):
        if lines[i][-1].strip()[0] == '*':
            if lines[i][-1].strip()[1:] not in used_labels:
                lines[i].pop()
                if lines[i] == []: lines[i].append('/REMOVED')

def replace_pattern(lines: list[list[str]], pattern: list[str], repl: list[str]):
    for i in range(len(lines)):
        if [s.strip() for s in lines[i]] == pattern:
            lines[i] = deepcopy(repl)

def modify_linked_jumps(lines: list[list[str]]):
    '''
    if any jump points to a 'jump' then it will where it points to accordingly
    jmpz &x    jmpz y
    *x      -> *x
    jump y     jump y
    '''
    for i in range(len(lines)):
        if is_jump(lines[i]):
            label_str = '    *' + lines[i][1].strip()[1:]

            for j in range(len(lines)-1):
                if lines[j][0] == label_str:
                    for k in range(j+1, len(lines)):
                        if skipable(lines[k], None): continue
                        if lines[k][0].strip() == 'jump':
                            lines[i][1] = lines[k][1]
                        break
                    break

def count_changes(lines):
    changes = 0
    for line in lines:
        if line == ['/REMOVED']: changes += 1
    return changes

def optimize(lines: list[list[str]], lvl = 0) -> str:
    if lvl == 0: return join_lines(lines)
    size_i = get_program_size(lines)
    LOAD_INS = ['lda', 'add', 'sub', 'multl', 'multh', 'and', 'or', 'cmp']

    prev_change = 0
    depth = 0
    for _ in range(lvl**2):
        depth += 1
        # LEVEL 1 OPTIMISATIONS:
        # (delete 1 line at a time)
        binary_remove(lines, ('sta', 'lda'), del_first=False, excep=LOAD_INS+['sta'])
        binary_remove(lines, ('lda', 'sta'), del_first=False)
        binary_remove(lines, ('sta', 'sta'), excep=LOAD_INS)
        depend_remove(lines, 'sta', LOAD_INS)
        binary_remove(lines, ('ldi', 'ldi'))
        binary_remove(lines, ('lda', 'lda'))
        binary_remove(lines, ('ldi', 'ldi'), del_first=False, excep=LOAD_INS)
        binary_remove(lines, ('lda', 'lda'), del_first=False, excep=LOAD_INS)
        binary_remove(lines, ('ldi', 'lda'), catch=False)
        binary_remove(lines, ('lda', 'ldi'), catch=False)

        # LEVEL 2 OPTIMISATIONS:
        # (delete multiple lines and/or modify a line to delete another)
        if lvl > 1:
            binary_remove(lines, ('ldi', 'ret'), mod=True)
            binary_remove(lines, ('ldi', 'push'), mod=True)
            binary_remove(lines, ('ldi', 'halt'), mod=True)
            remove_to_label(lines, 'ret')
            remove_to_label(lines, 'halt')
            remove_to_label(lines, 'jump')
            remove_to_label(lines, 'ret#')
            remove_to_label(lines, 'ret#', reverse_delete=True)
            remove_to_label(lines, 'halt#')
            remove_to_label(lines, 'halt#', reverse_delete=True)
            remove_useless_labels(lines)
            replace_pattern(lines, ['add#', '1'], ['    inc'])
            replace_pattern(lines, ['sub#', '1'], ['    dec'])
            replace_pattern(lines, ['add#', '255'], ['    dec'])
            replace_pattern(lines, ['sub#', '255'], ['    inc'])
            replace_pattern(lines, ['add#', '0'], ['/REMOVED'])
            replace_pattern(lines, ['sub#', '0'], ['/REMOVED'])
            replace_pattern(lines, ['multl#', '2'], ['    lsh'])
            modify_linked_jumps(lines)
            # sta x    sta x
            # lda y -> add y
            # add x

        # TODO: LEVEL 3 OPTIMISATIONS:
        # (change the order of things to delete unnecessary lines)
        if lvl < 0 or lvl > MAX_LVL:
            raise NotImplementedError(f"Optimisation level {lvl} is not supported")
        
        changes = count_changes(lines)
        if prev_change == changes:
            break
        else:
            prev_change = changes
        
    size_f = get_program_size(lines)
    try:
        size_dif = size_i/size_f
    except ZeroDivisionError:
        size_dif = 1
    except TypeError:
        size_dif = -1

    print(f'Optimization result ({lvl=}, {depth=}):', end=' ')
    if size_dif == 1:
        print(f'{size_i} bytes')
    elif size_dif == -1:
        print(f'{size_i} -> {size_f} bytes')
    else:
        print(f'{size_i} -> {size_f} bytes ({size_dif*100-100:.0f}% improv.)')
    return join_lines(lines)

def load_args():
    assert len(argv) >= 2
    assert path.isfile(argv[1])
    assert argv[1].endswith('.sbb')
    defined_file_creation = len(argv) > 2 and argv[2].endswith('.sbbasm')
    if defined_file_creation:
        assert argv[2].endswith('.sbbasm')
        assert len(argv[2].split('/')) > 1 and argv[2].split('/')[-2] == 'sbbasm_program_files'
    else:
        filename = './sbbasm_program_files/' + argv[1].split('/')[-1] + 'asm'
    global LVL, RT_COMPILE, PRINT_OPTIONS
    PRINT_OPTIONS = {'tokens': False, 'parsedcode': False, 'keywords': False}
    for option in (argv[3:] if defined_file_creation else argv[2:]):
        if option.startswith('-O') and len(option) > 2 and option[2:].isnumeric():
            global LVL
            LVL = int(option[2:])
        elif option == '-rt':
            RT_COMPILE = True
        elif option == '-ppc':
            PRINT_OPTIONS['parsedcode'] = True
        elif option == '-pt':
            PRINT_OPTIONS['tokens'] = True
        elif option == '-pkw':
            PRINT_OPTIONS['keywords'] = True
        else:
            assert False, f"Invalid option {option}"
    return argv[1], argv[2] if defined_file_creation else filename

def main(sourcepath, writepath):
    enum(reset=True)
    if PRINT_OPTIONS['keywords']:
        print('\n~~~~ KEYWORDS ~~~~')
        print(KEYWORDS)

    with open(sourcepath) as program:
        program = program.read()
        start = perf_counter()

        tokens = lexer(program, sourcepath)
        if PRINT_OPTIONS['tokens']:
            print('\n~~~~ TOKENS ~~~~')
            for token in tokens: print(token)

        syntax_tree = parser(tokens)
        if PRINT_OPTIONS['parsedcode']:
            print('\n~~~~ SYNTAX TREE ~~~~')
            print_parsed_code(syntax_tree)

        lines = generate_code(syntax_tree, PROGRAM, syntax_tree[0][0],
                            [['/ SBB COMPILER OUTPUT compiler.py']])
        lines = optimize(lines, lvl=LVL)
        print(f'Compiled in {(perf_counter()-start)*1000:.2f}ms')

    with open(writepath, 'w') as asm_file:
        asm_file.write(lines)

if __name__ == '__main__':
    sourcepath, writepath = load_args()
    while RT_COMPILE:
        sleep(1)
        system('cls')
        try:
            main(sourcepath, writepath)
        except SyntaxWarning: pass
    main(sourcepath, writepath)