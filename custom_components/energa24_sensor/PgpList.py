from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, TypeVar, Callable, Type, cast
import dateutil.parser


T = TypeVar("T")


def from_str(x: Any) -> str:
    if isinstance(x, str):
        return x
    return ""


def from_datetime(x: Any) -> datetime:
    return dateutil.parser.parse(x)


def from_bool(x: Any) -> bool:
    assert isinstance(x, bool)
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    return [f(y) for y in x]


def from_int(x: Any) -> int:
    assert isinstance(x, int) and not isinstance(x, bool)
    return x


def from_none(x: Any) -> Any:
    assert x is None
    return x


def to_class(c: Type[T], x: Any) -> dict:
    assert isinstance(x, c)
    return cast(Any, x).to_dict()


@dataclass
class PpgListElement:
    ppe_number: str
    collection_point_card: str
    mp_id_dms: str

    @staticmethod
    def from_dict(obj: Any) -> 'PpgListElement':
        assert isinstance(obj, dict)
        ppe_number = from_str(obj.get("ppeNumber"))
        collection_point_card = from_str(obj.get("collectionPointCard"))
        mp_id_dms = from_str(obj.get("mpIdDMS"))
        return PpgListElement(ppe_number, collection_point_card, mp_id_dms)

    def to_dict(self) -> dict:
        return {
            "ppeNumber": from_str(self.ppe_number),
            "collectionPointCard": from_str(self.collection_point_card), 
            "mpIdDMS": from_str(self.mp_id_dms)
        }


@dataclass
class PpgList:
    ppg_list: List[PpgListElement]
    account_number: str
    client_number: str

    @staticmethod
    def from_dict(obj: Any) -> 'PpgList':
        ppg_list = from_list(PpgListElement.from_dict, obj.get("ppes"))
        account_number = from_str(obj.get("accountNumber"))
        client_number = from_str(obj.get("clientNumber"))
        return PpgList(ppg_list, account_number, client_number)

    def to_dict(self) -> dict:
        return from_list(PpgListElement.to_dict, self.ppg_list)


def ppg_list_from_dict(s: Any) -> PpgList:
    return PpgList.from_dict(s)


def ppg_list_to_dict(x: PpgList) -> Any:
    return to_class(PpgList, x)
