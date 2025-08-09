# Whisper Model Setup

This directory stores the local Whisper models for FREE speech-to-text transcription.

## Installation

1. Install Whisper:
```bash
pip install openai-whisper
```

2. The model will be automatically downloaded on first use to this directory.

## Model Information

- **Model**: base
- **Size**: ~142MB
- **Parameters**: 74M
- **Languages**: 99+ languages supported
- **Accuracy**: Very high (comparable to cloud APIs)
- **Cost**: FREE!

## Memory Management

The AudioProcessingService implements automatic memory management:

1. **Lazy Loading**: Model is loaded only when needed
2. **Auto-Unload**: Model is unloaded after 5 minutes of inactivity
3. **VRAM Cleanup**: GPU memory is cleared when model is unloaded
4. **Garbage Collection**: Automatic cleanup to prevent memory leaks

## Manual Download (Optional)

If you want to pre-download the model:

```python
import whisper
model = whisper.load_model("base", download_root="./")
```

## Available Models

- **tiny**: 39M parameters (~39 MB)
- **base**: 74M parameters (~142 MB) - RECOMMENDED
- **small**: 244M parameters (~483 MB)
- **medium**: 769M parameters (~1.5 GB)
- **large**: 1550M parameters (~3.1 GB)
- **turbo**: Optimized for English

## GPU Support

If you have a CUDA-capable GPU:
- Model will automatically use GPU for faster transcription
- FP16 precision is enabled for better performance
- VRAM is automatically cleared after use

## Directory Structure

```
models/
├── README.md
└── base.pt  (auto-downloaded on first use)
```

## Troubleshooting

1. **Out of Memory**: The base model uses ~1GB VRAM. If you get OOM errors, the model will automatically fall back to CPU.

2. **Slow Performance**: CPU transcription is slower but still works. Consider using a smaller model (tiny) for faster CPU performance.

3. **Download Issues**: If automatic download fails, manually download the model using the Python script above.