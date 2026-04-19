from src.services.tool_registry import ToolRegistry, register_tool, get_tool_registry, get_tool, get_tools


def test_register_and_get():
    registry = ToolRegistry()

    def my_tool(x: int) -> int:
        return x + 1

    registry.register("my_tool", my_tool)
    assert registry.get("my_tool") is my_tool


def test_register_duplicate_raises():
    registry = ToolRegistry()

    def tool_a():
        pass

    registry.register("dup", tool_a)
    try:
        registry.register("dup", tool_a)
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "dup" in str(e)


def test_get_missing_returns_none():
    registry = ToolRegistry()
    assert registry.get("nonexistent") is None


def test_get_tool_raises_on_missing():
    registry = ToolRegistry()
    try:
        registry.get_tool("nonexistent")
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "nonexistent" in str(e)


def test_get_tools_returns_list():
    registry = ToolRegistry()

    def t1():
        pass

    def t2():
        pass

    registry.register("t1", t1)
    registry.register("t2", t2)
    result = registry.get_tools(["t1", "t2"])
    assert len(result) == 2
    assert result[0] is t1
    assert result[1] is t2


def test_get_tools_raises_on_missing():
    registry = ToolRegistry()

    def t1():
        pass

    registry.register("t1", t1)
    try:
        registry.get_tools(["t1", "missing"])
        assert False, "Expected ValueError"
    except ValueError as e:
        assert "missing" in str(e)


def test_contains():
    registry = ToolRegistry()

    def t1():
        pass

    registry.register("t1", t1)
    assert "t1" in registry
    assert "t2" not in registry


def test_names():
    registry = ToolRegistry()

    def b():
        pass

    def a():
        pass

    registry.register("beta", b)
    registry.register("alpha", a)
    assert registry.names() == ("alpha", "beta")


def test_clear():
    registry = ToolRegistry()

    def t():
        pass

    registry.register("t", t)
    assert "t" in registry
    registry.clear()
    assert "t" not in registry


def test_register_tool_decorator():
    @register_tool("decorated_tool", registry=ToolRegistry())
    def my_fn():
        return 42

    assert my_fn() == 42


def test_default_registry_is_shared():
    from src.services.tool_registry import _default_registry

    assert get_tool_registry() is _default_registry
