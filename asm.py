#https://eater.net/8bit/pc
from cpu import *
from time import perf_counter, sleep
from pathlib import Path
from random import randint
__version__ = "1.2.2"
__last_update__ = "Nov. 21st 2024"

#Assemble the program
OPS = {
    #ops with address arguments
    "lda"   : 0x00, "add"   : 0x10, "sub"   : 0x20, "sta"   : 0x30,
    "jsr"   : 0x40, "jump"  : 0x50, "jmpc"  : 0x60, "jmpz"  : 0x70,
    "jmpn"  : 0x80, "and"   : 0x90, "or"    : 0xa0, "ldax"  : 0xb0,
    "multl" : 0xc0, "multh" : 0xd0,#(1)     : 0xe+, (2)     : 0xf+
    #ops with numerical arguments (1)
    "ldi"   : 0xe0, "add#"  : 0xe1, "sub#"  : 0xe2, "and#"  : 0xe3,
    "or#"   : 0xe4, "ldib"  : 0xe5, "multl#": 0xe6, "multh#": 0xe7,
    "push#" : 0xe8, "xor#"  : 0xe9, "ret#"  : 0xea, "scp"   : 0xeb,
    "TBA"   : 0xec, "TBA"   : 0xed, "TBA"   : 0xee, "halt#" : 0xef,
    #ops w/o arguments (monos)    (2)
    "noop"  : 0xf0, "out"   : 0xf1, "inc"   : 0xf2, "dec"   : 0xf3,
    "rsh"   : 0xf4, "lsh"   : 0xf5, "take"  : 0xf6, "pusha" : 0xf7,
    "popa"  : 0xf8, "move"  : 0xf9, "ret"   : 0xfa, "hlta"  : 0xfb,
    "not"   : 0xfc,"refresh": 0xfd, "incb"  : 0xfe, "halt"  : 0xff
}

#Token is a named entity (variable or function), not an operation
class Token:
    def __init__(self, name, addr):
        self.name = name
        self.addr = 0 if name == "start" else addr
        self.content = [] #data or ops as numbers
        self.contentstr = [] #data or ops as strings (for printing)
    def __str__(self):
        string = f"<{self.name}> at {self.addr} contains ["
        for i in range(min(len(self.contentstr), 5)):
            string += self.contentstr[i] + ", "
        if len(self.contentstr) == 6:
            return string + self.contentstr[5] + ']'
        elif len(self.contentstr) > 6:
            return string + "...]"
        else:
            return string[:-2] + ']'

def number(arg: str) -> int | None:
    """
    '15'   -> 15 (decimal),
    '$10'  -> 16 (hex),
    '%101' -> 5 (bin),
    '"Hi"' -> 26952 (1 ascii character per byte),
    else   -> None
    """
    if arg.isdecimal() or (arg[0] == '-' and arg[1:].isdecimal()): #decimal
        return int(arg)
    elif arg[0] == '$': #hexadecimal
        return int(arg[1:], 16)
    elif arg[0] == '%': #binary
        return int(arg[1:], 2)
    elif arg[0] == '"' and arg[-1] == '"' and not arg.endswith('\\"'):
        num = 0
        string = arg[1:-1].encode("utf-8").decode("unicode_escape")
        for i, char in enumerate(string):
            num |= ord(char) << (i << 3)
        return num
    else:
        return None
    
def num2byte(num: int) -> list[int]:
    if num < 255:
        return [num & 255]
    bytes = []
    while num > 255:
        bytes.append(num & 255)
        num >>= 8
    bytes.append(num)
    return bytes

def split(string: str) -> list[str]:
    string = string.replace('\\"', '\\\\"').encode("utf-8").decode("unicode_escape")
    output = [""]
    string_form = False
    for char in string:
        if char in ' \t\n\r' and not string_form:
            if output[-1] != "":
                output.append("")
        elif char == '"' and not output[-1].endswith('\\'):
            output[-1] += char
            string_form = not string_form
        else:
            output[-1] += char
    return output[:-1] if output[-1] == "" else output

def read_program(name: str, create_object_file=False):
    cwd = str(Path.cwd())
    try:
        if name == "":
            path = cwd + "\\sbbasm_program_files\\test.sbbasm"
        elif name.endswith(".sbbasm"):
            if not name.__contains__(cwd):
                path = cwd + "\\sbbasm_program_files\\" + name
        else:
            path = cwd + "\\sbbasm_program_files\\" + name + ".sbbasm"
    except FileNotFoundError:
        if name == "":
            path = cwd + "\\test.sbbasm"
        elif name.endswith(".sbbasm"):
            if not name.__contains__(cwd):
                path = cwd + "\\" + name
        else:
            path = cwd + "\\" + name + ".sbbasm"
    program = open(path, 'r')
    lines = program.readlines()
    program.close()

    if create_object_file:
        path = path[:-len(".sbbasm")] + "-object.sbbasm"
        with open(path, 'w') as object:
            start = perf_counter()
            lines = preprocess(lines)
            print(f"Compiled successfully ({round((perf_counter() - start)*1000,2)}ms)")
            for i in range(len(lines)):
                lines[i] = lines[i].strip() + '\n'
            object.writelines(lines)
            print("Object file created at", path)
        exit()

    return lines

def tokenize_line(line: str) -> list[str]:
    line = ' '.join(split(line))
    new_line = ''
    for char in line:
        if char.isalnum() or char in "_#&*\"":
            new_line += char
        else:
            new_line += ' ' + char + ' '
    return new_line.split()

def preprocess(lines: list[str], print_types=False) -> list[str]:
    #imports
    while True:
        import_index = next((i for i, s in enumerate(lines) if s.startswith("@import")), -1)
        if import_index == -1:
            break
        import_path = lines[import_index].split()
        assert len(import_path) == 2, f"[Line {import_index+1}] Expected an import after @import"
        imported = read_program(import_path[1])
        start = next((i for i, s in enumerate(imported) if s.strip().startswith("start:")), -1)
        if start == -1:
            lines = lines[:import_index] + imported + lines[import_index+1:]
        else:
            lines = lines[:import_index] + imported[:start] + lines[import_index+1:]
    
    #macro expressions
    typeof = {} #will store the type of a label
    while True:
        # macro_start = next((i for i, s in enumerate(lines) if s.startswith("@macronew")), -1)
        # macro_end = next((i for i, s in enumerate(lines) if s.startswith("@macroend")), -1)
        macro_start = -1
        macro_end = -1
        for i in range(len(lines)-1, -1, -1):
            if lines[i].startswith("@macroend"):
                macro_end = i
            if lines[i].startswith("@macronew"):
                macro_start = i
                break
        if macro_start == macro_end == -1:
            break
        assert macro_start != -1 and macro_end != -1, f"[Line {max(macro_start,macro_end)+1}] Macro expression improperly declared"
        replace = lines[macro_start+1:macro_end]
        lines = lines[:macro_start] + lines[macro_end+1:]

        #this is the actual macro expression split up into tokens
        #adds the new macro to the list of tokens
        macro = ""
        for i, line in enumerate(replace):
            macro += line.strip()
            if line.strip().endswith(';'):
                replace = replace[i+1:]
                assert macro.startswith('..label.') or not macro.startswith('..'), \
                       "[Preprocess] Expression needs a keyword"
                macro = [i.strip() for i in macro.split('..')]
                temp = []
                for i, item in enumerate(macro):
                    if i%2 == 0:
                        temp += tokenize_line(item)
                    else:
                        temp.append(item)
                macro = temp
                break
            else:
                macro += " "
        
        # if '.' in macro[-2] and len(macro[-2]) > 1:
        #     macro = macro[:-1]
        label_macro = macro[0].startswith('label.')

        #replacing every instance of the macro expression found
        found_instance = True
        last_instance_index = -1
        while found_instance:
            word_index = 0
            line_index = [0,0]
            replace_temp = replace[:]
            codeblock = ''
            build_codeblock = False
            found_instance = False
            if label_macro:
                last_instance_index += 1
            else:
                start_range = len(lines)-1 if last_instance_index == -1 else last_instance_index-1
                last_instance_index = -1
                for i in range(start_range, -1, -1):
                    try:
                        if tokenize_line(lines[i])[0] == macro[0]:
                            last_instance_index = i
                            break
                    except IndexError:
                        continue
            if last_instance_index == -1 or last_instance_index >= len(lines):
                break
            if macro == ['char__expr__', 'expr.a', '-', 'expr.b', ';']:
                print('last instance:', lines[last_instance_index:])

            not_valid = False
            for line_nb in range(last_instance_index, len(lines)):
                if found_instance or not_valid: break
                if lines[line_nb].strip() == '' or lines[line_nb].strip()[0] == '/': continue
                line = tokenize_line(lines[line_nb])
                if word_index == 0:
                    if label_macro or macro[0] == line[0]:
                        line_index[0] = line_nb
                    else:
                        continue

                if macro == ['char__expr__', 'expr.a', '-', 'expr.b', ';']:
                    print(macro, line)
 
                i = word_index
                while i < len(macro):
                    if not_valid:
                        word_index = 0
                        replace_temp = replace[:]
                        break
                    if i-word_index >= len(line):
                        if build_codeblock:
                            codeblock += '\n'
                        else:
                            word_index = i
                        break
                    if i+1 == len(macro) and line[i-word_index] == macro[-1]:
                        if build_codeblock:
                            for rep_line_nb, rep_line in enumerate(replace_temp):
                                if rep_line.find('..'+name_temp+'..') == -1: continue
                                index_start = rep_line.find('..'+name_temp+'..')
                                index_end = index_start + len(name_temp) + 4
                                codeblock = codeblock.strip().split('\n')
                                for j in range(len(codeblock)):
                                    codeblock[j] += '\n'
                                replace_temp = replace_temp[:rep_line_nb]   \
                                    + [rep_line[:index_start]]              \
                                    + codeblock                             \
                                    + [rep_line[index_end:]]                \
                                    + replace_temp[rep_line_nb+1:]
                                codeblock = ''
                        line_index[1] = line_nb
                        found_instance = True
                        word_index = 0
                        break

                    if macro == ['char__expr__', 'expr.a', '-', 'expr.b', ';']:
                        print(macro[i], line[i-word_index], codeblock)

                    #To replace the num type in replacement
                    if macro[i].startswith('num.'):
                        name_temp = macro[i][macro[i].find('.')+1:]
                        num = number(line[i-word_index])
                        if num == None:
                            not_valid = True
                            break
                        num = num2byte(num)

                        for rep_line_nb, rep_line in enumerate(replace_temp):
                            if rep_line.find('..'+name_temp+'.') == -1: continue
                            index_start = rep_line.find('..'+name_temp+'.')
                            index_end = rep_line.find('..', index_start+3+len(name_temp))
                            index = rep_line[index_start+3+len(name_temp): index_end]

                            try:
                                index = int(index)
                                try:
                                    num_str = str(num[index])
                                except IndexError:
                                    num_str = '0'
                                replace_temp[rep_line_nb] = rep_line[:index_start] + num_str + rep_line[index_end+2:]

                            except ValueError:
                                if index == 'len':
                                    num_str = str(len(num))
                                    replace_temp[rep_line_nb] = rep_line[:index_start] + num_str + rep_line[index_end+2:]
                                else:
                                    not_valid = True

                    #To replace the code type in replacement
                    elif macro[i].startswith('code.') or macro[i].startswith('expr.'):
                        assert i+1 != len(macro), "[Preprocess] Expression cannot end in code"
                        end_char = '\n' if macro[i].startswith('code.') else ' '
                        # print('expr:', line, end_char)
                        name_temp = macro[i][macro[i].find('.')+1:]
                        build_codeblock = True
                        if macro[i+1] in line:
                            #TODO: make code blocks work on a single line pls
                            # raise AssertionError("[Preprocess] Code block parcel expected '\\n'")
                            index = line.index(macro[i+1], i-word_index)
                            codeblock += ' '.join(line[i-word_index: index]) + end_char

                            word_index -= index - 1
                            if macro[i-1] in line:
                                word_index += i

                        else:
                            codeblock = ' '.join(line[i-word_index:]) + end_char
                            word_index = i + 1
                            break

                    #To replace labels in replacement
                    elif macro[i].startswith('label.'):
                        name_temp = macro[i][macro[i].find('.')+1:]
                        for rep_line_nb, rep_line in enumerate(replace_temp):
                            index_start = rep_line.find('..'+name_temp+'.')
                            while index_start != -1:
                                index_end = index_start + 3 + len(name_temp)
                                if rep_line[index_end:index_end+6] == 'type..':
                                    index_end += 6
                                    # print(typeof)
                                    # print(line[i-word_index])
                                    try:
                                        label_str = typeof[line[i-word_index]]
                                        # print(label_str)
                                    except KeyError:
                                        not_valid = True
                                        break
                                elif rep_line[index_end] == '.':
                                    index_end += 1
                                    label_str = line[i-word_index]
                                else:
                                    raise AssertionError("[Preprocess] Incorrect use of <label.>")
                                replace_temp[rep_line_nb] = rep_line[:index_start] + label_str + rep_line[index_end:]
                                rep_line = replace_temp[rep_line_nb]
                                index_start = rep_line.find('..'+name_temp+'.')
                            if not_valid: break


                        if not_valid: continue

                        typedef_index = next((i for i, s in enumerate(replace_temp) if s.strip().startswith('@typedef')), -1)
                        while typedef_index != -1:
                            typeof[line[i-word_index]] = replace_temp[typedef_index].split(maxsplit=2)[2].strip()
                            replace_temp.pop(typedef_index)
                            typedef_index = next((i for i, s in enumerate(replace_temp) if s.strip().startswith('@typedef')), -1)
                    
                    #other case check if token is correct
                    elif macro[i] == line[i-word_index] or \
                        (build_codeblock and macro[word_index] == line[i-word_index]):
                        if build_codeblock:
                            for rep_line_nb, rep_line in enumerate(replace_temp):
                                if rep_line.find('..'+name_temp+'..') == -1: continue
                                index_start = rep_line.find('..'+name_temp+'..')
                                index_end = index_start + len(name_temp) + 4
                                codeblock = codeblock.strip().split('\n')
                                for j in range(len(codeblock)):
                                    codeblock[j] += '\n'
                                replace_temp = replace_temp[:rep_line_nb]   \
                                    + [rep_line[:index_start]]              \
                                    + codeblock                             \
                                    + [rep_line[index_end:]]                \
                                    + replace_temp[rep_line_nb+1:]
                                codeblock = ''

                        build_codeblock = False

                    elif build_codeblock:
                        if macro[word_index] in line:
                            raise AssertionError(f"[Preprocess] Syntax error did not expect <{macro[word_index]}>")
                            # i_new = line.index(macro[word_index])
                            # codeblock += ' ' + ' '.join(line[i-word_index:i_new])
                            # i = i_new + word_index
                            # build_codeblock = False
                        else:
                            codeblock += ' '.join(line[i-word_index:]) + end_char
                            print(codeblock)
                            break

                    else:
                        not_valid = True
                    i += 1

            if not_valid:
                found_instance = True
                continue
            if not label_macro:
                line_index[0] = last_instance_index
            # print(line_index)
            if found_instance:
                #add random where ?x?
                random = {}
                for i in range(len(replace_temp)):
                    start = replace_temp[i].find('?')
                    end = replace_temp[i].find('?', start+1) + 1
                    while not (start == end-1 == -1 or end <= start):
                        try:
                            random_num = random[replace_temp[i][start:end]]
                        except KeyError:
                            random[replace_temp[i][start:end]] = str(randint(0, 2**32-1))
                            random_num = random[replace_temp[i][start:end]]
                        replace_temp[i] = replace_temp[i][:start] + random_num + replace_temp[i][end:]
                        start = replace_temp[i].find('?')
                        end = replace_temp[i].find('?', start+1) + 1

                lines = lines[:line_index[0]] + replace_temp[:] + lines[line_index[1]+1:]

    if print_types:
        for label in typeof:
            print(f"[Debugger] Label <{label}> of type <{typeof[label]}>")
    return lines
        
def run_program(lines: list[str], *special_mode):
    start = perf_counter()
    lines = preprocess(lines, print_types=special_mode[0]) #Abandonned dynamic compilling
    # print(f"Compiled successfully ({round((perf_counter() - start)*1000,2)}ms)")
    start = perf_counter()
    # for line in lines: print(line.strip())
    RAM.clear()
    data_section = True
    program_ends = False
    tokenList: list[Token] = []
    refList: list[Token] = [] #list of references for jumps (*here and &here)
    mem_ptr = RAM_SIZE #memory pointer starts at the end and moves back

    #Create line pointers
    line_ptr = [0] * len(lines)
    start_section = False
    section = []
    for l, line in enumerate(lines):
        #remove empty lines or comment lines
        if line.strip() == '' or line.strip()[0] == '/': continue

        #remove end-of-line comments
        comment = line.find('/')
        if comment != -1:
            line = line[:comment].strip()
        
        #create references
        ref = len(line) - line[::-1].find('*') - 1
        if ref != len(line) and line.find('"', ref) == -1:
            valid = len(split(line[ref:])) == 1 and line[ref+1:].strip().isidentifier()
            assert valid, f"[line {l+1}] Invalid reference <{line[ref+1:-1]}>"
            name = split(line)[-1][1:]
            refList.append(Token(name, l+1))
            refList[-1].content.append(mem_ptr)
            refList[-1].contentstr.append(str(mem_ptr))

        #check if line is a new function
        if split(line)[0].endswith(':') or line == "@data\n":
            data_section = line == "@data\n"
            ptr = mem_ptr
            if len(section) != 0:
                for k, offset in enumerate(section):
                    line_ptr[section[0] + k] = ptr
                    if k == 0: continue
                    for ref in refList:
                        if ref.addr-1 == section[0] + k:
                            ref.content[0] = ptr
                            ref.contentstr[0] = str(ptr)
                    ptr += offset
                for ref in refList:
                    if ref.addr-1 == section[0]:
                        ref.content[0] = line_ptr[section[0]]
                        ref.contentstr[0] = str(line_ptr[section[0]])
            section = [l]
            if line == "start:\n":
                if len(refList) != 0:
                    if refList[-1].addr == l:
                        refList[-1].content[0] = 0
                        refList[-1].contentstr[0] = '0'
                mem_ptr = 0
                start_section = True
            
        #data section
        elif data_section:
            args = split(line)
            arg0 = number(args[0])
            if arg0 == None:
                if len(args) < 3:
                    line_ptr[l] = mem_ptr - 1
                    mem_ptr -= 1
                else:
                    size = 0
                    for i in range(2, len(args)):
                        try:
                            size += len(num2byte(number(args[i])))
                        except:
                            size += 1 #error here
                    line_ptr[l] = mem_ptr - size
                    mem_ptr -= size

            #rest of the cases    
            else:
                line_ptr[l] = arg0
            if len(refList) != 0 and refList[-1].addr == l+1:
                refList[-1].content = [line_ptr[l]]
                refList[-1].contentstr = [str(line_ptr[l])]
            

        #start function section
        elif start_section:
            line_ptr[l] = mem_ptr
            mem_ptr += 2 if OPS[split(line)[0]] < 0xf0 else 1

        #other function sections
        else:
            section.append(2 if OPS[split(line)[0]] < 0xf0 else 1)
            mem_ptr -= 2 if OPS[split(line)[0]] < 0xf0 else 1

    if special_mode[0]:
        print("[Debugger] Line pointers: ")
        for l, line in enumerate(lines):
            if l+1 == len(lines):
                print(f"    line {l+1} -> {line_ptr[l]}:\t{line.strip()}")
            else:
                print(f"    line {l+1} -> {line_ptr[l]}:\t{line[:-1].strip()}")
        if len(refList) == 0:
            print()
        else:
            print("[Debugger] Ref list: ")
            for ref in refList:
                print(f"    {ref}")

    #Create program tokens
    data_section = True
    mem_ptr = RAM_SIZE - 1
    for l, line in enumerate(lines):
        #remove empty lines or comment lines
        if line.strip() == '' or line.strip()[0] == '/': continue

        #remove end-of-line comments
        comment = line.find('/')
        if comment != -1:
            line = line[:comment].strip()
        
        #remove line references
        ref = len(line) - line[::-1].find('*') - 1
        if ref != len(line) and line.find('"', ref) == -1:
            line = line[:ref].strip()

        #special keyword that start with @
        if line == "@data\n":
            data_section = True
            continue

        args = split(line)

        #function section begin, creates a function token
        if args[0].endswith(':'):
            assert args[0][:-1].isidentifier(), f"[line {l+1}] Invalid declaration <{args[0]}>"
            data_section = False
            tokenList.insert(0, Token(args[0].strip(':'), mem_ptr + 1))

        #data section
        elif data_section:
            #if an address is given
            arg0 = number(args[0])
            if type(arg0) == int:
                assert len(args) != 1, f"[line {l+1}] Unexpected <{args[0]}>"
                arg1 = number(args[1])

                #data starts with 2 numbers
                if type(arg1) == int:
                    #set data at a nameless address (ex.: $2ea %10010010)
                    if len(args) == 2:
                        for i, byte in enumerate(num2byte(arg1)):
                            RAM.mem[arg0 + i].equal(byte)

                    #set multiple data to a range of addresses (ex.: $100 $200 x = 1500 3200)
                    else:
                        assert args[2].isidentifier(), f"[line {l+1}] Invalid declaration <{args[0]}>"
                        tokenList.insert(0, Token(args[2], arg0))
                        if len(args) > 3:
                            assert args[3] == '=', f"[line {l+1}] Syntax error expected '='"
                            assert len(args) > 4, f"[line {l+1}] Expected data after '='"
                            for i in range(4, len(args)):
                                num = number(args[i])
                                assert type(num) == int, f"[line {l+1}] Invalid initialization <{args[i]}>"
                                num = num2byte(num)
                                for byte in num:
                                    tokenList[0].content.append(byte)
                                    tokenList[0].contentstr.append(str(byte))
                        empty_len = 1 + arg1 - arg0 - len(tokenList[0].content)
                        tokenList[0].content += [0] * (empty_len)
                        tokenList[0].contentstr += ["<Empty>"] * (empty_len)
                
                #set data to named address
                else:
                    assert args[1].isidentifier(), f"[line {l+1}] Invalid declaration <{args[0]}>"
                    tokenList.insert(0, Token(args[1], arg0))
                    if len(args) == 2:
                        tokenList[0].content.append(0)
                        tokenList[0].contentstr.append("<Empty>")
                    else:
                        assert args[2] == '=', f"[line {l+1}] Syntax error expected '='"
                        assert len(args) > 3, f"[line {l+1}] Expected data after '='"
                        for i in range(3, len(args)):
                            num = number(args[i])
                            assert type(num) == int, f"[line {l+1}] Invalid initialization <{args[i]}>"
                            num = num2byte(num)
                            for byte in num:
                                tokenList[0].content.append(byte)
                                tokenList[0].contentstr.append(str(byte))


            #if an addressless-variable is declared
            else:
                assert args[0].isidentifier(), f"[line {l+1}] Invalid declaration <{args[0]}>"
                tokenList.insert(0, Token(args[0], mem_ptr))
                if len(args) == 1:
                    tokenList[0].content.append(0)
                    tokenList[0].contentstr.append("<Empty>")
                    mem_ptr -= 1
                else:
                    tokenList[0].addr += 1
                    assert args[1] == '=', f"[line {l+1}] Syntax error expected '='"
                    assert len(args) > 2, f"[line {l+1}] Expected data after '='"
                    for i in range(2, len(args)):
                        num = number(args[i])
                        assert type(num) == int, f"[line {l+1}] Invalid initialization <{args[i]}>"
                        num = num2byte(num)
                        for byte in num:
                            tokenList[0].content.append(byte)
                            tokenList[0].contentstr.append(str(byte))
                            tokenList[0].addr -= 1
                            mem_ptr -= 1

        #if data section is complete, add ops to function token
        else:
            tokenList[0].content.append(OPS[args[0]])
            OPS_LEN = 2 if OPS[args[0]] < 0b11110000 else 1
            assert OPS_LEN == len(args), f"[line {l+1}] Incorrect use of <{args[0]}>"
            tokenList[0].contentstr.append(' '.join(split(line)))

            #want to know if the program is intended to loop or not
            program_ends |= args[0] in ["halt", "hlta", "halt#"]

            #ops with number arguments
            if 0xf0 > OPS[args[0]] >= 0xe0:
                assert len(args) == 2, f"[line {l+1}] Incorrect use of <{args[0]}>"
                tokenList[0].content.append(number(args[1]) & 255)
                if tokenList[0].name != "start":
                    tokenList[0].addr -= 1
                    mem_ptr -= 1

            #ops with address arguments
            elif 0xe0 > OPS[args[0]]:
                assert len(args) == 2, f"[line {l+1}] Incorrect use of <{args[0]}>"
                #if second word is a number, store it directly as a number
                arg0 = number(args[1])
                if type(arg0) == int:
                    arg0 &= RAM_SIZE-1
                    tokenList[0].content[-1] += arg0 >> 8
                    tokenList[0].content.append(arg0 & 255)

                #line reference (ex.: l123 -> means to find the address at line 123)
                elif args[1][0].lower() == 'l' and args[1][1:].isdecimal():
                    arg0 = line_ptr[int(args[1][1:]) - 1]
                    tokenList[0].content[-1] += arg0 >> 8
                    tokenList[0].content.append(arg0 & 255)

                #line pointer reference (ex.: &&loop finds the address at 1 more than line marked *loop)
                elif args[1][0] == '&':
                    offset = 1
                    while args[1][offset:][0] == '&': offset += 1
                    invalid_ref = True
                    ref_named = args[1][offset:]

                    #if ref is known set value to corresponding line address
                    for ref in refList:
                        if ref.name == ref_named:
                            arg0 = ref.content[0] + offset - 1
                            tokenList[0].content[-1] += arg0 >> 8
                            tokenList[0].content.append(arg0 & 255)
                            invalid_ref = False

                    assert not invalid_ref, f"[line {l+1}] Invalid reference <{ref_named}>"

                #if second word has a name
                else:
                    invalid_token = True

                    #if word is a know token, add its address to token content
                    for l in range(1, len(tokenList)):
                        if tokenList[l].name == args[1]:
                            arg0 = tokenList[l].addr
                            tokenList[0].content[-1] += arg0 >> 8
                            tokenList[0].content.append(arg0 & 255)
                            invalid_token = False

                    #if word is an invalid token, create this token
                    if invalid_token:
                        assert tokenList[0].name != args[1], f"[line {l+1}] Invalid declaration <{args[1]}>"

                        #determine ram address of created token
                        if tokenList[0].name == "start":
                            try:
                                invalid_token_addr = tokenList[1].addr - 1
                            except IndexError:
                                invalid_token_addr = 4095
                        else:
                            invalid_token_addr = tokenList[0].addr + len(tokenList[0].content) - 2
                            tokenList[0].addr -= 1

                        #add token at second to last in token list
                        tokenList.insert(1, Token(args[1], invalid_token_addr))
                        tokenList[1].content.append(None)
                        tokenList[1].contentstr.append("<Empty>")
                        arg0 = tokenList[1].addr
                        tokenList[0].content[-1] += arg0 >> 8
                        tokenList[0].content.append(arg0 & 255)

                if tokenList[0].name != "start":
                    tokenList[0].addr -= 1
                    mem_ptr -= 1
            if tokenList[0].name != "start":
                tokenList[0].addr -= 1
                mem_ptr -= 1
        assert mem_ptr > 0, "Program unable to fit in memory"

    #Write program to RAM
    mem_ptr = 0
    program_size = 0
    if len(tokenList) > 1:
        assert tokenList[1].addr >= len(tokenList[0].content), "Too many variable or declared function after start"
    for token in tokenList:
        if len(token.content) == 0: continue
        mem_ptr = token.addr
        for content in token.content:
            if type(content) is int:
                RAM.mem[mem_ptr].equal(content)
                program_size += 1
                mem_ptr += 1
        if special_mode[5] or special_mode[1]:
            print("[Asm]", token)
            if special_mode[1]:
                RAM.chunk(token.addr, token.addr + len(token.content) - 1)
    program_size = max(len(RAM), program_size)
    if special_mode[7]:
        return program_size
    print(f"Assembled successfully ({round((perf_counter() - start)*1000,2)}ms)")
    print(f"Program size: {program_size} bytes ({round(program_size/RAM_SIZE*100,2)}%)\n")

    if special_mode[6]:
        print("Initializing Screen")
        SCREEN.on()

    #manual clock cycle mode
    if special_mode[4]:
        if input(" > ").lower() != "stop":
            while run(True, True, special_mode[0], special_mode[6]):
                if input("\n > ").lower() == "stop": break
        print("\n_________________________________                               \n"
              "OUT :", OUT,)

    #if program contains a halt (careful bc some programs might no end)
    elif program_ends:
        start = perf_counter()
        tick = 0
        while run(False, True, special_mode[0], special_mode[6]): tick += 1
        time = perf_counter() - start
        units = 1000 if time < 10 else 1
        print(f"_________________________________\n"
              f"Program execution: {time*units:.2f}{'ms' if time < 10 else 's'}, "
              f"{tick/time/1000:.2f}kHz\n"
              "OUT :", OUT)

    #program contains no loops
    else:
        l = 0
        while run(True, False, special_mode[0], special_mode[6]) and \
            (l<2**20 if special_mode[3] else l<2**14):
            if not special_mode[3]:
                sleep(0.03)
            l += 1
        print("_________________________________                               \n"
              "OUT :", OUT)

    if special_mode[2]:
        RAM.chunk(0x500,0x503)
        result = RAM.mem[0x500].uint()\
        | RAM.mem[0x501].uint() << 8  \
        | RAM.mem[0x502].uint() << 16 \
        | RAM.mem[0x503].uint() << 24
        print("Result:", result)
    #print(Gate.count, "logic gates used\n")

#if program is run as a main file ask for a file
if __name__ == "__main__":
    print(f'SBB Computer & SBBasm {__version__} by Charles Benoit ({__last_update__})')
    special_mode = [False] * 8
    program = input("Load program >>> ").strip()

    #debug tools
    while True:
        match program[-2:]:
            case "-d":
                print("[Special mode] Debug enabled")
                special_mode[0] = True
            case "-r":
                print("[Special mode] RAM printing enabled")
                special_mode[1] = True
            case "-m":
                print("[Special mode] Show mult output enabled")
                special_mode[2] = True
            case "-f":
                print("[Special mode] Fast mode enabled")
                special_mode[3] = True
            case "-s":
                print("[Special mode] Manual clock enabled")
                special_mode[4] = True
            case "-t":
                print("[Special mode] Token printing enabled")
                special_mode[5] = True
            case "-v":
                print("[Special mode] Screen visuals enabled")
                special_mode[6] = True
            case "-o":
                print("[Special mode] Object file compiling enabled")
                read_program(program[:-2].strip(), create_object_file=True)
            case _:
                print()
                break
        program = program[:-2].strip()

    run_program(read_program(program), *special_mode)