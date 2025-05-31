import json
import asyncio
import aiopath
import hashlib
import os
import re
import typing


def setup_env():
    gvm_root = os.environ['GVM_ROOT']
    os.environ['PATH'] = f"{gvm_root}/bin:{gvm_root}/pkgsets/go1.24.2/global/bin:{gvm_root}/gos/go1.24.2/bin:{gvm_root}/pkgsets/go1.24.2/global/overlay/bin:{os.environ['PATH']}"

async def batch_get_rewards_async(completions, project_path: list[str], relative_go_package: list[str], func_name: list[str]) -> list[float]:
    # print(prompts, completions, project_path, relative_go_package, relative_file_path, sep="\n")

    scores = [0.0]*len(completions)

    for i in range(len(completions)):
        scorer = Scorer(project_path[i], relative_go_package[i], func_name[i])

        scores[i] = await scorer.reward(completions[i])

    return scores

        

def batch_get_rewards(completions, project_path, relative_go_package, func_name) -> list[float]:
    scores = [0.0]*len(completions)
    async def run():
        scores = await batch_get_rewards_async(completions, project_path, relative_go_package, func_name)

    asyncio.run(run())

    return scores


class Scorer:
    paths: dict
    project_path: str
    test_file_path: str
    relative_go_package: str
    func_name: typing.Optional[str]
    
    def __init__(self, project_path: str, relative_go_package: str, func_name: typing.Optional[str], relative_file_path: str = None):
        self.paths = {'project_path': project_path, 'relative_go_package': relative_go_package, 'func_name': func_name}
        self.project_path = os.getcwd() + '/data/repos/' + project_path
        if func_name is None:
            filename = relative_file_path[:-3]
            filename = filename[filename.rfind('/')+1]
        else:
            filename = func_name
        self.test_file_path = self.project_path + relative_go_package + '/' + filename + '_llm_test.go'
        self.cover_file_path = self.project_path + relative_go_package + '/' +filename + '_llm_test_cover.out'
        self.relative_go_package = relative_go_package
        self.func_name = func_name

    async def __clean_project_test_files(self):
        project_path = aiopath.AsyncPath(self.project_path)
        async for p in project_path.glob('**/*_test.go'):
            await p.unlink()

    def test_file_content_from_completion(self, completion: str) -> str:
        go_content_start = completion.find('```go')+5
        if go_content_start == 4:
            return completion
        go_content_end = completion.find('```', go_content_start)
        if go_content_end == -1:
            raise Exception('completion parse: no finishing ``` found')
        return completion[go_content_start:go_content_end]

    async def __save_test_file(self, content: str):
        path = aiopath.AsyncPath(self.test_file_path)
        await path.write_text(content)

    def __test_funcs(self, content: str) -> list[str]:
        return re.findall(r'func\W+(Test\w+)\(t\W+\*testing\.T\)\W*\{', content)
    
    async def exec(self, cmd, timeout=60) -> tuple[int, str, str]:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=self.project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        try:
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            try:
                proc.kill()
            except OSError:
                # Ignore 'no such process' error
                pass
            return -1, proc.stdout.decode(), proc.stderr.decode()
        
        return proc.returncode, stdout.decode(), stderr.decode()

    async def __run_goimports(self):
        goimports_binary = f"{os.environ['GVM_ROOT']}/pkgsets/go1.24.2/global/bin/goimports"
        code, stdout, stderr = await self.exec(f"{goimports_binary} -w {self.test_file_path}", timeout=60)
        
        if code == -1:
            raise Exception('goimports: timeout')
        
        if code != 0:
            raise Exception(f"goimports: code {code}, 'strderr' {stderr}")

    async def __run_get_deps(self):
        code, stdout, stderr = await self.exec("go mod tidy", timeout=60)
        
        if code == -1:
            raise Exception('go mod tidy: timeout')
        
        if code != 0:
            raise Exception(f"go mod tidy: code {code}, 'strderr' {stderr}")

    async def __run_tests(self, test_funcs: list[str]) -> tuple:
        code, stdout, stderr = await self.exec(f"go test ./{self.relative_go_package} -run {'/'.join(test_funcs)} -json -coverprofile {self.cover_file_path}", timeout=60)
        
        if code == -1:
            raise Exception('run tests: timeout')
        
        return stdout, stderr, code

    def __parse_tests_stdout(self, stdout: str, stderr: str, returncode: int) -> dict:
        all_passed = 1 if returncode == 0 else 0
        passed = 0
        failed = 0
        root_passed = 0
        root_failed = 0
        for line in stdout.split('\n'):
            if line == "":
                continue
            line_data = {}
            try:
                line_data = json.loads(line)
            except Exception:
                continue
            if line_data.get('Action') == 'build-fail':
                raise Exception(f"go test build failed: stdout = {stdout}, stderr = {stderr}")
            if 'Test' not in line_data:
                continue
            if 'Action' not in line_data:
                continue
            action = line_data['Action']
            if action == 'pass':
                if '/' in line_data['Test']:
                    passed += 1
                else:
                    root_passed += 1
            elif action == 'fail':
                if '/' in line_data['Test']:
                    failed += 1
                else:
                    root_failed += 1
            else:
                continue
        return {'root_passed': root_passed, 'root_failed': root_failed, 'passed': passed, 'failed': failed, 'all_passed': all_passed}
    
    async def __run_mutation_test(self):
        if self.func_name is None:
            code, stdout, stderr = await self.exec(f"go-mutesting ./{self.relative_go_package}", timeout=60)
            
            return stdout, stderr, code

        code, stdout, stderr = await self.exec(f"go-mutesting ./{self.relative_go_package} --match={self.func_name}", timeout=60)
        
        return stdout, stderr, code
    
    async def __parse_mutation_test_stdout(self, stdout: str) -> float:
        score_str = stdout.split('\n')[-2]
        m = re.search(r'^The mutation score is ([01](\.\d+)?) ', score_str)
        if m is None:
            return 0.0
        
        score = m.group(1)
        
        return float(score)
    
    async def __mutation_score(self) -> float:
        stdout, stderr, code = await self.__run_mutation_test()
        
        if code != 0:
            return 0.0
        
        score = await self.__parse_mutation_test_stdout(stdout)
        
        return score
        

    async def __extract_coverage(self) -> float:
        path = aiopath.AsyncPath(self.cover_file_path)

        if not await path.exists():
            raise Exception(f"cover file not exists")

        coverout = await path.read_text()
        #print(path, coverout)

        lines = [line+'\n' for line in coverout.split('\n') if self.relative_go_package in line or line.startswith('mode:')]

        async with path.open(mode='w') as file:
            await file.writelines(lines)
        
        code, stdout, stderr = await self.exec(f"go tool cover -func {self.cover_file_path}", timeout=20)
        
        if code == -1:
            raise Exception('go tool cover: timeout')
        
        if code != 0:
            raise Exception(f"go tool cover: code {code}, 'strderr' {stderr}")

        coverage = 0.0
        foundCoverage = False
        #print(stdout)
        for line in stdout.split('\n'):
            if self.func_name is None:
                if line.startswith('total:'):
                    out = re.search(r"\(statements\)\W+(\d+\.?\d*)\%", line)
                    coverage = float(out.group(1))
                    foundCoverage = True
                continue
            out = re.search(r"\W+"+self.func_name+r"\W+(\d+\.?\d*)\%", line)
            if out is not None:
                coverage = float(out.group(1))
                foundCoverage = True
        if not foundCoverage:
            raise Exception(f"no func coverage, stdout:{stdout}, stderr: {stderr}")

        return coverage
        

    async def __clear(self):
        # clean
        try:
            path = aiopath.AsyncPath(self.test_file_path)
            await path.unlink()
        except Exception:
            pass
        try:
            path = aiopath.AsyncPath(self.cover_file_path)
            await path.unlink()
        except Exception:
            pass

    def __error_type(self, e: Exception) -> str:
        err = str(e)

        if err == '':
            return ''

        # completion parse
        if err.startswith('completion parse: '):
            return 'completion_parse'
        
        # run get deps
        if err.startswith('go mod tidy: '):
            return 'get_deps'

        # run goimports
        if err.startswith('goimports: '):
            return 'goimports'

        # run tests
        # no errors

        # parse tests stdout
        if err.startswith('go test build failed: '):
            return 'test_build_failed'
        
        # extract coverage
        if err.startswith('cover file not exists'):
            return 'no_cover_file'
        if err.startswith('go tool cover: '):
            return 'go_tool_cover'
        if err.startswith('no total coverage, '):
            return 'no_total_coverage'

        return 'other'

    async def score(self, completion: str) -> dict:
        test_results = {'root_passed': 0, 'root_failed': 0, 'passed': 0, 'failed': 0, 'all_passed': 0}
        coverage = 0.0
        mutation_score = 0.0
        try:
            await self.__clean_project_test_files()

            test_file_content = self.test_file_content_from_completion(completion)

            test_funcs = self.__test_funcs(test_file_content)

            if test_funcs == '':
                raise Exception('no test funcs')

            await self.__save_test_file(test_file_content)

            await self.__run_goimports()

            await self.__run_get_deps()

            tests_stdout, tests_stderr, tests_return_code = await self.__run_tests(test_funcs)

            test_results = self.__parse_tests_stdout(tests_stdout, tests_stderr, tests_return_code)

            coverage = await self.__extract_coverage()

            if test_results['all_passed'] == 1:
                mutation_score = await self.__mutation_score()

            await self.__clear()
        except Exception as e:
            #raise e
            result = {'error': str(e)+' '+str(type(e)), 'error_type': self.__error_type(e), 'test_results': test_results, 'coverage': coverage, 'mutation_score': mutation_score}
            await self.log(completion, result)
            return result

        result = {'error': '', 'error_type': '', 'test_results': test_results, 'coverage': coverage, 'mutation_score': mutation_score}
        await self.log(completion, result)
        return result

    async def log(self, completion: str, result: dict):
        hash_content = json.dumps({
            **self.paths,
            'completion': completion,
        }, sort_keys=True).encode()
        h = hashlib.sha256(hash_content).hexdigest()
        cache_content = json.dumps({
            **self.paths,
            'hash': h,
            'completion': completion,
            'result': result
        })
        async with aiopath.AsyncPath(os.getcwd()+'/logs/evaluator.log').open('a+') as f:
            await f.write(cache_content+"\n")

    def calculate_reward(self, evaluate_result: dict) -> float:
        """
        0 if test contains errors and not runnable:
        - failed to get deps
        - failed to format imports
        - test build failed (couldn't run tests, but failed tests are ok)

        0.45 for runnable test
        0.0...0.25 for success test
        0.0...0.2 for coverage
        0.0...0.1 for mutation score
        """
        error = evaluate_result['error']
        error_type = evaluate_result['error_type']
        test_results = evaluate_result['test_results']
        coverage = evaluate_result['coverage']
        mutation_score = evaluate_result['mutation_score']

        reward = 0.0
  
        # not runnable test
        if error_type in ['get_deps', 'goimports', 'test_build_failed']:
            return reward

        total_root_tests = test_results['root_passed'] + test_results['root_failed']
        if total_root_tests == 0:
            return reward
        # runnable test
        reward += 0.45

        reward += 0.25 * test_results['root_passed'] / total_root_tests

        reward += 0.2 * coverage / 100

        reward += 0.1 * mutation_score

        return reward
        

    async def reward(self, completion: str) -> float:
        evaluate_result = await self.score(completion)
        #print(evaluate_result)

        return self.calculate_reward(evaluate_result)
