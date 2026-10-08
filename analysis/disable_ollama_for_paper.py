"""Disable only the configured Ollama model; do not expose environment secrets."""
import json
import re
from pathlib import Path

from memebot.core.config import Settings

path = Path(__file__).resolve().parents[1] / '.env'
before = Settings().safe_summary()
original = path.read_text(encoding='utf-8')
updated, count = re.subn(r'(?m)^\s*BULLSEYE_OLLAMA_MODEL\s*=.*(?:\n|$)', '', original)
path.write_text(updated, encoding='utf-8')
after = Settings().safe_summary()
changed = [key for key in before if before[key] != after[key]]
assert not Settings().ollama_model, 'Ollama remains enabled by another configuration source'
assert set(changed) <= {'ollama_model_configured', 'execution_parameters'}, changed
changed_parameters = [key for key in before['execution_parameters']
                      if before['execution_parameters'][key] != after['execution_parameters'][key]]
assert set(changed_parameters) <= {'ollama_model'}, changed_parameters
assert Settings().execution_mode == 'paper'
print(json.dumps({'ollama_model_configured': False, 'removed_model_settings': count,
                  'changed_settings': changed, 'execution_mode': 'paper'}))
