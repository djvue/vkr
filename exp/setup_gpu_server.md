```bash
ssh ...
ssh-keygen -t ed25519
cp .ssh/id_ed25519.pub .ssh/authorized_keys
cat .ssh/id_ed25519
systemctl reload sshd

# on client system
nano ~/.ssh/gpudc_ed25519
# save private key
chmod 600 ~/.ssh/gpudc_ed25519
nano ~/.ssh/config
# enter
Host gpudc
	User user
	Hostname 85.143.167.11
    PreferredAuthentications publickey
    IdentityFile /home/djvue/.ssh/gpudc_ed25519
 

ssh selgpu

# in ssh

# pyenv
sudo apt update && sudo apt install -y build-essential libssl-dev zlib1g-dev \
libbz2-dev libreadline-dev libsqlite3-dev curl git \
libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev libffi-dev liblzma-dev

curl -fsSL https://pyenv.run | bash
nano .bashrc
# add lines from output pyenv.run to .bashrc end
# reboot terminal ctrl+d

pyenv install 3.11
pyenv global 3.11
sudo apt update && apt-get install -y python3-venv

mkdir -p /opt/vkr
mkdir -p /opt/vkr/data
cd /opt/vkr
python -m venv .venv
source .venv/bin/activate

wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/cuda-keyring_1.1-1_all.deb
sudo dpkg -i cuda-keyring_1.1-1_all.deb
sudo apt-get update
sudo apt-get -y install cuda-toolkit-12-8

pip install --upgrade pip
pip install 'torch>=2.7.0' torchvision torchaudio --index-url https://download.pytorch.org/whl/cu128
pip install datasets transformers tensorflow[and-cuda] trl tf-keras 'accelerate>=0.26.0' peft bitsandbytes

# instead for vllm
sudo apt-get -y install cuda-toolkit-12-4

pip install -U torch==2.6.0 torchvision==0.21.0 torchaudio==2.6.0
# --index-url https://download.pytorch.org/whl/cu126

## continue

pip freeze | grep torch

python -c 'import tensorflow as tf; tf.config.list_physical_devices('GPU')'

# from client system
scp ./train.py selgpu:/opt/vkr
scp ./evaluator.py selgpu:/opt/vkr
scp ./evaluator_client.py selgpu:/opt/vkr
scp -r ./data/splitted_ds selgpu:/opt/vkr/data/splitted_ds

# server system
cd /opt/vkr
source .venv/bin/activate
python train.py

```

hTzsqb8w

fastapi run evaluator_server.py


trl vllm-serve --model deepseek-ai/deepseek-coder-1.3b-instruct