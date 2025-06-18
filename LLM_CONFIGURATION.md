# LLM Configuration Guide

This guide explains how to configure different LLM providers and models with the Agent CLI.

## Overview

The Agent CLI supports multiple LLM providers using the existing `LLMClient` abstraction. You can configure the LLM provider, model, and parameters using either command-line arguments or environment variables.

## Supported Providers

### Anthropic
- **Provider name**: `anthropic`
- **Environment variable**: `ANTHROPIC_API_KEY`
- **Default model**: `claude-sonnet-4-20250514`
- **Available models**: Any Anthropic Claude model

### OpenAI
- **Provider name**: `openai`
- **Environment variable**: `OPENAI_API_KEY`
- **Default model**: `gpt-4`
- **Available models**: Any OpenAI model (GPT-4, GPT-4o, o1, etc.)

## Configuration Methods

### 1. Command Line Arguments

```bash
# Use Anthropic with default model
python cli.py --llm-provider anthropic

# Use OpenAI with specific model
python cli.py --llm-provider openai --llm-model gpt-4o

# Full configuration
python cli.py \
  --llm-provider anthropic \
  --llm-model claude-3-5-sonnet-20241022 \
  --llm-temperature 0.1 \
  --llm-max-tokens 4096
```

### 2. Environment Variables

```bash
# Set provider and model
export LLM_PROVIDER=openai
export LLM_MODEL=gpt-4o
export LLM_TEMPERATURE=0.2
export LLM_MAX_TOKENS=8192

# Set API key
export OPENAI_API_KEY=your-api-key

# Run with environment configuration
python cli.py
```

### 3. Mixed Configuration

Command-line arguments override environment variables:

```bash
# Environment sets defaults
export LLM_PROVIDER=anthropic
export LLM_MODEL=claude-3-5-sonnet-20241022

# CLI overrides provider but keeps model from environment
python cli.py --llm-provider openai
# Result: Uses OpenAI with claude-3-5-sonnet-20241022 model
```

## Configuration Options

### CLI Arguments

- `--llm-provider {anthropic,openai}`: Choose the LLM provider
- `--llm-model MODEL_NAME`: Specify the model name
- `--llm-temperature FLOAT`: Temperature for generation (0.0-1.0)
- `--llm-max-tokens INT`: Maximum tokens for generation

### Environment Variables

- `LLM_PROVIDER`: Default provider (`anthropic` or `openai`)
- `LLM_MODEL`: Default model name
- `LLM_TEMPERATURE`: Default temperature (default: `0.0`)
- `LLM_MAX_TOKENS`: Default max tokens (default: `8192`)
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `OPENAI_API_KEY`: Your OpenAI API key

## Examples

### Basic Usage

```bash
# Use default Anthropic
export ANTHROPIC_API_KEY=your-key
python cli.py --problem-statement "Fix the authentication bug"

# Switch to OpenAI
export OPENAI_API_KEY=your-key
python cli.py --llm-provider openai --problem-statement "Refactor the database layer"
```

### Advanced Configuration

```bash
# Environment setup
export ANTHROPIC_API_KEY=your-anthropic-key
export OPENAI_API_KEY=your-openai-key
export LLM_PROVIDER=anthropic
export LLM_MODEL=claude-3-5-sonnet-20241022
export LLM_TEMPERATURE=0.1

# Use environment defaults
python cli.py --problem-statement "Add user authentication"

# Override specific settings
python cli.py \
  --llm-provider openai \
  --llm-model gpt-4o \
  --llm-temperature 0.2 \
  --problem-statement "Optimize database queries"
```

### Interactive Mode

```bash
# Start interactive session with specific configuration
python cli.py \
  --llm-provider anthropic \
  --llm-model claude-3-5-haiku-20241022 \
  --workspace ./my-project

# Then interact with the agent
```

## Default Behavior

If no configuration is provided:

1. **Provider**: `anthropic` (or from `LLM_PROVIDER` env var)
2. **Model**: Provider-specific default:
   - Anthropic: `claude-sonnet-4-20250514`
   - OpenAI: `gpt-4`
3. **Temperature**: `0.0` (or from `LLM_TEMPERATURE` env var)
4. **Max Tokens**: `8192` (or from `LLM_MAX_TOKENS` env var)

## API Key Requirements

You must set the appropriate API key environment variable:

- For Anthropic: `ANTHROPIC_API_KEY`
- For OpenAI: `OPENAI_API_KEY`

The CLI will check for the required API key based on your selected provider and exit with an error if it's not set.

## Architecture

The configuration system uses the existing `LLMClient` abstraction:

```
CLI Args/Env Vars → Configuration Logic → get_client() → AnthropicDirectClient/OpenAIDirectClient → Agent
```

This approach:
- ✅ **Simple**: Uses existing `get_client()` function
- ✅ **Flexible**: CLI args and environment variables
- ✅ **Compatible**: No changes to Agent or LLMClient
- ✅ **Extensible**: Easy to add new providers to `get_client()`

## Troubleshooting

### Common Issues

1. **Missing API Key**
   ```
   Error: ANTHROPIC_API_KEY environment variable is not set.
   ```
   **Solution**: Set the required API key environment variable.

2. **Invalid Provider**
   ```
   Error: Unsupported LLM provider: invalid-provider
   ```
   **Solution**: Use `anthropic` or `openai` as the provider.

3. **Invalid Model**
   ```
   Error: Unknown model: invalid-model
   ```
   **Solution**: Check the model name with your provider's documentation.

### Debugging

To see what configuration is being used, you can add debug prints or check the logs. The CLI will show which provider and model it's using when it starts.
