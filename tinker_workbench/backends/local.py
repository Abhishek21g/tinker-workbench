from __future__ import annotations

from pathlib import Path

from tinker_workbench.backends.base import Checkpoint, StepResult
from tinker_workbench.config import ExperimentConfig
from tinker_workbench.datasets import Example, load_train_examples
from tinker_workbench.errors import BackendError

BOS = "\x00"
EOS = "\x01"


class LocalBackend:
    """Trains a real (tiny) neural language model locally, for free.

    This is not a simulation: a character-level MLP language model (Bengio
    2003 style — embedding, tanh hidden layer, softmax) is trained with
    hand-derived gradients and Adam. Loss falls because the model actually
    learns; too-high learning rates genuinely diverge; the memorization evals
    improve because the weights really store the strings. Checkpoints are
    real weight files on disk.

    The point: the entire Workbench pipeline (plan/run/doctor/evals/drift)
    exercises true training dynamics with zero spend, and swapping
    `mode: local` for `mode: tinker` is the only change needed to drive the
    real Tinker API.
    """

    name = "local"

    def __init__(self, config: ExperimentConfig) -> None:
        try:
            import numpy
        except ImportError as error:
            raise BackendError(
                "The local backend requires numpy: pip install numpy"
            ) from error
        if config.training.method != "sft":
            raise BackendError(
                "The local backend implements real supervised training only; "
                f"use method 'sft' (got {config.training.method!r}) or mode 'mock' "
                "for RL-shaped simulations."
            )
        self._np = numpy
        self.config = config
        self.run_id = "unbound"
        self._checkpoint_dir: Path | None = None
        local = config.local
        self.context_window = local.context_window
        self.embedding_dim = local.embedding_dim
        self.hidden_dim = local.hidden_dim

        # Vocabulary is fixed up front from the training set so encoding is
        # stable across steps, checkpoints, and resumed samplers.
        examples = load_train_examples(config.data, config.training.seed)
        chars = sorted({ch for ex in examples for ch in ex.prompt + ex.completion})
        self._vocab = [BOS, EOS, *chars]
        self._index = {ch: i for i, ch in enumerate(self._vocab)}

        rng = numpy.random.RandomState(config.training.seed)
        v, c, e, h = len(self._vocab), self.context_window, self.embedding_dim, self.hidden_dim
        self._params = {
            "emb": rng.normal(0.0, 0.1, (v, e)),
            "w1": rng.normal(0.0, 1.0 / (c * e) ** 0.5, (c * e, h)),
            "b1": numpy.zeros(h),
            "w2": rng.normal(0.0, 1.0 / h**0.5, (h, v)),
            "b2": numpy.zeros(v),
        }
        self._adam_m = {k: numpy.zeros_like(p) for k, p in self._params.items()}
        self._adam_v = {k: numpy.zeros_like(p) for k, p in self._params.items()}
        self._adam_t = 0

    def start(self, run_id: str, run_dir: Path | None = None) -> None:
        self.run_id = run_id
        if run_dir is not None:
            self._checkpoint_dir = run_dir / "checkpoints"
            self._checkpoint_dir.mkdir(parents=True, exist_ok=True)

    def train_step(self, step: int, batch: list[Example], learning_rate: float) -> StepResult:
        contexts, targets = self._training_pairs(batch)
        loss, grads = self._loss_and_grads(contexts, targets)
        self._adam_step(grads, learning_rate)
        return StepResult(
            step=step,
            loss=float(loss),
            tokens=int(len(targets)),
            learning_rate=learning_rate,
        )

    def save_checkpoint(self, step: int) -> Checkpoint:
        if self._checkpoint_dir is None:
            raise BackendError("LocalBackend is not started; no checkpoint directory.")
        path = self._checkpoint_dir / f"step-{step:05d}.npz"
        self._np.savez(
            path,
            vocab="".join(self._vocab),
            **self._params,
        )
        return Checkpoint(step=step, path=str(path), sampler_ready=True)

    def sample(self, prompt: str, max_tokens: int, checkpoint: Checkpoint | None = None) -> str:
        params = self._params
        if checkpoint is not None:
            loaded = self._np.load(checkpoint.path)
            params = {k: loaded[k] for k in ("emb", "w1", "b1", "w2", "b2")}

        context = [self._index[BOS]] * self.context_window
        for ch in prompt:
            context = context[1:] + [self._index.get(ch, self._index[BOS])]

        output: list[str] = []
        for _ in range(max_tokens):
            logits = self._forward(self._np.array([context]), params)[0][0]
            next_index = int(logits.argmax())
            if self._vocab[next_index] == EOS:
                break
            output.append(self._vocab[next_index])
            context = context[1:] + [next_index]
        return "".join(output)

    def close(self) -> None:
        pass

    # --- model internals -------------------------------------------------

    def _training_pairs(self, batch: list[Example]):
        """Sliding-window next-char pairs; loss only on completion chars.

        Mirrors the real SFT setup: prompt positions get zero weight, the
        model is graded on producing the completion (plus EOS) given the
        prompt.
        """
        np = self._np
        contexts = []
        targets = []
        for example in batch:
            sequence = [self._index[BOS]] * self.context_window
            for ch in example.prompt:
                sequence.append(self._index.get(ch, self._index[BOS]))
            completion = [self._index[ch] for ch in example.completion]
            completion.append(self._index[EOS])
            for target in completion:
                contexts.append(sequence[-self.context_window :])
                targets.append(target)
                sequence.append(target)
        return np.array(contexts), np.array(targets)

    def _forward(self, contexts, params):
        np = self._np
        embedded = params["emb"][contexts].reshape(contexts.shape[0], -1)
        pre_hidden = embedded @ params["w1"] + params["b1"]
        hidden = np.tanh(pre_hidden)
        logits = hidden @ params["w2"] + params["b2"]
        return logits, (embedded, hidden)

    def _loss_and_grads(self, contexts, targets):
        np = self._np
        n = contexts.shape[0]
        logits, (embedded, hidden) = self._forward(contexts, self._params)

        shifted = logits - logits.max(axis=1, keepdims=True)
        exp = np.exp(shifted)
        probs = exp / exp.sum(axis=1, keepdims=True)
        loss = -np.log(probs[np.arange(n), targets] + 1e-12).mean()

        dlogits = probs
        dlogits[np.arange(n), targets] -= 1.0
        dlogits /= n

        grads = {}
        grads["w2"] = hidden.T @ dlogits
        grads["b2"] = dlogits.sum(axis=0)
        dhidden = dlogits @ self._params["w2"].T
        dpre = dhidden * (1.0 - hidden**2)
        grads["w1"] = embedded.T @ dpre
        grads["b1"] = dpre.sum(axis=0)
        dembedded = (dpre @ self._params["w1"].T).reshape(
            n, self.context_window, self.embedding_dim
        )
        grads["emb"] = np.zeros_like(self._params["emb"])
        np.add.at(grads["emb"], contexts, dembedded)
        return loss, grads

    def _adam_step(self, grads, learning_rate: float) -> None:
        np = self._np
        beta1, beta2, eps = 0.9, 0.999, 1e-8
        self._adam_t += 1
        for key, grad in grads.items():
            self._adam_m[key] = beta1 * self._adam_m[key] + (1 - beta1) * grad
            self._adam_v[key] = beta2 * self._adam_v[key] + (1 - beta2) * grad**2
            m_hat = self._adam_m[key] / (1 - beta1**self._adam_t)
            v_hat = self._adam_v[key] / (1 - beta2**self._adam_t)
            self._params[key] -= learning_rate * m_hat / (np.sqrt(v_hat) + eps)
