import re

TYPE_FUNC = 'func'
TYPE_VAR = 'var'
TYPE_CONST = 'const'
TYPE_TYPE = 'type'
TYPE_IMPORT = 'import'

end_of_block_delimiters_re = re.compile(r'[`\'"{}()\n,=]|//|/\*|\*/')

def end_of_block(s: str, start: int) -> int:
    #if s[openBracketPos] != '{' and s[openBracketPos] != '(' and s[openBracketPos] != '[':
    #    raise Exception('want openBracketPos in second argument')
    
    quoteOpened = ''
    multilineComment = False
    single_line_comment_end = 0
    brackets = []

    #print('end of block', s[start:])

    for m in end_of_block_delimiters_re.finditer(s, start):
        x = m.group()
        pos = m.start()
        if pos <= single_line_comment_end:
            continue
        # print(x, pos)
        if multilineComment:
            if x == "*/":
                multilineComment = False
            continue
        if quoteOpened != '':
            if x != quoteOpened:
                continue # inside string
            backslash_count = 0
            while pos-1-backslash_count >= 0:
                if s[pos-1-backslash_count] != '\\':
                    break
                backslash_count += 1
            if quoteOpened != '`' and backslash_count % 2 == 1:
                continue # quote is escaped
            quoteOpened = ''
            if len(brackets) == 0:
                return pos+1
            continue

        if x == '//':
            single_line_comment_end = s.find('\n', pos)
            if len(brackets) == 0:
                return single_line_comment_end
            continue
        if x == '/*':
            multilineComment = True
            continue
        if x in '\'"`':
            quoteOpened = x
            continue
        if x == '\n' or x == ',' or x == '=':
            if len(brackets) == 0:
                #print(f"end of block return 68: {x}, pos={pos}")
                return pos
            continue
        if x in '{[(':
            #print(f"add bracket {x} pos={pos}")
            brackets.append(x)
            continue
        if len(brackets) == 0:
            raise Exception(f"unexpected delimiter {x} at pos={pos}")
        wantBracket = '}' if brackets[-1] == '{' else ']' if brackets[-1] == '[' else ')'
        if x == wantBracket:
            #print(f"pop bracket {x} pos={pos}")
            brackets.pop()
            #if len(brackets) == 0:
            #    return pos+1
            continue
        raise Exception(f"invalid syntax, wrong bracket: expected {wantBracket} got {x} at pos={pos}")
    if len(brackets) > 0 or quoteOpened != '' or multilineComment:
        #print('start_stdout', s[start:], 'end_stdout')
        raise Exception('invalid syntax, no end of block')
    return len(s)

parse_imports_single_import_re = re.compile(r'^import[\t ]+([A-Za-z_][A-Za-z0-9_]*|\.)?[\t ]*"([^"]+)"', re.MULTILINE)
parse_imports_block_import_re = re.compile(r'^import[\t ]+\(', re.MULTILINE)
parse_imports_import_in_block_re = re.compile(r'[\t ]*([A-Za-z_][A-Za-z0-9_]*|\.)?[\t ]*"([^"]+)"')
parse_imports_path_alias_re = re.compile(r'(^|[^A-Za-z0-9_])([A-Za-z0-9_]+)$')

def parse_imports(s: str) -> dict[str, list[str]]:
    imports: dict[str, list[str]] = {}

    raw_imports = []
    for m in parse_imports_single_import_re.finditer(s):
        alias = m.group(1)
        path = m.group(2)
        raw_imports.append((alias, path))

    for m in parse_imports_block_import_re.finditer(s):
        block_start = m.end()-1
        block_end = end_of_block(s, block_start)
        inner_content = s[block_start+1:block_end-1]
        for line in inner_content.split('\n'):
            m = parse_imports_import_in_block_re.search(line)
            if m is None:
                continue
            alias = m.group(1)
            path = m.group(2)
            raw_imports.append((alias, path))

    for (alias, path) in raw_imports:
        if alias is None:
            m = parse_imports_path_alias_re.search(path)
            if m is None:
                continue
            alias = m.group(2)

        imports_by_alias = imports.get(alias, [])
        imports_by_alias.append(path)
        imports[alias] = imports_by_alias

    return imports

parse_funcs_func_re = re.compile(r'^func[\t ]*([A-Za-z_][A-Za-z0-9_]*)[\t ]*(\[[^\]]+\])?[\t ]*\([^)]*\)[^{]*\{', re.MULTILINE)

def parse_funcs(s: str) -> dict[str, str]:
    func_body: dict[str, str] = {}

    for m in parse_funcs_func_re.finditer(s):
        fn = m.group(1)
        fn_start_pos = m.start()
        block_start_pos = m.end()-1
        block_end_pos = end_of_block(s, block_start_pos)
        
        func_body[fn] = s[fn_start_pos:block_end_pos]

    return func_body

parse_directives_block_re = re.compile(r'^(type|var|const)[ \t]*\(', re.MULTILINE)
parse_directives_block_directive_re = re.compile(r'^[\t ]*([A-Za-z_][A-Za-z0-9_]*([\t ]*,[\t ]*[A-Za-z_][A-Za-z0-9_]*)*)', re.MULTILINE)
parse_directives_single_re = re.compile(r'^(type|var|const)[ \t]+([A-Za-z_][A-Za-z0-9_]*([\t ]*,[\t ]*[A-Za-z_][A-Za-z0-9_]*)*)', re.MULTILINE)

def parse_directives(s: str) -> dict[str, dict[str, str]]:
    directives: dict[str, dict[str, str]] = {TYPE_CONST: {}, TYPE_VAR: {}, TYPE_TYPE: {}}

    for m in parse_directives_block_re.finditer(s):
        directive_type = m.group(1)
        fn_start_pos = m.start()
        block_start_pos = m.end()-1
        #print("\n", fn)
        block_end_pos = end_of_block(s, block_start_pos)
        
        block = s[fn_start_pos:block_end_pos]
        #print('block', directive_type, block)
        
        start = block.find('(')+1
        end = block.rfind(')')

        prev_content_end = 0
        for m in parse_directives_block_directive_re.finditer(block, start, end):
            varname = m.group(1)

            if m.start() < prev_content_end:
                continue

            res, prev_content_end = parse_one_directive(block, m.end(), varname, directive_type)

            directives[directive_type].update(res)

    for m in parse_directives_single_re.finditer(s):
        directive_type = m.group(1).strip()
        varname = m.group(2).strip()
        varname_end = m.end()

        res, _ = parse_one_directive(s, varname_end, varname, directive_type)

        directives[directive_type].update(res)            

    return directives

def parse_one_directive(block: str, varname_end: int, varname: str, directive_type: str) -> tuple[dict[str, str], int]:
    res: dict[str, str] = {}

    names = []
    for part in varname.split(','):
        names.append(part.strip())
        #if '[' in names[-1]:
        #    print('varname', varname, block)

    typename_start = varname_end
    typename_end = end_of_block(block, typename_start)
    typename = block[typename_start:typename_end].strip()
    #if directive_type == 'var':
    #   print(f"block\ndirective_type={directive_type}\ntypename={typename}\nblock_content={block}\n")

    if block[typename_end] != '=':
        for name in names:
            if name == '_':
                continue
            res[name] = render_directive(name, typename, None)
        return res, typename_end

    # has value
    value_start = typename_end+1
    value_end = end_of_block(block, value_start)
    value = block[value_start:value_end].strip()
    #if directive_type == 'type':
    #    print(f"block\ndirective_type={directive_type}\nvalue={value}\ntypename={typename}\nblock_content={block}\n")

    value_start = typename_end+1
    for name in names:
        value_end = end_of_block(block, value_start)
        value = block[value_start:value_end].strip()
        #if directive_type == 'type':
        #    print(f"end_of_block name={name} content={block[value_start:]} value={value}")
        if name != '_':
            res[name] = render_directive(name, typename, value)
        value_start = value_end + 1

    return res, value_start


def render_directive(name: str, typename, value: str) -> str:
    if value is None or value == '':
        return f"{name} {typename}"
    if typename is None or typename == '':
        return f"{name} = {value}"
    return f"{name} {typename} = {value}"

def get_deps(directive_type: str, names: list[str], body: str, exclude = [], include: str = []) -> set[tuple[str, str]]:
    if not isinstance(exclude, list):
        exclude = [exclude]

    search_names = [f for f in names if f not in exclude]
    if len(search_names) == 0:
        return set()
    other = '|'.join([f for f in names if f not in exclude])

    #print(other)
    found = re.finditer(r'(?=[^A-Za-z0-9_]('+other+r')[^A-Za-z0-9_])', ' '+body+' ')

    s = set([(directive_type, name.group(1)) for name in found])

    for name in include:
        if name in names:
            s.add((directive_type, name))

    return s


get_package_re = re.compile(r'^package[ \t]+([A-Za-z_][A-Za-z0-9_]*)[^A-Za-z0-9_]', re.MULTILINE)
def get_package(s: str) -> str:
    m = get_package_re.search(s)

    if m is None:
        raise Exception('package not found in file')

    return m.group(1)

def calculate_deps(func_body: dict[str, str], directives: dict[str, dict[str, str]], imports: dict[str, list[tuple[str, str]]]) -> dict[tuple[str, str], set[tuple[str, str]]]:
    deps: dict[tuple[str, str], set[tuple[str, str]]] = {}

    for name, body in func_body.items():
        deps[(TYPE_FUNC, name)] = get_deps(TYPE_FUNC, func_body.keys(), body, [name, '_'])

        for directive_type in [TYPE_VAR, TYPE_CONST, TYPE_TYPE]:
            deps[(TYPE_FUNC, name)].update(get_deps(directive_type, directives[directive_type].keys(), body, [name, '_']))

        deps[(TYPE_FUNC, name)].update(get_deps(TYPE_IMPORT, imports.keys(), body, [name, '.', '_'], ['.', '_']))

    for name, body in directives[TYPE_VAR].items():
        deps[(TYPE_VAR, name)] = get_deps(TYPE_FUNC, func_body.keys(), body, [name, '_'])

        for directive_type in [TYPE_VAR, TYPE_CONST, TYPE_TYPE]:
            #if directive_type == TYPE_CONST:
            #    print(directive_type, name, body, directives[directive_type].keys(), get_deps(directive_type, directives[directive_type].keys(), body, name))
            deps[(TYPE_VAR, name)].update(get_deps(directive_type, directives[directive_type].keys(), body, [name, '_']))

        deps[(TYPE_VAR, name)].update(get_deps(TYPE_IMPORT, imports.keys(), body, [name, '.', '_'], ['.', '_']))

    for name, body in directives[TYPE_TYPE].items():
        deps[(TYPE_TYPE, name)] = get_deps(TYPE_CONST, directives[TYPE_CONST].keys(), body, name)

        deps[(TYPE_TYPE, name)].update(get_deps(TYPE_IMPORT, imports.keys(), body, [name, '.', '_'], ['.', '_']))

    for name, body in directives[TYPE_CONST].items():
        deps[(TYPE_CONST, name)] = get_deps(TYPE_CONST, directives[TYPE_CONST].keys(), body, name)

        deps[(TYPE_CONST, name)].update(get_deps(TYPE_IMPORT, imports.keys(), body, [name, '.', '_'], ['.', '_']))

    for name, values in imports.items():
        deps[(TYPE_IMPORT, name)] = set()

    return deps

def render_func_with_deps(
    func_name: str,
    max_len: int,
    package: str,
    deps: dict[tuple[str, str], set[tuple[str, str]]],
    func_body: dict[str, str],
    directives: dict[str, dict[str, str]],
    imports: dict[str, list[tuple[str, str]]],
) -> str:
    render_list = []
    dedup = set()
    size = 0

    stack = []

    dedup.add((TYPE_FUNC, func_name))
    stack.append((TYPE_FUNC, func_name))

    while len(stack) > 0 and size < max_len:
        el = stack.pop(0)
        (directive_type, name) = el

        el_size = 0
        if directive_type == TYPE_FUNC:
            el_size = len(func_body[name])+2
        elif directive_type == TYPE_IMPORT:
            el_size = len('"'+('"\n"'.join(imports[name]))+'"')
        else:
            el_size = len(directives[directive_type][name])+5

        if el_size+size > max_len and len(render_list) > 0:
            break
    
        render_list.append(el)
        size += el_size
        for stack_candidate in deps[el]:
            if stack_candidate[0] != TYPE_IMPORT:
                continue
            if stack_candidate in dedup:
                continue
            dedup.add(stack_candidate)
            stack.append(stack_candidate)
        for stack_candidate in deps[el]:
            if stack_candidate[0] == TYPE_IMPORT:
                continue
            if stack_candidate in dedup:
                continue
            dedup.add(stack_candidate)
            stack.append(stack_candidate)

    render_imports = ''
    body = ''

    for el in render_list:
        (directive_type, name) = el
        if directive_type == TYPE_FUNC:
            body += func_body[name]+'\n\n'
        elif directive_type == TYPE_IMPORT:
            render_imports += '\t"'+('"\n\t"'.join(imports[name]))+'"\n'
        else:
            body += directive_type+' '+directives[directive_type][name]+'\n\n'

    #print('render list', render_list)
    #print(f"package {package}\n\nimport (\n{render_imports})\n\n{body}")

    if render_imports == '':
        return f"package {package}\n\n{body}"

    return f"package {package}\n\nimport (\n{render_imports})\n\n{body}"

