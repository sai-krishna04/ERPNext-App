

import frappe
import requests
import uuid
@frappe.whitelist()
def verify_payment_otp(phone, otp,purchase_invoice=None,
    bank_account=None,
    amount=None,reciever=None):

    url = "http://integ.local:8000/api/method/integ_app.api.validate_otp"

    headers = {
        "Authorization": "token cbdf2692bd670b0:3752219d3d08b14"
    }

    response = requests.post(
        url,
        headers=headers,
        data={
            "phone": phone,
            "otp": otp,
            "purchase_invoice": purchase_invoice,
            "bank_account": bank_account,
            "amount": amount,
            "reciever":reciever
        },
        timeout=10
    )

    if response.status_code != 200:
        return {
            "success": False,
            "message": "OTP service unavailable"
        }

    result = response.json()

    return result.get("message")

