import copy

import torch
from torch import nn

import train


class _BatchLimitModel(nn.Module):
    def __init__(self):
        super().__init__()
        self.linear = nn.Linear(2, 3)

    def forward(self, x):
        if x.shape[0] > 2:
            raise RuntimeError("CUDA out of memory (simulated for retry test)")
        return self.linear(x)


def test_cuda_oom_falls_back_and_preserves_effective_batch(monkeypatch):
    torch.manual_seed(7)
    model = _BatchLimitModel()
    reference = copy.deepcopy(model)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.05)
    reference_optimizer = torch.optim.SGD(reference.parameters(), lr=0.05)
    criterion = nn.CrossEntropyLoss()
    scaler = train._grad_scaler(False)
    x = torch.randn(4, 2)
    y = torch.tensor([0, 1, 2, 1])

    original_to = torch.Tensor.to

    def keep_test_tensors_on_cpu(tensor, *args, **kwargs):
        if args and str(args[0]).startswith("cuda"):
            return tensor
        return original_to(tensor, *args, **kwargs)

    monkeypatch.setattr(torch.Tensor, "to", keep_test_tensors_on_cpu)
    loss_value, microbatch_size = train._train_accumulated_batch(
        model,
        x,
        y,
        "cuda",
        criterion,
        optimizer,
        scaler,
        False,
        [4, 2, 1],
    )

    reference_optimizer.zero_grad(set_to_none=True)
    criterion(reference.linear(x), y).backward()
    reference_optimizer.step()

    assert microbatch_size == 2
    assert loss_value > 0
    for actual, expected in zip(model.parameters(), reference.parameters()):
        torch.testing.assert_close(actual, expected, atol=1e-7, rtol=1e-6)
