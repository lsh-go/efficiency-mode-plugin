---
description: Optimize a prompt using local Ollama LLM to reduce tokens and clarify intent.
---

The user wants to optimize a prompt using the local Ollama LLM before sending it to Claude.

Run the prompt optimizer script with the provided argument:

```bash
C:/ProgramData/Anaconda3/python.exe C:/Users/Administrator/Desktop/master/scripts/prompt_optimizer.py "$ARGUMENTS"
```

If no argument is provided, show usage:
```
Usage: /opt <your prompt text>

Example:
  /opt sys/strategy_manager 안에 있는 파일들 다 보여주고 각각 뭐 하는지 설명해줘

The optimizer will:
1. Compress your prompt to its core intent
2. Show token savings estimate
3. Classify complexity (simple/medium/complex)
4. Output the optimized version ready to use
```

After showing the result, ask the user if they want to proceed with the optimized prompt.
