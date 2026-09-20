from uuid import UUID, uuid4

class Stock:
    def __init__(self,id: UUID,symbol: str,name: str):
        self.id = id

        normalized_symbol = symbol.strip().upper()
        normalized_name = name.strip()

        if not normalized_symbol:
            raise ValueError("Stock symbol cannot be empty")

        if not normalized_name:
            raise ValueError("Stock name cannot be empty")

        self.symbol = normalized_symbol
        self.name = normalized_name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Stock):
            return NotImplemented

        return self.id == other.id

    @classmethod
    def reconstitute(cls, id:UUID, symbol: str, name: str):
        return cls(
                    id=id,
                    symbol=symbol,
                    name=name,
                )

    @classmethod
    def create(cls, symbol: str, name: str):
        return cls(id=uuid4(), symbol=symbol, name=name)