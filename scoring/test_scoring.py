import pytest
import aiopath
from scoring.scoring import Scorer, setup_env


@pytest.mark.parametrize('project_path, relative_go_package, func_name, completion_path, expected_result',
    [
('c3643eb9da5c673101f8fe15a6deb40bfc4a1c85/', 'pkg/markdown/', 'ToHTML', 'scoring/tests/prompt_pkg_markdown_convert.md', {
    'error_type': '',
    'coverage': 83.3,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 1, 'passed': 0, 'failed': 2, 'all_passed': 0},
}),
('c3643eb9da5c673101f8fe15a6deb40bfc4a1c85/', 'pkg/markdown/', 'ToHTML', 'scoring/tests/prompt_pkg_markdown_convert_goimports_broken.md', {
    'error_type': 'goimports',
    'coverage': 0.0,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 0, 'passed': 0, 'failed': 0, 'all_passed': 0},
}),
('c3643eb9da5c673101f8fe15a6deb40bfc4a1c85/', 'pkg/markdown/', 'ToHTML', 'scoring/tests/prompt_pkg_markdown_convert_deps_broken.md', {
    'error_type': 'get_deps',
    'coverage': 0.0,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 0, 'passed': 0, 'failed': 0, 'all_passed': 0},
}),
('c3643eb9da5c673101f8fe15a6deb40bfc4a1c85/', 'pkg/markdown/', 'ToHTML', 'scoring/tests/prompt_pkg_markdown_convert_test_build_failed.md', {
    'error_type': 'test_build_failed',
    'coverage': 0.0,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 0, 'passed': 0, 'failed': 0, 'all_passed': 0},
}),
('35ffa2ac421130af2b8578464a6657aae98295ed/', 'internal/stringutil/', 'MatchCaptureGroups', 'scoring/tests/prompt_stringutil.md', {
    'error_type': '',
    'coverage': 100.0,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 1, 'passed': 0, 'failed': 0, 'all_passed': 0},
}),
('44846bba2287e2ce117baa253454befd6313161f/', 'pkg/topology/kademlia/internal/metrics/', 'PeerLogIn', 'scoring/tests/prompt_PeerLogIn.md', {
    'error_type': '',
    'coverage': 81.8,
    'mutation_score': 0.333333,
    'test_results': {'root_passed': 1, 'root_failed': 0, 'passed': 0, 'failed': 0, 'all_passed': 1},
}),

   ])
@pytest.mark.asyncio
async def test_score(project_path, relative_go_package, func_name, completion_path, expected_result):
    setup_env()

    scorer = Scorer(project_path, relative_go_package, func_name)

    completion = await aiopath.AsyncPath(completion_path).read_text()
    evaluate_result = await scorer.score(completion)

    print(evaluate_result)

    assert evaluate_result['error_type'] == expected_result['error_type']
    assert evaluate_result['coverage'] == expected_result['coverage']
    assert evaluate_result['mutation_score'] == expected_result['mutation_score']
    assert evaluate_result['test_results'] == expected_result['test_results']


@pytest.mark.parametrize('evaluate_result, expected_reward',
    [
({
    'error': '',
    'error_type': 'goimports',
    'coverage': 0.0,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 0, 'passed': 0, 'failed': 0, 'all_passed': 0},
}, 0.0),
({
    'error': '',
    'error_type': 'goimports',
    'coverage': 0.0,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 0, 'passed': 0, 'failed': 0, 'all_passed': 0},
}, 0.0),
({
    'error': '',
    'error_type': 'get_deps',
    'coverage': 0.0,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 0, 'passed': 0, 'failed': 0, 'all_passed': 0},
}, 0.0),
({
    'error': '',
    'error_type': 'test_build_failed',
    'coverage': 0.0,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 0, 'passed': 0, 'failed': 0, 'all_passed': 0},
}, 0.0),
({
    'error': '',
    'error_type': '',
    'coverage': 1.5,
    'mutation_score': 0.0,
    'test_results': {'root_passed': 0, 'root_failed': 1, 'passed': 1, 'failed': 1, 'all_passed': 0},
}, 0.453),
({
    'error': '',
    'error_type': '',
    'coverage': 75,
    'mutation_score': 0.333333,
    'test_results': {'root_passed': 1, 'root_failed': 0, 'passed': 1, 'failed': 0, 'all_passed': 1},
}, 0.8833333),
    ])
def test_calculate_reward(evaluate_result, expected_reward):
    scorer = Scorer('', '', '')

    reward = scorer.calculate_reward(evaluate_result)

    assert reward == expected_reward

