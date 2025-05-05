import datasets
import transformers
from peft import LoraConfig, get_peft_model
from trl import GRPOTrainer, GRPOConfig
#from evaluator import batch_get_rewards, setup_env
import torch
import gc
import os
from scoring.scoring import setup_env, Scorer
import asyncio
import json
from tqdm import tqdm
import hashlib


setup_env()
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,max_split_size_mb:128'

ds = datasets.load_from_disk('./data/splitted_ds')
test_ds = ds['test']
test_ds = test_ds.skip(100).take(400)

#model_name = 'deepseek-ai/deepseek-coder-1.3b-instruct'
model_name = './data/model_2'

tokenizer = transformers.AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)

# bnb_config = transformers.BitsAndBytesConfig(
#     load_in_4bit=True,
#     bnb_4bit_use_double_quant=True,
#     bnb_4bit_quant_type="nf4",
#     bnb_4bit_compute_dtype=torch.bfloat16,
#     bnb_4bit_quant_storage=torch.bfloat16,
# )


model = transformers.AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    #torch_dtype=torch.float16,
    torch_dtype=torch.bfloat16,
    #use_cache=False,
    #low_cpu_mem_usage=True,
    #local_files_only=True,
    #quantization_config=bnb_config,
)

def generate_completions(prompts):
    texts = [tokenizer.apply_chat_template(
        prompt,
        tokenize=False,
        add_generation_prompt=True
    ) for prompt in prompts]
    model_inputs = tokenizer(texts, padding=True, return_tensors="pt", truncation=True, max_length=1200).to(model.device)

    # tokenizer.eos_token_id is the id of <|EOT|> token
    model.generation_config.pad_token_id = tokenizer.pad_token_id
    # with torch.no_grad()
    outputs = model.generate(**model_inputs, max_new_tokens=1200, do_sample=False, top_k=50,
        # top_p=0.95,
        num_return_sequences=1,
        pad_token_id=tokenizer.eos_token_id,eos_token_id=tokenizer.eos_token_id)

    outputs = [output[model_inputs['input_ids'].shape[1]:] for i, output in enumerate(outputs)]
    completions = tokenizer.batch_decode(outputs, skip_special_tokens=True)

    return completions

def reward_func(prompts, completions, **kwargs):
    completions = [chat[0]['content'] for chat in completions]
    #scores = batch_get_rewards(completions, kwargs['project_path'], kwargs['relative_package_path'], kwargs['relative_file_path'])
    scores = evaluator.batch_get_rewards(completions, kwargs['project_path'], kwargs['relative_package_path'], kwargs['relative_file_path'])

    return scores

async def run():
    for row in tqdm(test_ds):
        completion = generate_completions([row['prompt']])[0]

        scorer = Scorer(row['project_path'], row['relative_package_path'], row['relative_file_path'])

        evaluation_result = await scorer.score(completion)

        reward = scorer.calculate_reward(evaluation_result)

        hash_content = json.dumps({
            **row,
            'completion': completion,
        }, sort_keys=True).encode()
        h = hashlib.sha256(hash_content).hexdigest()
        log_content = json.dumps({
            'hash': h,
            **row,
            'completion': completion,
            'result': evaluation_result,
            'reward': reward,
        })
        with open('logs/eval2_model_2_no_q.log', 'a+') as f:
            f.write(log_content+"\n")

asyncio.run(run())