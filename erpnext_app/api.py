import frappe
import requests


@frappe.whitelist()
def verify_payment_otp(
    phone,
    otp,
    purchase_invoice=None,
    bank_account=None,
    receiver=None,
    amount=None,
    payment_type=None,
    unique_id=None
):

    url = (
        "http://integ.local:8000/"
        "api/method/integ_app.api.validate_otp"
    )

    headers = {
        "Authorization": "token cbdf2692bd670b0:3752219d3d08b14"
    }
    frappe.msgprint(receiver)
    response = requests.post(
        url,
        headers=headers,
        data={
            "phone": phone,
            "otp": otp,
            "purchase_invoice": purchase_invoice,
            "bank_account": bank_account,
            "receiver_no": receiver,
            "amount": amount,
            "payment_type": payment_type,
            "unique_id":unique_id
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