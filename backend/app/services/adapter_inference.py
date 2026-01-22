"""
Service for loading and running inference with trained LoRA adapters.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
import torch
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    GenerationConfig
)
from peft import PeftModel


class AdapterInferenceService:
    """
    Service to load LoRA adapters and run inference for chatbot functionality.
    """

    def __init__(self):
        self.loaded_adapters: Dict[str, Dict] = {}
        self.conversation_histories: Dict[str, List[Dict[str, str]]] = {}

    async def load_adapter(self, session_id: str, adapter_path: str) -> None:
        """
        Load a trained LoRA adapter for inference.

        Args:
            session_id: The session ID
            adapter_path: Path to the adapter directory
        """
        adapter_path = Path(adapter_path)

        # Find the model checkpoint directory
        # LlamaFactory typically creates a checkpoint-XXX directory
        checkpoint_dirs = list(adapter_path.glob("checkpoint-*"))
        if not checkpoint_dirs:
            # Check if files are directly in output directory
            if not (adapter_path / "adapter_config.json").exists():
                raise FileNotFoundError(
                    f"No adapter checkpoint found in {adapter_path}"
                )
            model_path = adapter_path
        else:
            # Use the latest checkpoint
            model_path = sorted(checkpoint_dirs)[-1]

        # Read the adapter config to get the base model
        import json
        with open(model_path / "adapter_config.json", "r") as f:
            adapter_config = json.load(f)

        base_model_name = adapter_config.get("base_model_name_or_path")
        if not base_model_name:
            raise ValueError("Base model name not found in adapter config")

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(
            base_model_name,
            trust_remote_code=True
        )

        # Load base model
        base_model = AutoModelForCausalLM.from_pretrained(
            base_model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True
        )

        # Load LoRA adapter
        model = PeftModel.from_pretrained(
            base_model,
            str(model_path),
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )

        # Merge adapter weights for faster inference (optional)
        model = model.merge_and_unload()

        # Set to evaluation mode
        model.eval()

        # Store loaded model and tokenizer
        self.loaded_adapters[session_id] = {
            "model": model,
            "tokenizer": tokenizer,
            "base_model_name": base_model_name
        }

        # Initialize conversation history
        self.conversation_histories[session_id] = []

    def is_loaded(self, session_id: str) -> bool:
        """Check if adapter is loaded for a session."""
        return session_id in self.loaded_adapters

    async def generate_response(
        self,
        session_id: str,
        user_message: str,
        max_new_tokens: int = 256,
        temperature: float = 0.7,
        top_p: float = 0.9
    ) -> str:
        """
        Generate a response to a user message using the loaded adapter.

        Args:
            session_id: The session ID
            user_message: The user's message
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            top_p: Nucleus sampling parameter

        Returns:
            The generated response
        """
        if session_id not in self.loaded_adapters:
            raise ValueError(f"No adapter loaded for session {session_id}")

        adapter_info = self.loaded_adapters[session_id]
        model = adapter_info["model"]
        tokenizer = adapter_info["tokenizer"]

        # Add user message to history
        self.conversation_histories[session_id].append({
            "role": "user",
            "content": user_message
        })

        # Build conversation prompt
        # Format depends on the model's chat template
        conversation = self.conversation_histories[session_id].copy()

        # Try to use the model's chat template if available
        if hasattr(tokenizer, "apply_chat_template") and tokenizer.chat_template:
            prompt = tokenizer.apply_chat_template(
                conversation,
                tokenize=False,
                add_generation_prompt=True
            )
        else:
            # Fallback to simple format
            prompt = self._format_conversation_simple(conversation)

        # Tokenize input
        inputs = tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=2048
        )

        # Move to same device as model
        if torch.cuda.is_available():
            inputs = {k: v.to(model.device) for k, v in inputs.items()}

        # Generate response
        with torch.no_grad():
            generation_config = GenerationConfig(
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=tokenizer.pad_token_id or tokenizer.eos_token_id
            )

            outputs = model.generate(
                **inputs,
                generation_config=generation_config
            )

        # Decode response
        full_response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract only the new generated text (remove the prompt)
        response = full_response[len(prompt):].strip()

        # Add assistant response to history
        self.conversation_histories[session_id].append({
            "role": "assistant",
            "content": response
        })

        return response

    def _format_conversation_simple(self, conversation: List[Dict[str, str]]) -> str:
        """
        Simple conversation formatting fallback.
        """
        formatted = []
        for msg in conversation:
            role = "Human" if msg["role"] == "user" else "Assistant"
            formatted.append(f"{role}: {msg['content']}")

        formatted.append("Assistant:")
        return "\n".join(formatted)

    def get_conversation_history(self, session_id: str) -> List[Dict[str, str]]:
        """Get conversation history for a session."""
        return self.conversation_histories.get(session_id, [])

    def clear_history(self, session_id: str) -> None:
        """Clear conversation history for a session."""
        if session_id in self.conversation_histories:
            self.conversation_histories[session_id] = []

    def unload_adapter(self, session_id: str) -> None:
        """Unload adapter and free memory."""
        if session_id in self.loaded_adapters:
            # Delete model to free memory
            del self.loaded_adapters[session_id]["model"]
            del self.loaded_adapters[session_id]["tokenizer"]
            del self.loaded_adapters[session_id]

        if session_id in self.conversation_histories:
            del self.conversation_histories[session_id]

        # Force garbage collection
        import gc
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
