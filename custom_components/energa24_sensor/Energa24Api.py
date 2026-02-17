import requests
from datetime import datetime, timedelta
from .EnergaAuth import EnergaAuth
from .PgpList import ppg_list_from_dict
from .PpgReadingForMeter import ppg_reading_for_meter_from_dict, PpgReadingForMeter, MeterReading
from .Invoices import invoices_from_dict, Invoices

DEVICES_LIST_URL = "https://24.energa.pl/api/dashboard"
READINGS_URL = "https://ebok.myorlen.pl/crm/get-all-ppg-readings-for-meter?pageSize=10&pageNumber=1&api-version=3.0&idPpg="
INVOICES_URL = "https://24.energa.pl/api/clients/{clientNumber}/accounts/{accountNumber}/invoices?page=0&size=10&localDateTo={now_date}&localDateFrom={from_date}"

class Energa24Api:

    def __init__(self, username, password) -> None:
        self.auth = EnergaAuth(username, password)

    def login(self):
        return self.auth.login()

    def meterList(self):
        token_type, token, key_cloak_id = self.auth.login()
        data = {"keycloakId": key_cloak_id['sub'], "email": key_cloak_id['email']}
        headers = self.auth.get_headers()
        return ppg_list_from_dict(requests.post(DEVICES_LIST_URL, headers=headers, json=data).json()['clients'][0]['invoiceProfile'][0])

    def readingForMeter(self, meter_id, account_number, client_number):
        invoices = self.invoices(account_number, client_number).invoices_list
        
        # Filter invoices for this meter (PPE) and sort by date descending
        meter_invoices = [i for i in invoices if i.id_pp == meter_id and i.end_date]
        if not meter_invoices:
             # Return empty structure if no data found, similar to previous mock but empty
            return PpgReadingForMeter(meter_readings=[], code=0, message=None, display_to_end_user=False, end_user_message=None, token_expire_date=datetime.now(), token_expire_date_utc=datetime.now())

        latest_invoice = max(meter_invoices, key=lambda x: x.end_date)
        
        val = latest_invoice.wear_kwh
        # Create a MeterReading object from the invoice data
        # Note: Some fields like 'value' (read index) might be missing or different in invoices. 
        # The sensor uses .value, so we need to map something meaningful there if possible, 
        # or at least mapped 'wear' which seems to be what user wants ("ile kwh zostało żużytych").
        # The 'value' field in MeterReading usually expects the counter state (index).
        # user said: "brał odczyt z ostatniej faktury ile kwh zostało żużytych" -> "items from last invoice how many kwh were used"
        # This maps to 'wear' (consumption).
        # Existing sensor accesses: .value (MeterReading.value) and .wear (MeterReading.wear)
        
        # We'll construct a MeterReading with the info we have.
        reading = MeterReading(
            status="INVOICE",
            reading_date_local=latest_invoice.end_date,
            reading_date_utc=latest_invoice.end_date, # Approximation
            pp_id=0, # Unknown from invoice, maybe not needed
            value=int(val), # Mapping consumption to value? Or should value be the index?
                            # The user request says "reading ... how many kwh were used". 
                            # If 'value' is index and 'wear' is consumption.
                            # The sensor code: `return max(readings, key=lambda z: z.reading_date_utc)`
                            # Then `state` property logic: `return self._state.value`
                            # But `extra_state_attributes` uses `self._state.wear`
                            # If user wants "how many kwh used" as the state, maybe I should put consumption in value?
                            # Use case: readingForMeter ... ile kwh zostało żużytych.
                            # I will put consumption in both 'wear' and 'value' to be safe for now, 
                            # or check if value is strictly index.
            value2=None,
            value3=None,
            meter_number=meter_id,
            region_code="",
            wear=int(val),
            type="INVOICE",
            color="black"
        )
        
        return PpgReadingForMeter(
            meter_readings=[reading],
            code=0,
            message=None,
            display_to_end_user=True,
            end_user_message=None,
            token_expire_date=datetime.now(),
            token_expire_date_utc=datetime.now()
        )

    def invoices(self, account_number, client_number):
        headers = self.auth.get_headers()
        now = datetime.now()
        now_date = now.strftime("%Y-%m-%d")
        from_date = (now - timedelta(days=180)).strftime("%Y-%m-%d")
        return invoices_from_dict(requests.get(INVOICES_URL.format(
            accountNumber=account_number,
            clientNumber=client_number,
            now_date=now_date,
            from_date=from_date
        ), headers=headers).json())
