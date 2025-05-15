import transformers
import torch
import os
# from peft import LoraConfig, get_peft_model, PeftModel
# from vllm import LLM

def make_model_with_tokenizer(name: str):
    model_name = './data/'+name
    if name == 'original' or name == 'default' or name == 'deepseek':
        model_name = 'deepseek-ai/deepseek-coder-1.3b-instruct'

    os.environ['PYTORCH_CUDA_ALLOC_CONF'] = 'expandable_segments:True,max_split_size_mb:128'

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
        # quantization_config=bnb_config,
        trust_remote_code=True,

    )

    # model = LLM(model=model)
    
    #peft_model = PeftModel.from_pretrained(model, model_name)

    return tokenizer, model

def generate_completions(tokenizer, model, prompts):
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