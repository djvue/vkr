import transformers
import sys
from dataset.prompt import parse_package, get_prompt, render_func_with_deps
from evaluating.generator import generate_completions
from scoring.scoring import Scorer

model_name = 'Djvue/go-test-rl'
INPUT_CODE_MAX_LEN = 2000

tokenizer = transformers.AutoTokenizer.from_pretrained('deepseek-ai/deepseek-coder-1.3b-instruct', trust_remote_code=True)

model = transformers.AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
)

def generate_test_content(package_path: str, func_name: str) -> str:
        go_package, func_body, directives, imports, deps = parse_package(package_path)

        input_code = render_func_with_deps(
            func_name,
            INPUT_CODE_MAX_LEN,
            go_package,
            deps,
            func_body,
            directives,
            imports,
        )

        prompt = get_prompt(func_name, input_code)

        completion = generate_completions(tokenizer, model, [prompt])[0]

        return Scorer('', '', '', '').test_file_content_from_completion(completion)


def generate_test(package_path: str, func_name: str):
    test_content = generate_test_content(package_path, func_name)
    test_file_path = package_path + '/' + func_name + '_test.go'
    with open(test_file_path, 'w') as f:
        f.write(test_content)

def run():
    if len(sys.argv) < 3:
        print("""
usage:
python console_util.py {package_path} {func_name}
package_path - path to go package to generate test for
func_name - name of function to generate test for
""")
        return

    package_path = sys.argv[1]
    func_name = sys.argv[2]

    package_path = package_path.rstrip('/') + '/'
    generate_test(package_path, func_name)


if __name__ == '__main__':
    run()
