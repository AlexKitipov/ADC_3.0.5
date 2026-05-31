import importlib
import sys
import types


def test_pivot_env_imports_without_gymnasium_runtime_dependency(monkeypatch):
    fake_numpy = types.SimpleNamespace(
        inf=float("inf"),
        float32="float32",
        zeros=lambda shape, dtype=None: [0] * shape[0],
        array=lambda values, dtype=None: values,
    )
    monkeypatch.setitem(sys.modules, "numpy", fake_numpy)
    monkeypatch.delitem(sys.modules, "gymnasium", raising=False)
    monkeypatch.delitem(sys.modules, "gymnasium.spaces", raising=False)
    sys.modules.pop("app.services.pivot_env", None)

    pivot_env = importlib.import_module("app.services.pivot_env")
    env = pivot_env.PivotEnv(
        hist_df=None,
        gen_df=None,
        broker_api=None,
        order_manager=None,
    )

    assert env.action_space.n == 5
    assert env.observation_space.shape == (17,)
