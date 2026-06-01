# Recommended Models

AgentQuest now selects models by alias from `configs/model_catalog.json` instead of local `.gguf` paths.

| Alias | Display Name | Hugging Face |
| --- | --- | --- |
| `qwen3_4b_q4_k_m` | Qwen3 4B Q4_K_M | `Qwen/Qwen3-4B-GGUF` / `Qwen3-4B-Q4_K_M.gguf` |
| `qwen2_5_3b_instruct_q5_k_m` | Qwen2.5 3B Instruct Q5_K_M | `Qwen/Qwen2.5-3B-Instruct-GGUF` / `qwen2.5-3b-instruct-q5_k_m.gguf` |
| `llama_3_2_3b_instruct_q4_k_m` | Llama 3.2 3B Instruct Q4_K_M | `gpustack/Llama-3.2-3B-Instruct-GGUF` / `Llama-3.2-3B-Instruct-Q4_K_M.gguf` |

Use the alias in `configs/run_config.json`:

```json
{
  "backend": "llama_cpp",
  "model": "qwen3_4b_q4_k_m",
  "preset": "BATTLE_PLAN",
  "prompt_format": "json_only"
}
```
