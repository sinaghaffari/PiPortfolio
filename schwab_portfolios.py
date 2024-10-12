import json

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Self


class Node(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def to_dict(self):
        pass

    @classmethod
    def from_dict(cls, node_dict: dict) -> Self:
        if node_dict['type'] == 'EQUITY':
            return Equity.from_dict(node_dict)
        elif node_dict['type'] == 'PORTFOLIO':
            return Portfolio.from_dict(node_dict)
        else:
            raise ValueError("Invalid node type.")

    @abstractmethod
    def to_json(self) -> str:
        pass

    @classmethod
    def from_json(cls, json_node: str) -> Self:
        node_dict = json.loads(json_node)
        return cls.from_dict(node_dict)

    @abstractmethod
    def pretty(self, indent: int = 0) -> str:
        pass

    @abstractmethod
    def __getitem__(self, key: str) -> tuple[Self, float] | None:
        pass

    @abstractmethod
    def __truediv__(self, key: str) -> tuple[Self, float] | None:
        pass


class Equity(Node):
    ticker: str
    name: str = None

    def __init__(self, *, ticker: str):
        self.name = ticker
        self.ticker = ticker

    def to_dict(self):
        return {'type':'EQUITY', 'ticker':self.ticker, }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, equity_dict: dict):
        assert equity_dict['type'] == 'EQUITY'
        return Equity(ticker=equity_dict['ticker'])

    @classmethod
    def from_json(cls, json_equity: str) -> Self:
        equity_dict = json.loads(json_equity)
        return cls.from_dict(equity_dict)

    def pretty(self, indent: int = 0) -> str:
        return f"{'  ' * indent}{repr(self)}"

    def __repr__(self):
        return f"Equity(ticker='{self.ticker}')"

    def __getitem__(self, key: str) -> tuple[Node, float] | None:
        raise Exception("Can't slice equity.")

    def __truediv__(self, key: str) -> tuple[Self, float] | None:
        raise Exception("Can't slice equity.")


class Portfolio(Node):
    name: str = None
    children: dict[Node, Decimal]
    _children_by_name: dict[str, tuple[Node, Decimal]]

    def __init__(self, *, name: str, children: dict[Node, str]):
        self.name = name
        self.children = {k:Decimal(v) for k, v in children.items()}
        self._children_by_name = {node.name:(node, pct) for node, pct in self.children.items()}

        assert sum(val for val in self.children.values()) == 1
        child_names = [child.name for child in self.children.keys()]
        assert len(child_names) == len(set(child_names))

    def to_dict(self):
        return {
            'type':"PORTFOLIO",
            'name':self.name,
            'children':[[child.to_dict(), str(pct)] for child, pct in self.children.items()]
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, node_dict: dict) -> Self:
        assert node_dict['type'] == "PORTFOLIO"
        return Portfolio(
            name=node_dict['name'],
            children={Node.from_dict(child):pct for child, pct in node_dict['children']}
        )

    @classmethod
    def from_json(cls, json_node: str) -> Self:
        node_dict = json.loads(json_node)
        return cls.from_dict(node_dict)

    def all_equities(self) -> set[Equity]:
        result = set()
        for child in self.children.keys():
            if isinstance(child, Equity):
                result.add(child)
            elif isinstance(child, Portfolio):
                result = result.union(child.all_equities())
        return result

    def flatten(self) -> dict[str, Decimal]:
        result = {}
        for node, pct in self.children.items():
            if isinstance(node, Portfolio):
                flattened_child = node.flatten()
                for path, child_pct in flattened_child.items():
                    result[f"{self.name}/{path}"] = pct * child_pct
            elif isinstance(node, Equity):
                result[f"{self.name}/{node.ticker}"] = pct
        return result

    def pretty(self, indent: int = 0) -> str:
        children = [f"{node.pretty(indent + 2)}: {pct}" for node, pct in self.children.items()]
        return (
            f"{'  ' * indent}Portfolio(\n"
            f"{'  ' * (indent + 1)}""name='{self.name}',\n"
            f"{'  ' * (indent + 1)}children={{\n{'\n'.join(children)}\n"
            f"{'  ' * (indent + 1)}}})"
        )

    def __truediv__(self, key: str) -> Node | None:
        child = self._children_by_name.get(key, None)
        return child and child[0]

    def __getitem__(self, key: str) -> tuple[Node, float] | None:
        return self._children_by_name.get(key, None)

    def __repr__(self):
        return f"Portfolio(name='{self.name}', children={repr(self.children)})"

    def __hash__(self):
        return hash((self.name, *self.children.items()))
