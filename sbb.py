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
# python sbb.py "./sbb_lang_files/program.sbb"

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
    def __init__(self, value, typ, bol=0, i=0, program='', file='', line_nb=0, builtin=False):
        self.value = value
        self.type = typ
        if not builtin:
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"','`'): self.str_value = value[1:-1]
            ind = i-bol-len(self.value)
            self.loc = f"{file}:{line_nb+1}:{ind+1}:"
            self.target = program[bol:].split('\n')[0] + '\n' + (' ' * ind) + '^'.ljust(len(self.value), '~')
            self.was_warned = False

    def __str__(self):
        if isinstance(self.type, str):
            return f"{self.loc} '{self.value}'"
        elif istokentype(self.type, globals()):
            return f"{self.loc} {namestr(self.type, globals())}; '{self.value}'"
        else:
            return f"{self.loc} /!\\ Undefined token type; '{self.value}'"
    
    def error(self, msg='Unspecified error;', warning=False):
        if not warning or (warning and not OPTIONS['nowarnings'] and not self.was_warned):
            print(self.loc, msg)
            print(self.target)
        if warning:
            self.was_warned = True
        else:
            print('[SBB-lang Compiler] Compilation terminated; No output file generated')
            if RT_COMPILE:
                raise SyntaxWarning
            else:
                exit(1)
    
    def get(self):
        return (self.value, self.type)

pre_compile_terminate = False
def assert_error(assertion: bool, msg='Unspecified pre-compilation error', kill=False):
    global pre_compile_terminate
    assert type(assertion) == bool
    if not assertion:
        print('[SBB-lang Compiler] Pre-compilation error;', msg)
        pre_compile_terminate = True
    if pre_compile_terminate and kill: exit(1)

def lexer(program: str, filepath: str, define=False, import_=False) -> list[Token]:
    '''
    Lexical analysis breaks the source code into tokens like keywords, 
    identifiers, operators, and punctuation.
    '''
    TYPE_NULL = 0
    TYPE_WORD = 1
    TYPE_OPER = 2
    TYPE_STR  = 3
    TYPE_CHAR = 4
    TYPE_DEF  = 5
    CHARS_NULL = ' \t\n'
    CHARS_OPER = '*&|+-/^=<>!'
    CHARS_WORD = '_'
    QUOTES = {TYPE_STR: '"', TYPE_CHAR: "'", TYPE_DEF: '`'}

    tokens: list[Token] = []
    token = ''
    token_type = TYPE_NULL
    line_nb = 0
    bol = 0

    def add_token(token: str, invalid=False):
        if token != '':
            if token.isidentifier() and token not in KEYWORDS:
                typ = IDENTIFIER
            elif token[0] == token[-1] == '"':
                typ = STR_LIT
            elif token[0] == token[-1] == "'":
                try:
                    typ = INT_LIT
                    tokens.append(Token(token, typ, bol, i, program, filepath, line_nb))
                    token = str(ord(token[1:-1].encode('ascii').decode('unicode_escape')))
                    tokens[-1].value = token
                    if int(token) > 127: raise TypeError
                    return
                except TypeError:
                    tokens.pop()
                    Token(token, -1, bol, i, program, filepath, line_nb)\
                    .error(f"Syntax error; invalid character literal '{token}'", True)
                    invalid = True
            elif token[0] == token[-1] == '`':
                typ = DEFINE
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
                            .error(f"Syntax error; invalid identifier '{token}'", True)
                            invalid = True
                        else:
                            typ = token
            if invalid: typ = INVALID_TK
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

        if token_type in (TYPE_STR, TYPE_CHAR, TYPE_DEF):
            quotes = QUOTES[token_type]
            if char == quotes:
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
                .error(f"Syntax error; missing terminating '{quotes}' character", True)
                add_token(token, True)
                token = ''
                token_type = TYPE_NULL
                line_nb += 1
                bol = i + 1
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
        elif char == "'":
            char_type = TYPE_CHAR
        elif char == '`':
            char_type = TYPE_DEF
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
    
    if token != '' and token != '//': add_token(token)
    if not define: tokens.append(Token('', END_OF_FILE, bol, i, program, filepath, line_nb))
    return preprocess(tokens, define, import_)

def preprocess(tokens: list[Token], define_=False, import_=False) -> list[Token]:
    #imports
    setimport = False
    for i, token in enumerate(tokens):
        if setimport:
            if token.type == STR_LIT:
                importpath = token.str_value
                if path.isfile(importpath):
                    with open(importpath) as importprogram:
                        importprogram = lexer(importprogram.read(), importpath, import_=True)[:-1]
                        tokens = tokens[:i-1] + importprogram + (tokens[i+1:] if i != len(tokens) else [])
                        return preprocess(tokens)
                elif not define_:
                    token.error("Import error; provided file path does not exist")
            elif not define_:
                token.error("Import error; expected file path as string")
        else:
            setimport = token.type == 'import'

    if import_: return tokens
    #define
    setdefine = 0
    for i, token in enumerate(tokens):
        if setdefine == 1:
            # print('define:', token)
            if token.type == IDENTIFIER:
                defineid = token
                setdefine = 2
            elif not define_:
                token.error("Define error; expected identifier to define")
        elif setdefine == 2:
            if token.type in (STR_LIT, INT_LIT, IDENTIFIER, DEFINE):
                defineto = lexer(token.str_value, '', define=True) if token.type == DEFINE else [token]
                tokens = tokens[:i-2] + (tokens[i+1:] if i != len(tokens) else [])
                expanded_from_msg = f"\n{defineid.loc} expanded from '{defineid.value}'\n{defineid.target}\n"
                newtokens = []
                for token in tokens:
                    if token.value == defineid.value:
                        token_loc_msg = token.loc.split('\n')
                        last_loc = token_loc_msg.pop()
                        token_loc_msg = ('\n'.join(token_loc_msg) + expanded_from_msg + last_loc).strip()
                        for thing in defineto:
                            thing.loc = token_loc_msg
                            thing.target = token.target
                        newtokens.extend(defineto)
                    else:
                        newtokens.append(token)
                return preprocess(newtokens)
            elif not define_:
                token.error("Define error; expected definition statement within backtick characters '`'")
        else:
            setdefine = int(token.type == 'define')

    return tokens

def tk_name(token: tuple) -> str:
    return token[0]

def tk_type(token: tuple) -> int|str:
    return token[1]

class Obj:
    def __init__(self, tk: Token, scope: dict[int|str,'str|Obj'], size=1, call=False, const=False):
        self.tk = tk
        self.id = scope[NEW_SCOPE] + '_' + tk.value
        self.callable = call
        self.size = size
        if call != False:
            self.scope = scope
            self.args = []
            if type(call) == list:
                scope[self.id] = self
                for arg in call:
                    arg_name = f"{tk.value}_opr{len(self.args)}_"
                    scope[arg_name] = Obj(Token(arg_name, BUILTIN, builtin=True), scope, arg)
                    self.add_arg(arg)
        else:
            self.const = const

        if type(call) != list and self.id in scope:
            tk.error(f"Declaration error; already in scope '{tk.value}'")
        if call and self.id == 'global_main' and size != 1:
            tk.error(f"Declaration error; invalid type for '{tk.value}'")
        if type(call) != list and ('builtin_' + tk.value) in scope:
            tk.error(f"Declaration error; '{tk.value}' is assigned to a built-in "\
                     f"{'callable' if scope['builtin_' + tk.value].callable else 'variable'}")
    
    def add_arg(self, size):
        if self.callable:
            self.args.append(size)
    
    def __str__(self):
        if self.callable:
            return f"'{self.id}': {tuple(self.args)} -> {byte_s(self.size)}"
        else:
            return f"'{self.id}': {byte_s(self.size)}"

def int_size(int_value, size, is_str=False):
    if is_str: return size == 1
    unsigned = 256**size
    signed = unsigned // 2
    max = unsigned-signed-1
    min = -signed
    return max >= int_value >= min

def count_real_tokens(tokens: list[Token]) -> int:
    count = 0
    for token in tokens:
        if type(token) == str or token in GRAMMAR:
            count += 1
    return count

class TreeData:
    def __init__(self):
        self.decl        = False
        self.call        = False
        self.arg         = False
        self.set_size    = False
        self.assert_type = False
        self.neg         = False
        self.assert_arr  = False

def last_function_in_scope_size(scope: dict[str, Obj], name=False) -> str:
    for obj in list(scope)[1:][::-1]:
        if scope[obj].callable:
            return (obj, scope[obj].size) if name else scope[obj].size
    assert False, f'no function in scope: {scope}'

def byte_s(n):
    assert type(n) == int
    if n == 0: return f'void (0 bytes)'
    if n < 0: return f'passive option enabled: ERROR ({n}) byte?'
    return '1 byte' if n == 1 else f'{n} bytes'

DEFAULT_SCOPE: dict[int|str, str|Obj] = {
    NEW_SCOPE: '',
    'builtin_storechar': Obj(Token('storechar', BUILTIN, builtin=True), {NEW_SCOPE: 'builtin'}, call=[1,1], size=0),
    'builtin_getchar': Obj(Token('getchar', BUILTIN, builtin=True), {NEW_SCOPE: 'builtin'}, call=[1]),
    'builtin_refr': Obj(Token('refr', BUILTIN, builtin=True), {NEW_SCOPE: 'builtin'}, call=True, size=0),
    'builtin_getheap': Obj(Token('getheap', BUILTIN, builtin=True), {NEW_SCOPE: 'builtin'}, call=[1]),
    'builtin_keybin': Obj(Token('keybin', BUILTIN, builtin=True), {NEW_SCOPE: 'builtin'}),
}
fct_scopes = {i: DEFAULT_SCOPE[i].scope for i in DEFAULT_SCOPE if type(i) != int and DEFAULT_SCOPE[i].callable}

def parser(tokens: list[Token]) -> list:
    '''
    Syntax analysis ensures that tokens generated from lexical analysis are
    arranged according to SBB lang grammar.
    '''
    syntax_tree = []
    token_index = 0
    max_index = 0
    global str_lits
    str_lits = ""

    def make(grammar: list,
             syntax_tree: list,
             scope:dict[int|str,str|Obj]=DEFAULT_SCOPE,
             compound = False,
             tree_data = TreeData(),
             data=['',0,1,1,1]) -> bool:
        #data: function call name, function argument counter, var size, expr size, arr size
        nonlocal token_index, max_index
        global str_lits
        if type(grammar) == int:
            if grammar == tokens[token_index].type:
                syntax_tree.append(tokens[token_index].get())
                if grammar == IDENTIFIER:
                    var_name = tokens[token_index].value
                    scope_var_name = scope[NEW_SCOPE] + '_' + var_name
                    # print(var_name, decl, set_size)
                    if tree_data.decl:
                        scope[scope_var_name] = Obj(tokens[token_index], scope, data[2], tree_data.call)
                        if tree_data.arg:
                            scope[data[0]].add_arg(data[2])
                        elif tree_data.call:
                            data[0] = scope_var_name
                        data[3] = scope[scope_var_name].size
                    elif get_var_name(var_name, scope) == 0:
                        tokens[token_index].error(f"Name error; out of scope '{var_name}'")
                    elif tree_data.call and not scope[get_var_name(var_name,scope)].callable:
                        return False
                    
                    if not tree_data.decl:
                        scope_var_name = get_var_name(var_name, scope)
                        size = scope[scope_var_name].size
                        if tree_data.call:
                            data[0] = scope_var_name
                            data[1] = 0
                        elif tree_data.arg:
                            if len(scope[data[0]].args) <= data[1]:
                                tokens[token_index].error(f"Argument error; in '{scope[data[0]].tk.value}' call, "\
                                                          f"argument '{scope_var_name}' not expected")
                            
                            # print(scope[data[0]], data[1], tokens[token_index], namestr(grammar, globals()))   
                            if scope[data[0]].args[data[1]] != size:
                                tokens[token_index].error(f"Type error; in '{scope[data[0]].tk.value}' call, "\
                                                          f"incorrect argument type of '{scope[scope_var_name].tk.value}'\n"\
                                                          f"Expected {byte_s(scope[data[0]].args[data[1]])}, "\
                                                          f"instead got {byte_s(size)}")
                            data[1] += 1
                        elif tree_data.set_size:
                            data[3] = size
                            if scope[scope_var_name].callable:
                                tokens[token_index].error(f"Type error; invalid assignment of '{scope[scope_var_name].tk.value}',\n"\
                                                          f"Callable object cannot be reassigned")
                        if tree_data.assert_type:
                            if data[3] != size:
                                if data[3] != -BOOL_SIZE:
                                    tokens[token_index].error(f"Type error; incorrect argument type of '{scope[scope_var_name].tk.value}',\n"\
                                                              f"Expected {byte_s(data[3])}, instead got {byte_s(size)}")
                                data[3] = size
                            elif tree_data.assert_arr:
                                data[4] = size
                elif grammar == INT_LIT or grammar == STR_LIT:
                    is_str = grammar == STR_LIT
                    if is_str:
                        int_value = len(str_lits.encode('ascii').decode('unicode_escape'))
                        str_lits += tokens[token_index].str_value + '\0'
                        ovf_msg = "string pointer may only have 'var[1]' type"
                        if len(str_lits) > 255:
                            tokens[token_index].error(f"String error; string buffer overflow")
                    else:
                        int_value = int(tokens[token_index].value) * (-1 if tree_data.neg else 1)
                        ovf_msg = "may cause overflowing"
                    syntax_tree[-1] = (str(int_value), syntax_tree[-1][1])
                    expected_size = 1 if tree_data.assert_arr else data[3]
                    if tree_data.set_size:
                        # print('set size at:', tokens[token_index][0])
                        data[2] = int_value
                        if data[2] < 1:
                            tokens[token_index].error(f"Declaration error; cannot have zero size")
                    elif tree_data.arg:
                        if len(scope[data[0]].args) <= data[1]:
                            tokens[token_index].error(f"Argument error; in '{scope[data[0]].tk.value}' call, "\
                                                      f"argument '{scope_var_name}' not expected")
                            
                        if not int_size(int_value, scope[data[0]].args[data[1]], is_str):
                            tokens[token_index].error(f"Type warning; in '{scope[data[0]].tk.value}' call, "\
                                                      f"'{tokens[token_index].value}' {ovf_msg}", not is_str)
                        data[1] += 1
                    elif tree_data.assert_type and expected_size == 0:
                        tokens[token_index].error(f"Type error; incorrect argument type of '{str(int_value)}',\n"\
                                                  f"Expected {byte_s(data[3])}, instead got INTEGER LITERAL")
                    elif tree_data.assert_type and not int_size(int_value, expected_size, is_str):
                        tokens[token_index].error(f"Type warning; "\
                                                  f"'{tokens[token_index].value}' {ovf_msg}", not is_str)
                token_index += 1
                max_index = max(max_index, token_index)
                return True
            else:
                return False
            
        return_index = token_index
        # print('grammar', grammar, '| root token:', tokens[root_index][0])
        for variation in grammar:
            valid = True
            tree_data = TreeData()
            if not isinstance(variation, tuple): variation = (variation,)

            #Ensure to skip if left-most token is same grammar
            # if is_recursive(variation, grammar, root_index): continue

            # print('variation:', variation, '| looked at token:', tokens[token_index][0])
            token_index = return_index
            syntax_tree.clear()
            ini_str_lits = str_lits
            for token in variation:
                # print(tokens[token_index][0], token)
                temp_tree = []

                # if token in GRAMMAR and GRAMMAR[token] == grammar:
                #     next_root_index = i
                # else:
                #     next_root_index = -1

                if token == NEW_SCOPE:
                    scope = dict(scope)
                    if scope[NEW_SCOPE] == '':
                        scope[NEW_SCOPE] = 'global'
                    elif tree_data.decl and tree_data.call:
                        scope[NEW_SCOPE] = data[0]
                        # fct_scopes.append(scope)
                    else:
                        scope[NEW_SCOPE] = 'local' + str(enum())
                    syntax_tree.append((scope, NEW_SCOPE))
                elif token == DECL:
                    tree_data.decl = True
                elif token == CALL:
                    tree_data.call = True
                elif token == ARG:
                    if not tree_data.decl:
                        if len(scope[data[0]].args) == 0:
                            valid = False
                            str_lits = ini_str_lits
                            break
                        data[2] = scope[data[0]].args[data[1]]
                    tree_data.arg = True
                elif token == END_OF_ARGS:
                    if len(scope[data[0]].args) != data[1]:
                        tokens[token_index].error(f"Argument error; in '{scope[data[0]].tk.value}' call, "\
                                                  f"too few arguments")
                elif token == SET_SIZE:
                    data[2] = 1
                    tree_data.set_size = True
                elif token == VOID_FCT:
                    data[2] = 0
                    tree_data.set_size = True
                elif token == BOOL_SIZE:
                    data[3] = -BOOL_SIZE
                elif token == ASSERT_TYPE:
                    tree_data.assert_type = True
                elif token == NEGATIVE:
                    tree_data.neg = True
                elif token == ASSERT_RET:
                    data[3] = last_function_in_scope_size(scope)
                elif token == ASSERT_ARR:
                    tree_data.assert_arr = True
                    tree_data.assert_type = True
                elif token == CHECK_ARR:
                    if data[4] != 1:
                        tokens[token_index].error(f"Type error; incorrect argument type of '{scope[scope_var_name].tk.value}',\n"\
                                                  f"Expected 1 byte, instead got {byte_s(size)}")
                elif type(token) == tuple:
                    while make([token], temp_tree, scope, True, tree_data):
                        syntax_tree.extend(temp_tree)
                        temp_tree = []
                    if len(temp_tree) == count_real_tokens(token) - 1:
                        syntax_tree.extend(temp_tree)
                elif type(token) == str and token == tokens[token_index].type:
                    # syntax_tree.append(tokens[token_index])
                    token_index += 1
                    max_index = max(max_index, token_index)
                elif type(token) == int and \
                    make(GRAMMAR[token], temp_tree, scope, compound, tree_data):
                    tree_data.set_size = False
                    if len(temp_tree) == 1 and token == tk_type(temp_tree[0]):
                        syntax_tree.append(temp_tree[0])
                    elif token != ARG_DECL:
                        syntax_tree.append((temp_tree, token))
                else:
                    valid = False
                    if not compound: str_lits = ini_str_lits
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
                else:
                    print(' ' * indent + '  ' + str(scope[var]))

        else:
            try:
                print(' ' * indent + namestr(tk_type(branch), globals()) + ': ' + str(branch[0]))
            except KeyError:
                print(' ' * indent + f"/!\\ Undefined behavior: " + str(branch[0]))

def no_output(_type):
    return _type in (STATEMENT, EXPR, BOOL, PROG_BODY, PROGRAM, END_OF_FILE, NEW_SCOPE)

def get_var_name(id: str, scope: dict):
    for key in reversed(scope):
        if key == NEW_SCOPE: continue

        if key.endswith(id):
            return key
    
    return 0
    # raise LookupError(f"'{id}' not found within scope {list(scope)}")

def get_bin(int_str: str, size: int) -> list[str]:
    assert size >= 0
    lit = int(int_str) & (256**size - 1)
    bin_list = []
    if size == 0:
        bin_list.append('%' + bin(lit & 255)[2:].rjust(8, '0'))
        lit >>= 8
        while lit != 0:
            bin_list.append('%' + bin(lit & 255)[2:].rjust(8, '0'))
            lit >>= 8
    else:
        for _ in range(size):
            bin_list.append('%' + bin(lit & 255)[2:].rjust(8, '0'))
            lit >>= 8
    return bin_list

def get_chunks(var, size, op, backup:str=None, special:str=None, start=0):
    assert type(var) in (tuple, list)
    if type(var) == tuple:
        var_name, var_size = var
        if var_name == 'builtin_keybin':
            var = ['keyb']
        else:
            var = [f"{var_name}{i}" for i in range(start, var_size+start)]
            
    else:
        var_size = len(var)
    if backup == None: backup = f'{op}%' if op[-1] != '%' else op
    if size == 0: size = var_size

    if special == None:
        chunks = [[[f'    {op} ', f"{var[i]}"]] for i in range(var_size)]
        if var_size < size:
            for _ in range(var_size, size):
                chunks.append([[f'    {backup} ', '%00000000']])
        elif size < var_size:
            chunks = chunks[:size]

    else:
        chunks = [[[f'    {special} '], [f'    {op} ', f"{var[i]}"]] for i in range(var_size)]
        if var_size < size:
            for _ in range(var_size, size):
                chunks.append([[f'    {special} '], [f'    {backup} ', '%00000000']])
        elif size < var_size:
            chunks = chunks[:size]
        chunks[0] = chunks[0][1:]

    return chunks

def get_expr(expr: list, scope: dict[str,int|Obj], size: int):
    expr_type = tk_type(expr[0])

    if expr_type in (LITERAL, ARG_LIT):
        literal = dig(expr)
        chunks = get_bin(literal, size)
        return [[['    ldi ', chunk]] for chunk in chunks]
    
    elif expr_type == IDENTIFIER:
        var_name = get_var_name(tk_name(expr[0]), scope)
        var_size = scope[var_name].size
        return get_chunks((var_name, var_size), size, 'lda', backup='ldi')
    
    elif expr_type == LONE_EX:
        if len(expr) == 1:
            return get_expr(tk_name(expr[0]), scope, size)
        
        a = tk_name(expr[0])[0]
        b = tk_name(tk_name(expr[1])[0])[0]
        op = tk_type(expr[1])
        if tk_type(b) == LITERAL:
            literal = tk_name(b[0])[0]
            b_value = get_bin(literal, size)
        else:
            b_name = get_var_name(tk_name(b), scope)
            b_size = scope[b_name].size
        a = get_expr([a], scope, size)

        if op == ADD_EX:
            if tk_type(b) == LITERAL:
                op = get_chunks(b_value, size, 'add#', special='addc')
            else:
                op = get_chunks((b_name, b_size), size, 'add', special='addc')
        elif op == SUB_EX:
            if tk_type(b) == LITERAL:
                op = get_chunks(b_value, size, 'sub#', special='subc')
            else:
                op = get_chunks((b_name, b_size), size, 'sub', special='subc')
        elif op == MULT_EX:
            if tk_type(b) == LITERAL:
                op = '    multl# '  
            else:
                raise NotImplementedError
                # op = get_chunks_var((b_name, b_size), size, 'multl', special='multh')
                # for i in range(1, len(a)):
                #     a_chunk = a[i]
                #     op_chunk = op[i]
                #     a_chunk[0][0] = a_chunk[0][0].replace('lda', 'add')
                #     a_chunk[0][0] = a_chunk[0][0].replace('ldi', 'add#')
                #     op_chunk[0].append(a[i-1][-1][-1])
                # chunks = [([y[0]] + x + y[1:]) for x, y in zip(a, op)]
                # chunks[0].reverse()
                # return chunks
        elif op == CMP_EX:
            a = reversed(a)
            if tk_type(b) == LITERAL:
                op = reversed(get_chunks(b_value, size, 'cmp#'))
            else:
                op = reversed(get_chunks((b_name, b_size), size, 'cmp'))
        elif op == AND_EX:
            if tk_type(b) == LITERAL:
                op = get_chunks(b_value, size, 'and#')
            else:
                op = get_chunks((b_name, b_value), size, 'and')
        else:
            raise NotImplementedError(f"{namestr(tk_type(expr[0]), globals())} not implemented")

        return [(x + y) for x, y in zip(a, op)]
    
    elif expr_type in (EXPR, CAST_EX):
        return get_expr(tk_name(expr[0]), scope, size)
    
    elif expr_type == ARRAY_GET:
        name = get_var_name(expr[0][0][0][0], scope) + '0'
        index = expr[0][0][1][0]
        if index.isnumeric():
            index = int(index)
            indices = [get_bin(str(index+i), 1)[0] for i in range(size)]
            return [[
                ['    lda ', name],
                ['    add# ', index],
                ['    jsr ', 'builtin_getheap']
            ] for index in indices]
        else:
            index = get_var_name(index, scope) + '0'
            offsets = [get_bin(str(i), 1)[0] for i in range(size)]
            return [[
                ['    lda ', name],
                ['    add ', index],
                ['    add# ', offset],
                ['    jsr ', 'builtin_getheap']
            ] for offset in offsets]
        
    elif expr_type in (FCT_CALL, FCT_EX):
        global fct_scopes

        fct_name = inst(1, IDENTIFIER, tk_name(expr[0]))
        fct = scope[get_var_name(fct_name, scope)]
        fct_scope = fct_scopes[fct.id]
        
        args = [i for i in fct_scope.values() if (type(i) == Obj and i.id.startswith(fct.id))][1:len(fct.args)+1]
        arg_exprs = [inst(1+i, ARG_EX, tk_name(expr[0])) for i in range(len(args))]
        
        lines_for_calling = []
        if len(args) == 1 and args[0].size == 1:
            load = get_expr(arg_exprs[0], scope, 1)
            expr_extend(lines_for_calling, load, use_sta=False)
        else:
            for expr, arg in zip(arg_exprs, args):
                load = get_expr(expr, scope, arg.size)
                expr_extend(lines_for_calling, load, arg.id, True)
        lines_for_calling.append(['    jsr ', fct.id])

        if fct.size == 1: return [lines_for_calling]
        chunks = get_expr([(fct_name, IDENTIFIER)], scope, size)
        for chunk in chunks:
            chunk[0][1] = chunk[0][1].replace(fct.id, 'temp')
        chunks[0] = lines_for_calling + chunks[0]
        return chunks

    else:
        raise NotImplementedError(f"{namestr(tk_type(expr[0]), globals())} not implemented")

def get_expr_size(expr: tuple, scope: dict[str,int|Obj]) -> int:
    assert type(expr) == tuple, expr
    typ = tk_type(expr)
    if typ == IDENTIFIER:
        return scope[get_var_name(tk_name(expr), scope)].size
    elif typ == LITERAL:
        return -len(get_bin(dig([expr]), 0))
    elif typ == ARRAY_GET:
        return 0
    else:
        sizes = [get_expr_size(e, scope) for e in tk_name(expr)]
        m = max(sizes)
        if m > 0:
            return m
        elif m == 0:
            return 1
        else:
            return min(sizes)

def get_jump(type: int, scope_str: str) -> list[list[str]] | None:
    if type == BOOL_EQ:  return [['    jpne ', '&' + scope_str]]
    if type == BOOL_NEQ: return [['    jpeq ', '&' + scope_str]]
    if type == BOOL_LTE: return [['    jpgt ', '&' + scope_str]]
    if type == BOOL_GTE: return [['    jplt ', '&' + scope_str]]
    if type == BOOL_LT:  return [['    jpgt ', '&' + scope_str],
                                 ['    jpeq ', '&' + scope_str]]
    if type == BOOL_GT:  return [['    jplt ', '&' + scope_str],
                                 ['    jpeq ', '&' + scope_str]]
    else: return None

def get_bool(expr: list, scope: dict, scope_str: str):
    expr_type = tk_type(expr[0])
    jump_op = get_jump(expr_type, scope_str)
    if jump_op != None:
        expr1 = tk_name(expr[0])[0]
        expr2 = tk_name(expr[0])[1]

        if tk_type(expr1) == tk_type(expr2) == LONE_EX:
            dig1 = dig([expr1])
            dig2 = dig([expr2])
            if type(dig1) == str:
                size = scope[get_var_name(dig1, scope)].size
            elif type(dig2) == str:
                size = scope[get_var_name(dig2, scope)].size
            else:
                size = 0
            chunks = get_expr([expr1, ([expr2], CMP_EX)], scope, size)
            bool_chunks = []
            for chunk in chunks:
                bool_chunks.extend(chunk + jump_op)
            return bool_chunks
        elif tk_type(expr1[0][-1]) == LONE_EX or tk_type(expr2[0][-1]) == LONE_EX:
            if tk_type(expr1[0][-1]) == LONE_EX:
                expr1, expr2 = expr2, expr1 #make expr2 the lone expr
            expr1 = dig([expr1])
            expr2 = dig([expr2])
            if tk_type(expr2[0]) == IDENTIFIER:
                size = scope[get_var_name(tk_name(expr2[0]), scope)].size
            cmp = get_expr(expr2, scope, size)
            cmp[0][0][0] = cmp[0][0][0].replace('ldi', 'cmp#')
            cmp[0][0][0] = cmp[0][0][0].replace('lda', 'cmp')
            # print(cmp)
            other_expr = get_expr(tk_name(expr1), scope, size)
            # print(other_expr)
            bool_chunks = []
            for a, b in zip(other_expr, cmp):
                bool_chunks.extend(a + b + jump_op)
            return bool_chunks
        else:
            size1 = get_expr_size(expr1, scope)
            size2 = get_expr_size(expr2, scope)
            m = max(size1, size2)
            if m > 0:
                size = m
            elif m == 0:
                size = 1
            else:
                size = -min(size1, size2)
            expr1 = get_expr([expr1], scope, size)
            expr2 = get_expr([expr2], scope, size)
            chunks_temp1 = get_chunks(('temp', size), size, 'sta')
            start = len(chunks_temp1)
            chunks_temp2 = get_chunks(('temp', size), size, 'sta', start=start)
            chunks = []
            for x, y in zip(expr1, chunks_temp1):
                chunks.extend(x+y)
            for x, y in zip(expr2, chunks_temp2):
                chunks.extend(x+y)
            for i in range(start):
                chunks.extend([
                    ['    lda ', f'temp{i+start}'],
                    ['    cmp ', f'temp{i}'],
                    *jump_op
                ])
            return chunks
        
    elif expr_type == BOOL_TRUE:
        return []
    
    elif expr_type == BOOL_FALSE:
        return [['    jump ', '&' + scope_str]]

    else:
        raise NotImplementedError(f"{namestr(tk_type(expr[0]), globals())} not implemented")

def inst(n, typ, syntax_tree):
    assert n > 0
    count = 0
    for branch in syntax_tree:
        if tk_type(branch) == typ: count += 1
        if count == n: return tk_name(branch)
    assert False, f"Unreachable instance {namestr(typ, globals())} in tree {syntax_tree}"

def dig(surface, typ=None):
    under = tk_name(surface[0])[0]
    assert type(under) == tuple, under
    if typ == None: return tk_name(under)
    if tk_type(under) != typ: return None
    return tk_name(under)

def expr_extend(lines:list, chunks:list, var_name:str='', use_sta=True):
    new_lines = []
    for i in range(len(chunks)):
        new_lines.extend(chunks[i])
        if use_sta:
            new_lines.append(['    sta ', var_name+str(i)])
    lines.extend(new_lines)

def generate_code(syntax_tree: list, _type: int, scope: dict[str,int|Obj], lines: list[list[str]]):
    if lines == []:
        lines.append(['/ SBB COMPILER OUTPUT sbb.py'])
        if str_lits != '':
            str_repr = repr(str_lits.replace('"', '\\"'))[1:-1]
            str_repr = str_repr.replace("\\'", "'")
            str_repr = str_repr.replace('\\\\"', '\\"')
            lines.append([f'$-heap __strlits__ = "{str_repr}"'])
        lines.extend(BUILTIN_BLOCKS)

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
        
        scope = inst(1, NEW_SCOPE, syntax_tree)                 # define the scope of the function
        fct_name = scope[NEW_SCOPE]
        global fct_scopes
        fct_scopes[fct_name] = scope
        lines.append(['\n' + fct_name + ':'])                   # write -> function:
        args = scope[fct_name].args
        if len(args) == 1 and args[0] == 1:
            arg = [i for i in scope.values() if (type(i) == Obj and i.id.startswith(fct_name))][1:2][0]
            lines.append(['    sta ', f'{arg.id}0'])
        fct_statement = inst(1, STATEMENT, syntax_tree)         # find the function statement
        generate_code(fct_statement, STATEMENT, scope, lines)   # generate the statement within

        if not ''.join(lines[-1]).strip().startswith('ret'):
            lines.append(['    ret'])                           # in case function doesn't return
    
    elif _type == RETURN_ST:
        if len(syntax_tree) > 0:
            size = last_function_in_scope_size(scope)
            expr = inst(1, EXPR, syntax_tree)
            chunks = get_expr(expr, scope, size)
            expr_extend(lines, chunks, 'temp', size > 1)
        lines.append(['    ret'])
    
    elif _type == VAR_EQ:
        var_id = inst(1, IDENTIFIER, syntax_tree)
        var_name = get_var_name(var_id, scope)
        size = scope[var_name].size
        expr = inst(1, EXPR, syntax_tree)
        chunks = get_expr(expr, scope, size)
        expr_extend(lines, chunks, var_name)
    
    elif _type == IF_ST:
        assert len(syntax_tree) in (2,3), f"Unexpected behavior for {namestr(_type, globals())}"
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
        assert len(syntax_tree) in (2,3), f"Unexpected behavior for {namestr(_type, globals())}"
        name = get_var_name(inst(1, IDENTIFIER, syntax_tree), scope)
        size = scope[name].size
        literal = inst(1, LITERAL, syntax_tree)[0][0]
        value = get_bin(literal, size)
        for i in range(size):
            lines.insert(1, [f"{name}{i}", ' = ', value[i], '/NOTAB'])

    elif _type == VAR_DECL:
        return
    
    elif _type == FCT_CALL:
        fct_name = inst(1, IDENTIFIER, syntax_tree)
        fct = scope[get_var_name(fct_name, scope)]
        fct_scope = fct_scopes[fct.id]
        
        args = [i for i in fct_scope.values() if (type(i) == Obj and i.id.startswith(fct.id))][1:len(fct.args)+1]
        arg_exprs = [inst(1+i, ARG_EX, syntax_tree) for i in range(len(args))]

        if len(args) == 1 and args[0].size == 1:
            load = get_expr(arg_exprs[0], scope, 1)
            expr_extend(lines, load, use_sta=False)
        else:
            for expr, arg in zip(arg_exprs, args):
                load = get_expr(expr, scope, arg.size)
                expr_extend(lines, load, arg.id, True)
        lines.append(['    jsr ', fct.id])

    else:
        raise NotImplementedError(f"{namestr(_type, globals())} not implemented")

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
    return -1 if OPTIONS['passive'] else run_program(temp_lines, *special_mode)

def skipable(line, excep: None|list[str]):
    join_line = ''.join(line)
    if '*' in join_line or ':' in join_line:
        return False
    stripped_line = line[0].strip()
    if excep == None and stripped_line != '':
        return stripped_line[0] == '/' or stripped_line == 'noop'
    else:
        return not stripped_line in excep

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
                        found_jump = False
                        for line in lines[i+1:j+1]:
                            if is_jump(line):
                                found_jump = True
                                break
                        if found_jump:
                            lines[j] = ['/REMOVED']
                        else:
                            lines[i+1:j+1] = [['/REMOVED']] * (j-i)

                elif not skipable(lines[j], excep):
                    break

def depend_remove(lines, dep: str, ind: list[str]):
    len_line = 4 if dep == None else 2
    for i in range(len(lines)):
        if len(lines[i]) != len_line: continue
        if (dep == None and lines[i][0].startswith('global_')) or lines[i][0].strip() == dep:
            operand = lines[i][0 if dep == None else 1].strip()
            if operand.startswith('&'): continue
            found = False
            for line in lines:
                if line[0].strip() in ind and line[1].strip() == operand:
                    found = True
            if not found:
                lines[i] = ['/REMOVED']

JUMP_INS = ('jpne', 'jpeq', 'jplt', 'jpgt', 'jmpz', 'jmpz', 'jmpn', 'jsr')
def is_jump(line: list[str], cond=False):
    if line == []: return False
    op = line[0].strip()
    return (not cond and op == 'jump') or op in JUMP_INS

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
    used_labels = set()
    for line in lines:
        if is_jump(line):
            if line[1].strip()[0] == '&':
                used_labels.add(line[1].strip('&'))
    
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

def remove_useless_fcts(lines: list[list[str]]):
    #search for used functions
    used_fcts = {'start'}
    for line in lines:
        if line[0] == '    jsr ':
            used_fcts.add(line[1])
    
    #delete unused functions
    remove_this = False
    for i in range(len(lines)):
        line_first_word = lines[i][0].strip()
        if line_first_word[-1] == ':':
            remove_this = False
            if line_first_word[:-1] not in used_fcts:
                lines[i] = ['/REMOVED']
                remove_this = True
        elif remove_this:
            lines[i] = ['/REMOVED']

LOAD_INS = ['lda', 'add', 'sub', 'multl', 'multh', 'and', 'or', 'cmp']
def optimize(lines: list[list[str]], lvl = 0) -> str:
    remove_useless_fcts(lines)
    size_i = get_program_size(lines)
    if lvl == 0:
        print(f'[SBB-lang Compiler] Compilation result (unoptimized): {byte_s(size_i)}')
        return join_lines(lines)
    
    prev_change = 0
    depth = 0
    while True:
        depth += 1
        # LEVEL 1 OPTIMISATIONS:
        # (delete 1 line at a time)
        binary_remove(lines, ('sta', 'lda'), del_first=False, excep=LOAD_INS+['sta'])
        binary_remove(lines, ('lda', 'sta'), del_first=False)
        binary_remove(lines, ('sta', 'sta'), excep=LOAD_INS)
        depend_remove(lines, 'sta', LOAD_INS+list(JUMP_INS))
        depend_remove(lines, None, LOAD_INS+list(JUMP_INS))
        binary_remove(lines, ('ldi', 'ldi'))
        binary_remove(lines, ('lda', 'lda'))
        binary_remove(lines, ('ldi', 'ldi'), del_first=False, excep=LOAD_INS+['sta'])
        binary_remove(lines, ('lda', 'lda'), del_first=False, excep=LOAD_INS+['sta'])
        binary_remove(lines, ('ldi', 'lda'), catch=False)
        binary_remove(lines, ('lda', 'ldi'), catch=False)
        remove_useless_fcts(lines)

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
            replace_pattern(lines, ['add#', '%00000001'], ['    inc'])
            replace_pattern(lines, ['sub#', '%00000001'], ['    dec'])
            replace_pattern(lines, ['add#', '%11111111'], ['    dec'])
            replace_pattern(lines, ['sub#', '%11111111'], ['    inc'])
            replace_pattern(lines, ['add#', '%00000000'], ['/REMOVED'])
            replace_pattern(lines, ['sub#', '%00000000'], ['/REMOVED'])
            replace_pattern(lines, ['multl#', '%00000010'], ['    lsh'])
            modify_linked_jumps(lines)
            # sta x    sta x
            # lda y -> add y
            # add x

        # TODO: LEVEL 3 OPTIMISATIONS:
        # (change the order of things to delete unnecessary lines)
        if lvl < 0 or lvl > MAX_LVL:
            raise NotImplementedError(f"Optimisation level {lvl} is not supported")
        
        changes = count_changes(lines)
        if prev_change == changes or depth > 99:
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
        print(f'{byte_s(size_i)}')
    elif size_dif == -1:
        print(f'{size_i} -> {byte_s(size_f)}')
    else:
        print(f'{size_i} -> {byte_s(size_f)} ({size_dif*100-100:.0f}% improv.)')
    return join_lines(lines)

def print_help(do_exit):
    print('To run write: python sbb.py <SOURCE.sbb> <OPTIONAL:WRITE.sbbasm>')
    print('-wdis    -> disable all warnings')
    print('-pkw     -> print language keywords')
    print('-pt      -> print tokens')
    print('-ppc     -> print parsed code')
    print('-psb     -> print string buffer')
    print('-time    -> time each compilation step')
    print('-dump    -> dump generated contents before writing to a file')
    print('-nout    -> no output code')
    print('-pas     -> avoid using the assembler on optimization step')
    print('-rt      -> real time compile')
    print(f'-Ox      -> optimization level (x={','.join(str(i) for i in range(MAX_LVL+1))})')
    print('-run     -> launch the computer and run, .sbbasm file generated')
    print('-runv    -> launch the computer and run, .sbbasm file generated, visuals enabled')
    print('-d       -> turn on all debug options, including assembler debug options if \'-run\' is selected')
    print('-dr      -> turn on assembler debug options and runs the code')
    if do_exit: exit()

def load_args():
    global pre_compile_terminate

    if not len(argv) >= 2 or argv[1].lower() == '-help': print_help(do_exit=True)
    assert_error(path.isfile(argv[1]), 
    f"[INVALID SOURCE FILE PATH]:\n    source file path '{argv[1]}' does not exist\n")
    assert_error(argv[1].endswith('.sbb'), 
    f"[INVALID SOURCE FILE PATH]:\n    source file path '{argv[1]}' must end with '.sbb'\n")
    
    defined_file_creation = len(argv) > 2 and argv[2].endswith('.sbbasm')
    if defined_file_creation:
        assert_error(len(argv[2].split('/')) > 1 and argv[2].split('/')[-2] == 'sbbasm_program_files',
        f"[INVALID OUTPUT FILE PATH]:\n    output file path '{argv[2]}' must be contained within 'sbbasm_program_files' folder\n")
    else:
        filename = './sbbasm_program_files/' + argv[1].split('/')[-1] + 'asm'

    global LVL, RT_COMPILE, OPTIONS
    OPTIONS = {'tokens': False, 'parsedcode': False, 'keywords': False, 'time': False,
               'nout': False, 'stringbuffer': False, 'nowarnings': False, 'dump': False,
               'run': False, 'debugassembler': False, 'passive': False, 'visuals': False}
    
    for option in (argv[3:] if defined_file_creation else argv[2:]):
        option = option.lower()
        if option.startswith('-o') and len(option) > 2 and option[2:].isnumeric():
            global LVL
            LVL = int(option[2:])
            assert_error(LVL <= MAX_LVL, f"[INVALID OPTION]:\n    option {option} is not defined\n")
        elif option == '-rt':
            RT_COMPILE = True
        elif option == '-ppc':
            OPTIONS['parsedcode'] = True
        elif option == '-pt':
            OPTIONS['tokens'] = True
        elif option == '-pkw':
            OPTIONS['keywords'] = True
        elif option == '-time':
            OPTIONS['time'] = True
        elif option == '-nout':
            OPTIONS['nout'] = True
        elif option == '-psb':
            OPTIONS['stringbuffer'] = True
        elif option == '-wdis':
            OPTIONS['nowarnings'] = True
        elif option == '-dump':
            OPTIONS['dump'] = True
        elif option == '-run':
            OPTIONS['run'] = True
        elif option == '-runv':
            OPTIONS['run'] = True
            OPTIONS['visuals'] = True
        elif option == '-d':
            OPTIONS['parsedcode'] = True
            OPTIONS['tokens'] = True
            OPTIONS['keywords'] = True
            OPTIONS['stringbuffer'] = True
            OPTIONS['debugassembler'] = True
        elif option == '-dr':
            OPTIONS['run'] = True
            OPTIONS['debugassembler'] = True
        elif option == '-pas':
            OPTIONS['passive'] = True
        elif option == '-help':
            print_help(do_exit=False)
        else:
            assert_error(False, f"[INVALID OPTION]:\n    option {option} is not defined\n")

    assert_error(not (OPTIONS['run'] and RT_COMPILE), '[INVALID COMBINATION]:\n    -run or -runv cannot be used with -rt')
    assert_error(True, kill=True)
    return argv[1], argv[2] if defined_file_creation else filename

def main(sourcepath, writepath):
    enum(reset=True)
    if OPTIONS['keywords']:
        print('\n~~~~ KEYWORDS ~~~~')
        print(KEYWORDS)

    with open(sourcepath) as program:
        program = program.read()
        start = perf_counter()
        times = []

        tokens = lexer(program, sourcepath)
        if OPTIONS['tokens']:
            print('\n~~~~ TOKENS ~~~~')
            for token in tokens: print(token)
        times.append(perf_counter())

        syntax_tree = parser(tokens)
        if OPTIONS['parsedcode']:
            print('\n~~~~ SYNTAX TREE ~~~~')
            print_parsed_code(syntax_tree)
        if OPTIONS['stringbuffer']:
            print('\n~~~~ STRING BUFFER ~~~~')
            print(f'"{str_lits}"')
        times.append(perf_counter())

        if not OPTIONS['nout'] or OPTIONS['dump']:
            lines = generate_code(syntax_tree, PROGRAM, syntax_tree[0][0], [])
            if OPTIONS['dump']:
                print('\n~~~~ CONTENT DUMP ~~~~')
                print(join_lines(deepcopy(lines)))
            times.append(perf_counter())

        if not OPTIONS['nout']:
            lines = optimize(lines, lvl=LVL)
            times.append(perf_counter())

        if OPTIONS['time']:
            print('\n~~~~ TIME ~~~~')
            print(f'[time] Lexed in {(times[0]-start)*1000:.2f}ms')
            print(f'[time] Parsed in {(times[1]-times[0])*1000:.2f}ms')
            if len(times) > 2:
                print(f'[time] Generated in {(times[2]-times[1])*1000:.2f}ms')
            if len(times) > 3:
                print(f'[time] Optimized in {(times[3]-times[2])*1000:.2f}ms')
        print(f'[SBB-lang Compiler] Compiled succesfully ({(times[-1]-start)*1000:.2f}ms)')

    if not OPTIONS['nout']:
        with open(writepath, 'w') as asm_file:
            asm_file.write(lines)
    
    if OPTIONS['run'] or OPTIONS['debugassembler']:
        special_mode = [False] * 8
        if OPTIONS['debugassembler']:
            special_mode[0] = True
            special_mode[1] = True
            special_mode[4] = True
        special_mode[6] = OPTIONS['visuals']
        lines = [line+'\n' for line in lines.split('\n')]
        run_program(lines, *special_mode)

if __name__ == '__main__':
    sourcepath, writepath = load_args()
    while RT_COMPILE:
        sleep(1)
        system('cls')
        try:
            main(sourcepath, writepath)
        except SyntaxWarning: pass
    main(sourcepath, writepath)