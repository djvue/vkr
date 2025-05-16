import glob
import aiopath
from dataset.parser import get_package, parse_imports, parse_funcs, parse_directives, calculate_deps, render_func_with_deps, TYPE_FUNC, TYPE_IMPORT, TYPE_TYPE, TYPE_CONST, TYPE_VAR

ROOT_DIR = str(aiopath.AsyncPath.cwd().parent)
#ROOT_DIR = str(aiopath.AsyncPath.cwd())
REPOS_DIR = ROOT_DIR+'/data/repos'

INPUT_CODE_MAX_LEN = 1000

system_message = """
You are an expert programmer. 
You should only return output test file containing working code.
The user is going to give you code and would like to have unit tests for for first function.
All the other functions are just dependencies to give you context of all the possible test cases to produce.
Cover all possible inputs and their respective outputs using tests.
Each subtest must be wrapped into t.Run.
"""

def get_prompt(func_name: str, input_code: str) -> list[dict]:
    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": f"write unit tests for function {func_name}:\n```go\n{input_code}```"}
    ]

def get_package_rows(project_path: str, relative_go_package: str) -> list[dict]:
    package_path = REPOS_DIR+'/'+project_path+relative_go_package
    # print('package_path', package_path)

    package_files = glob.glob(package_path+'*.go')

    go_package = ''

    imports: dict[str, list[tuple[str, str]]] = {}
    func_body: dict[str, str] = {}
    directives: dict[str, dict[str, str]] = {TYPE_TYPE: {}, TYPE_VAR: {}, TYPE_CONST: {}}

    for file_path in package_files:
        f = open(file_path, 'r')
        file_content = f.read()
        f.close()

        file_package = get_package(file_content)
        if go_package == '':
            go_package = file_package
        if go_package != file_package:
            continue

        file_imports = parse_imports(file_content)
        file_func_body = parse_funcs(file_content)
        file_directives = parse_directives(file_content)

        imports.update(file_imports)
        func_body.update(file_func_body)
        for directive_type in [TYPE_TYPE, TYPE_CONST, TYPE_VAR]:
            directives[directive_type].update(file_directives[directive_type])

    deps = calculate_deps(func_body, directives, imports)

    res = []

    for func_name in func_body.keys():
        input_code = render_func_with_deps(
            func_name,
            INPUT_CODE_MAX_LEN,
            go_package,
            deps,
            func_body,
            directives,
            imports,
        )

        res.append({
            'project_path': project_path,
            'relative_go_package': relative_go_package,
            'func_name': func_name,
            'input_code': input_code,
            'prompt': get_prompt(func_name, input_code),
        })

    return res