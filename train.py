import datasets
import transformers
from peft import LoraConfig, get_peft_model
from trl import GRPOTrainer, GRPOConfig
#from evaluator import batch_get_rewards, setup_env
import torch
import gc
import os
import scoring.scoring_client


#setup_env()
gc.collect()
torch.cuda.empty_cache()
os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,max_split_size_mb:128'


ds = datasets.load_from_disk('../data/splitted_ds')
train_ds = ds['train']
train_ds = train_ds.take(500)

#ds['train'].take(100).save_to_disk('./data/splitted_sample_ds')
#train_ds = datasets.load_from_disk('./data/splitted_sample_ds')


print(train_ds)

def reward_func(prompts, completions, **kwargs):
    completions = [chat[0]['content'] for chat in completions]
    #scores = batch_get_rewards(completions, kwargs['project_path'], kwargs['relative_package_path'], kwargs['relative_file_path'])
    scores = scoring.scoring_client.batch_get_rewards(completions, kwargs['project_path'], kwargs['relative_package_path'], kwargs['relative_file_path'])

    return scores

bnb_config = transformers.BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
    bnb_4bit_quant_storage=torch.bfloat16,
)

model_name = 'deepseek-ai/deepseek-coder-1.3b-instruct'
#model_name = 'TheBloke/deepseek-coder-1.3b-instruct-AWQ'
#model_name = 'TheBloke/deepseek-coder-1.3b-instruct-GPTQ'
#model_name = './data/model_1'
model = transformers.AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    #torch_dtype=torch.float16,
    torch_dtype=torch.bfloat16,
    #use_cache=False,
    #low_cpu_mem_usage=True,
    #local_files_only=True,
    quantization_config=bnb_config,
)

peft_config = LoraConfig(
    lora_alpha=16,
    lora_dropout=0.05,
    r=16,
    bias="none",
    target_modules="all-linear",
    task_type="CAUSAL_LM",
    modules_to_save=[
        "lm_head",
        "embed_tokens",
    ],
)

# lora_config = LoraConfig(
#     target_modules=["q_proj", "k_proj"],
#     modules_to_save=["lm_head"],
# )
# model.add_adapter(lora_config, adapter_name="lora_1")

max_prompt_length = 1200
max_completion_length = 1200

training_args = GRPOConfig(
    #use_vllm=True,
    #vllm_device="cuda:0",
    #vllm_gpu_memory_utilization=0.35,
    #vllm_max_model_len=max_prompt_length + max_completion_length,

    output_dir='../data/trainer_output',
    max_prompt_length=max_prompt_length,
    max_completion_length=max_completion_length,
    num_generations=2,
    per_device_train_batch_size=2,
    per_device_eval_batch_size=2,
    num_train_epochs=2,

    learning_rate=2e-05,
    bf16=True, 

    gradient_accumulation_steps=4,
    gradient_checkpointing=True,
    gradient_checkpointing_kwargs={"use_reentrant": False},

    #optim="adamw_8bit",
    optim="adamw_torch_fused",

    logging_steps=1,
    save_steps=500,
    max_grad_norm=0.1,
    report_to="tensorboard",
    logging_dir="logs/runs",
)

trainer = GRPOTrainer(
    model=model,
    reward_funcs=reward_func,
    train_dataset=train_ds,
    args=training_args,
    peft_config=peft_config,
)

trainer.train()

trainer.save_model("data/model_2")
