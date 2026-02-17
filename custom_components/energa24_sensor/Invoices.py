from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, TypeVar, Callable, Type, cast
import dateutil.parser

T = TypeVar("T")


def from_str(x: Any) -> str:
    return str(x) if x is not None else ""


def from_datetime(x: Any) -> datetime:
    if x is None:
        return datetime.now()
    return dateutil.parser.parse(x)


def from_float(x: Any) -> float:
    if x is None:
        return 0.0
    return float(x)


def from_int(x: Any) -> int:
    if x is None:
        return 0
    return int(float(x)) 


def from_bool(x: Any) -> bool:
    return bool(x)


def from_none(x: Any) -> Any:
    return x


def to_float(x: Any) -> float:
    return x


def from_list(f: Callable[[Any], T], x: Any) -> List[T]:
    return [f(y) for y in x]


def to_class(c: Type[T], x: Any) -> dict:
    return cast(Any, x).to_dict()


@dataclass
class Invoices:
    number: str
    date: datetime
    sell_date: datetime
    gross_amount: float
    amount_to_pay: float
    wear: float
    wear_kwh: float
    paying_deadline_date: datetime
    start_date: datetime
    end_date: datetime
    is_paid: bool
    id_pp: str
    type: str
    status: str

    @staticmethod
    def from_dict(obj: Any) -> 'Invoices':
        assert isinstance(obj, dict)
        
        # New API Mapping
        number = from_str(obj.get("invoiceNumber"))
        date = from_datetime(obj.get("issueDate"))
        
        # PPES handling
        ppes = obj.get("ppes", [])
        first_ppe = ppes[0] if isinstance(ppes, list) and len(ppes) > 0 else {}
        
        # Dates from PPE or Invoice
        start_date = from_datetime(first_ppe.get("startDate")) if first_ppe.get("startDate") else date
        end_date = from_datetime(first_ppe.get("endDate")) if first_ppe.get("endDate") else date
        sell_date = end_date # Best guess for sell_date
        
        gross_amount = from_float(obj.get("invoiceAmount"))
        payment = from_float(obj.get("payment"))
        # If status is PAID, assume 0 to pay? 
        # sensor logic checks is_paid, so amount_to_pay is relevant when !is_paid.
        # We can just store the remaining amount.
        amount_to_pay = gross_amount - payment
        
        wear = from_float(first_ppe.get("consumption"))
        wear_kwh = from_float(first_ppe.get("consumption")) # Assuming unit is kWh as per example
        
        paying_deadline_date = from_datetime(obj.get("paymentDate"))
        
        status_str = obj.get("status", "")
        is_paid = status_str == "PAID"
        
        # id_pp -> dmsId
        id_pp = from_str(first_ppe.get("ppeNumber"))
        
        type_str = from_str(obj.get("documentType"))
        
        return Invoices(
            number=number,
            date=date,
            sell_date=sell_date,
            gross_amount=gross_amount,
            amount_to_pay=amount_to_pay,
            wear=wear,
            wear_kwh=wear_kwh,
            paying_deadline_date=paying_deadline_date,
            start_date=start_date,
            end_date=end_date,
            is_paid=is_paid,
            id_pp=id_pp,
            type=type_str,
            status=status_str
        )

    def to_dict(self) -> dict:
        # Simplified to_dict, mostly for consistency if needed
        result: dict = {
            "invoiceNumber": self.number,
            "issueDate": self.date.isoformat(),
            "invoiceAmount": self.gross_amount,
            "paymentDate": self.paying_deadline_date.isoformat(),
            "status": self.status,
            "dmsId": self.id_pp,
            "documentType": self.type
        }
        return result


@dataclass
class InvoicesList:
    invoices_list: List[Invoices]

    @staticmethod
    def from_dict(obj: Any) -> 'InvoicesList':
        data_list = []
        if isinstance(obj, list):
            data_list = obj
        invoices_list = from_list(Invoices.from_dict, data_list)
        
        return InvoicesList(invoices_list=invoices_list)

    def to_dict(self) -> dict:
        result: dict = {
            "InvoicesList": from_list(lambda x: to_class(Invoices, x), self.invoices_list)
        }
        return result


def invoices_from_dict(s: Any) -> InvoicesList:
    return InvoicesList.from_dict(s)


def invoices_to_dict(x: InvoicesList) -> Any:
    return to_class(InvoicesList, x)
