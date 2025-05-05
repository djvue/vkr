import pytest
import aiopath
from scoring.scoring_client import batch_get_rewards


@pytest.mark.parametrize('project_path, relative_package_path, relative_file_path, completion_path, expected_result',
    [
        (
            ['c3643eb9da5c673101f8fe15a6deb40bfc4a1c85/', '35ffa2ac421130af2b8578464a6657aae98295ed/'],
            ['pkg/markdown/', 'internal/stringutil/'],
            ['pkg/markdown/convert.go', 'internal/stringutil/parse.go'],
            ['scoring/tests/prompt_pkg_markdown_convert_goimports_broken.md', 'scoring/tests/prompt_stringutil.md'],
            [0, 0.5342]
        ),
    ])
@pytest.mark.asyncio
async def test_batch_get_rewards(project_path, relative_package_path, relative_file_path, completion_path, expected_result):
    completions = [await aiopath.AsyncPath(p).read_text() for p in completion_path]

    got_result = batch_get_rewards(completions, project_path, relative_package_path, relative_file_path)
    
    assert got_result == expected_result
