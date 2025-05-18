import pandas as pd
from scoring.scoring import setup_env, Scorer
import json
from tqdm.asyncio import tqdm
import hashlib
import time
import numpy as np
import aiopath


async def score(name: str, take: int, no_fixing: bool):
    setup_env()

    in_log = f"./logs/{name}/generate.log"
    out_log = f"./logs/{name}/score.log"
    await aiopath.AsyncPath(out_log).touch()

    fixed_in_log = f"./logs/{name}/generate_fixed.log"
    await aiopath.AsyncPath(fixed_in_log).touch()
    fixed_out_log = f"./logs/{name}/score_fixed.log"
    await aiopath.AsyncPath(fixed_out_log).touch()

    out_df = pd.read_json(out_log, lines=True)
    ready = len(out_df)
    total_reward = 0.0
    total_time = 0.0
    processed_count = 0
    for _, row in out_df.iterrows():
        processed_count += 1
        reward = row.get('reward', 0.0)
        total_reward += reward
        
    with tqdm(total=take, initial=ready, postfix={'avg_reward': 0, 'avg_score_time': 0}) as t:
        t.set_description('score')
        if ready > 0 and processed_count > 0:
            t.set_postfix({
                'avg_reward': '{0:.4f}'.format(total_reward/ready),
                'avg_score_time': '{0:.2f}'.format(total_time/processed_count),
            })
        t.update()
        while True:
            if ready >= take:
                break

            in_df = pd.read_json(in_log, lines=True)

            unprocessed_df = in_df.tail(len(in_df) - ready)

            for _, row in unprocessed_df.iterrows():
                completion = row['completion']

                scorer = Scorer(row['project_path'], row['relative_go_package'], row['func_name'])

                start = time.time()
                evaluation_result = await scorer.score(completion)

                reward = scorer.calculate_reward(evaluation_result)

                log_content = json.dumps({
                    **row,
                    'score_time': time.time()-start,
                    'result': evaluation_result,
                    'reward': reward,
                })
                with open(out_log, 'a+') as f:
                    f.write(log_content+"\n")

                ready += 1
                total_time += time.time()-start
                total_reward += reward
                processed_count += 1
                t.set_postfix({
                    'avg_reward': '{0:.4f}'.format(total_reward/ready),
                    'avg_score_time': '{0:.2f}'.format(total_time/processed_count),
                })
                t.update(1)
            
            if ready >= take:
                break
            
            if len(unprocessed_df) == 0:
                time.sleep(10)

    if no_fixing:
        return

    out_df = pd.read_json(fixed_out_log, lines=True)
    ready = len(out_df)
    total_time = 0.0
    total_reward = 0.0
    processed_count = 0
    for _, row in out_df.iterrows():
        processed_count += 1
        reward = row['best_reward']
        if np.isnan(reward):
            reward = row['reward']
            if np.isnan(reward):
                reward = 0.0
        total_reward += reward
        
    with tqdm(total=take, initial=ready, postfix={'avg_reward': 0, 'avg_score_time': 0}) as t:
        t.set_description('score fixed')
        if ready > 0 and processed_count > 0:
            t.set_postfix({
                'avg_reward': '{0:.4f}'.format(total_reward/ready),
                'avg_score_time': '{0:.2f}'.format(total_time/processed_count),
            })
        t.update()
        while True:
            if ready >= take:
                break

            in_df = pd.read_json(fixed_in_log, lines=True)

            unprocessed_df = in_df.tail(len(in_df) - ready)

            for _, row in unprocessed_df.iterrows():
                completion = row['completion2']
                evaluation_result = row['result']
                reward = row['reward']

                start = time.time()
                scorer = Scorer(row['project_path'], row['relative_go_package'], row['func_name'])            

                evaluation_result2 = {}
                reward2 = 0
                best_reward = reward
                is_reward2_better = False
                if evaluation_result['error_type'] != '':
                    evaluation_result2 = await scorer.score(completion)

                    reward2 = scorer.calculate_reward(evaluation_result2)

                    if reward2 > reward:
                        evaluation_result = evaluation_result2
                        best_reward = reward2
                        is_reward2_better = True

                log_content = json.dumps({
                    **row,
                    'result2': evaluation_result2,
                    'reward2': reward2,
                    'score_time2': time.time()-start,
                    'best_reward': best_reward,
                    'is_reward2_better': is_reward2_better,
                })
                with open(fixed_out_log, 'a+') as f:
                    f.write(log_content+"\n")

                ready += 1
                total_time += time.time()-start
                total_reward += best_reward
                processed_count += 1
                t.set_postfix({
                    'avg_reward': '{0:.4f}'.format(total_reward/ready),
                    'avg_score_time': '{0:.2f}'.format(total_time/processed_count),
                })
                t.update(1)
            
            if ready >= take:
                break
            
            if len(unprocessed_df) == 0:
                time.sleep(10)