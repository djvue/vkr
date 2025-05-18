import datasets
import json
from tqdm.asyncio import tqdm
import hashlib
from evaluating.generator import make_model_with_tokenizer, generate_completions
from scoring.scoring import setup_env, Scorer
import pandas as pd
import time
import aiopath


def get_hash(row: dict):
    hash_content = (row['project_path']+row['relative_go_package']).encode()
    h = hashlib.sha256(hash_content).hexdigest()
    return h

system_message = """
You are an expert programmer. 
You should only fix input unit test file to make code working.
Input has this structure:
1. An error text that is raised when trying to run test file
2. Test file code
3. File which is tested
All the other files are just dependencies to give you context.
"""

def get_fixing_prompt(row: dict, test_file_content: str, evaluation_result: dict) -> str:
    old_user_prompt = row['prompt'][1]['content']
    err = evaluation_result['error']

    user_content = f"raised error:\n`{err[:100]}`\ntest file content which you need to fix and return:\n```go\n{test_file_content}\n```\ntested file:\n```go\n{old_user_prompt}\n```"

    return [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_content},
    ]
    

async def fix_error(tokenizer, model, row: dict, test_file_content: str, evaluation_result: dict) -> str:
    prompt2 = get_fixing_prompt(row, test_file_content, evaluation_result)
    
    completion2 = generate_completions(tokenizer, model, [prompt2])[0]

    return completion2


async def generate(name: str, take: int, no_fixing: bool):
    setup_env()
    tokenizer, model = make_model_with_tokenizer(name)

    ds = datasets.load_from_disk('./data/splitted_ds')
    test_ds = ds['test']

    out_log = f"./logs/{name}/generate.log"
    await aiopath.AsyncPath(out_log).parent.mkdir(exist_ok=True, parents=True)
    await aiopath.AsyncPath(out_log).touch()

    fixed_in_log = f"./logs/{name}/score.log"
    await aiopath.AsyncPath(fixed_in_log).touch()
    fixed_out_log = f"./logs/{name}/generate_fixed.log"
    await aiopath.AsyncPath(fixed_out_log).touch()

    out_df = pd.read_json(out_log, lines=True)
    ready = len(out_df)
    total_time = 0
    processed_count = 0
    with tqdm(total=take, initial=ready, postfix={'avg_time': 0, 'estimate': 0}) as t:
        t.set_description('generate')

        if ready < take:
            test_ds = test_ds.take(take).skip(ready)
        else:
            test_ds = []

        for row in test_ds:
            start = time.time()
            completion = generate_completions(tokenizer, model, [row['prompt']])[0]

            log_content = json.dumps({
                'hash': '',
                **row,
                'hash': get_hash(row),
                'generate_time': time.time()-start,
                'completion': completion,
            })
            with open(out_log, 'a+') as f:
                f.write(log_content+"\n")
            ready += 1
            total_time += time.time()-start
            processed_count += 1
            t.set_postfix({
                'avg_time': '{0:.2f}'.format(total_time/processed_count),
                'estimate': '{0:.2f}'.format((take - ready)/processed_count*total_time),
            })
            t.update(1)

    if no_fixing:
        return

    out_df = pd.read_json(fixed_out_log, lines=True)
    ready = len(out_df)
    total_time = 0
    processed_count = 0
    with tqdm(total=take, initial=ready, postfix={'avg_time': 0, 'estimate': 0}) as t:
        t.set_description('generate fixed')
        while True:
            in_df = pd.read_json(fixed_in_log, lines=True)

            unprocessed_df = in_df.tail(len(in_df) - ready)

            for _, row in unprocessed_df.iterrows():
                scorer = Scorer(row['project_path'], row['relative_go_package'], row['func_name'])

                completion = row['completion']
                evaluation_result = row['result']
                start = time.time()

                try_fix = evaluation_result['error_type'] != ''
                completion2 = ''
                if try_fix:
                    test_file_content = completion
                    try:
                        test_file_content = scorer.test_file_content_from_completion(completion)
                    except Exception as e:
                        pass
                    completion2 = await fix_error(tokenizer, model, row, test_file_content, evaluation_result)

                log_content = json.dumps({
                    **row,
                    'try_fix': try_fix,
                    'generate_time2': time.time()-start,
                    'completion2': completion2,
                })
                with open(fixed_out_log, 'a+') as f:
                    f.write(log_content+"\n")
                ready += 1
                total_time += time.time()-start
                processed_count += 1
                t.set_postfix({
                    'avg_time': '{0:.2f}'.format(total_time/processed_count),
                    'estimate': '{0:.2f}'.format((take - ready)/processed_count*total_time),
                })
                t.update(1)
            
            if ready >= take:
                break
            
            if len(unprocessed_df) == 0:
                time.sleep(10)
