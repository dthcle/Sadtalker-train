import os
from src.utils.safetensor_helper import load_x_from_safetensor
import safetensors  
import safetensors.torch


root_path = os.path.dirname(os.path.realpath(__file__))
org = os.path.join(root_path, 'checkpoints', 'SadTalker_V0.0.2_256.safetensors')
new = os.path.join(root_path, 'run_cfg', 'result', 'result', 'ep450_iter450.safetensors')

org_model = safetensors.torch.load_file(org)
new_model = safetensors.torch.load_file(new)
add = {}
for key in org_model:
    print(key)
    if key not in new_model:
        add[key] = org_model[key]
new_model.update(add)
safetensors.torch.save_file(new_model, os.path.join(os.path.dirname(org), "latest.safetensors"))
