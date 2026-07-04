from __future__ import annotations

import os

from tinker_workbench.backends.base import Checkpoint, StepResult
from tinker_workbench.config import ExperimentConfig
from tinker_workbench.datasets import Example
from tinker_workbench.errors import BackendError


class TinkerBackend:
    """Adapter for the real Tinker training API.

    Maps the workbench backend contract onto the Tinker SDK's LoRA training
    client (forward_backward + optim_step futures, save_weights_for_sampler,
    sampling clients).

    Status: written against the public tinker-cookbook API surface but not yet
    exercised end-to-end — this machine has no TINKER_API_KEY. Every entry
    point fails fast with an actionable error rather than guessing.
    """

    name = "tinker"

    def __init__(self, config: ExperimentConfig) -> None:
        self.config = config
        self.run_id = "unbound"
        self._tinker = None
        self._service_client = None
        self._training_client = None
        self._tokenizer = None
        self._sampler_paths: dict[int, str] = {}

    def start(self, run_id: str, run_dir=None) -> None:
        if not os.environ.get("TINKER_API_KEY"):
            raise BackendError(
                "TINKER_API_KEY is not set. Export it (or run with --backend mock) "
                "before launching a real Tinker run."
            )
        try:
            import tinker
        except ImportError as error:
            raise BackendError(
                "The 'tinker' SDK is not installed. Install it with "
                "`pip install tinker` or run with --backend mock."
            ) from error

        self.run_id = run_id
        self._tinker = tinker
        self._service_client = tinker.ServiceClient()
        self._training_client = self._service_client.create_lora_training_client(
            base_model=self.config.model.base_model,
            rank=self.config.model.lora_rank,
        )
        self._tokenizer = self._training_client.get_tokenizer()

    def train_step(self, step: int, batch: list[Example], learning_rate: float) -> StepResult:
        self._require_started()
        types = self._tinker.types
        data = [self._datum(example) for example in batch]
        forward_future = self._training_client.forward_backward(data, loss_fn="cross_entropy")
        optim_future = self._training_client.optim_step(
            types.AdamParams(learning_rate=learning_rate)
        )
        forward_result = forward_future.result()
        optim_future.result()

        loss = _extract_mean_loss(forward_result)
        tokens = sum(
            len(self._encode(ex.prompt)) + len(self._encode(ex.completion)) for ex in batch
        )
        return StepResult(step=step, loss=loss, tokens=tokens, learning_rate=learning_rate)

    def save_checkpoint(self, step: int) -> Checkpoint:
        self._require_started()
        result = self._training_client.save_weights_for_sampler(
            name=f"{self.run_id}-step-{step:05d}"
        ).result()
        path = getattr(result, "path", None) or str(result)
        self._sampler_paths[step] = path
        return Checkpoint(step=step, path=path, sampler_ready=True)

    def sample(self, prompt: str, max_tokens: int, checkpoint: Checkpoint | None = None) -> str:
        self._require_started()
        if checkpoint is None:
            if not self._sampler_paths:
                raise BackendError("No sampler-ready checkpoint yet; save a checkpoint first.")
            path = self._sampler_paths[max(self._sampler_paths)]
        else:
            path = checkpoint.path

        types = self._tinker.types
        sampling_client = self._service_client.create_sampling_client(model_path=path)
        prompt_input = types.ModelInput.from_ints(tokens=self._encode(prompt))
        result = sampling_client.sample(
            prompt=prompt_input,
            num_samples=1,
            sampling_params=types.SamplingParams(max_tokens=max_tokens, temperature=0.0),
        ).result()
        tokens = result.sequences[0].tokens
        return self._tokenizer.decode(tokens)

    def close(self) -> None:
        self._training_client = None
        self._service_client = None

    def _datum(self, example: Example):
        types = self._tinker.types
        prompt_tokens = self._encode(example.prompt)
        completion_tokens = self._encode(example.completion)
        input_tokens = prompt_tokens + completion_tokens
        # Standard next-token setup: model_input is all tokens but the last,
        # targets are shifted by one, and prompt positions carry zero weight.
        weights = [0.0] * (len(prompt_tokens) - 1) + [1.0] * len(completion_tokens)
        return types.Datum(
            model_input=types.ModelInput.from_ints(tokens=input_tokens[:-1]),
            loss_fn_inputs={
                "weights": weights,
                "target_tokens": input_tokens[1:],
            },
        )

    def _encode(self, text: str) -> list[int]:
        return self._tokenizer.encode(text)

    def _require_started(self) -> None:
        if self._training_client is None:
            raise BackendError("TinkerBackend is not started. Call start() first.")


def _extract_mean_loss(forward_result) -> float:
    """Pull a scalar loss out of a forward_backward result defensively.

    The SDK result shape has shifted across releases; prefer the documented
    fields and fall back to NaN (which doctor will flag) over crashing a paid
    run at the metrics-recording step.
    """
    for attr in ("loss", "mean_loss"):
        value = getattr(forward_result, attr, None)
        if isinstance(value, (int, float)):
            return float(value)
    outputs = getattr(forward_result, "loss_fn_outputs", None)
    if outputs:
        losses = []
        for output in outputs:
            value = (
                output.get("loss") if isinstance(output, dict) else getattr(output, "loss", None)
            )
            if isinstance(value, (int, float)):
                losses.append(float(value))
        if losses:
            return sum(losses) / len(losses)
    return float("nan")
