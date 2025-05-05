import datasets
import transformers
#from peft import LoraConfig
from trl import GRPOTrainer, GRPOConfig
#from evaluator import batch_get_rewards, setup_env
import torch
import gc
import os
import scoring_client


#setup_env()
gc.collect()
torch.cuda.empty_cache()
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,max_split_size_mb:128'


ds = datasets.load_from_disk('./data/splitted_ds')
test_ds = ds['test']
test_ds = test_ds.take(500)

#ds['train'].take(100).save_to_disk('./data/splitted_sample_ds')
#train_ds = datasets.load_from_disk('./data/splitted_sample_ds')


print(test_ds)

def reward_func(prompts, completions, **kwargs):
    completions = [chat[0]['content'] for chat in completions]
    #scores = batch_get_rewards(completions, kwargs['project_path'], kwargs['relative_package_path'], kwargs['relative_file_path'])
    scores = scoring_client.batch_get_rewards(completions, kwargs['project_path'], kwargs['relative_package_path'], kwargs['relative_file_path'])

    return scores

#model_name = 'deepseek-ai/deepseek-coder-1.3b-instruct'
#model_name = 'TheBloke/deepseek-coder-1.3b-instruct-AWQ'
#model_name = 'TheBloke/deepseek-coder-1.3b-instruct-GPTQ'
model_name = './data/model_1'
model = transformers.AutoModelForCausalLM.from_pretrained(model_name,
#torch_dtype=torch.float16,
torch_dtype=torch.bfloat16,
#low_cpu_mem_usage=True
local_files_only=True
).cuda()

# lora_config = LoraConfig(
#     target_modules=["q_proj", "k_proj"],
#     modules_to_save=["lm_head"],
# )
# model.add_adapter(lora_config, adapter_name="lora_1")

max_prompt_length = 1200
max_completion_length = 1200

trainer = GRPOTrainer(
    model=model,
    reward_funcs=reward_func,
    args=GRPOConfig(
        use_vllm=True,
        vllm_device="cuda:0",
        vllm_gpu_memory_utilization=0.35,
        vllm_max_model_len=max_prompt_length + max_completion_length,

        output_dir='./data/trainer_output',
        max_prompt_length=max_prompt_length,
        max_completion_length=max_completion_length,
        num_generations=2,
        per_device_train_batch_size=2,
        per_device_eval_batch_size=2,
        num_train_epochs=2,

        optim="adamw_8bit",
        logging_steps=10,
        save_steps=500,
        max_grad_norm=0.1,
        report_to="tensorboard",
        logging_dir="logs/runs",
    ),
)

metrics = trainer.evaluate(test_ds)

print(metrics)

