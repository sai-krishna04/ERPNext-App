import frappe
import requests

from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

@frappe.whitelist()
def verify_payment_otp(
    phone,
    otp,
    purchase_invoice=None,
    bank_account=None,
    receiver_no=None,
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

    try:

        response = requests.post(
            url,
            headers=headers,
            data={
                "phone": phone,
                "otp": otp,
                "purchase_invoice": purchase_invoice,
                "bank_account": bank_account,
                "receiver_no": receiver_no,
                "amount": amount,
                "payment_type": payment_type,
                "unique_id": unique_id
            },
            timeout=30
        )

    except requests.RequestException as e:

        return {
            "success": False,
            "message": str(e)
        }

    if response.status_code != 200:

        return {
            "success": False,
            "message": response.text
        }

    result = response.json()

    return result.get("message", result)
@frappe.whitelist()
def generate_payment_otp(phone):

    url = (
        "http://integ.local:8000/"
        "api/method/integ_app.api.generate_otp"
    )

    headers = {
        "Authorization": "token cbdf2692bd670b0:3752219d3d08b14"
    }

    response = requests.post(
        url,
        headers=headers,
        data={
            "phone": phone
        },
        timeout=10
    )

    if response.status_code != 200:
        return {
            "success": False,
            "message": "OTP service unavailable"
        }

    return response.json().get("message")

def check_pending_payments():

    invoices = frappe.get_all(
        "Purchase Invoice",
        fields=["name"]
    )

    for invoice in invoices:

        invoice_doc = frappe.get_doc(
            "Purchase Invoice",
            invoice.name
        )

        changed = False

        for transaction in invoice_doc.custom_payment_trans:

            print(transaction.custom_payment_status)

            if transaction.custom_payment_status != "Pending":
                continue

            if not transaction.unique_id:
                continue

            try:

                url = (
                    "http://integ.local:8000/"
                    "api/method/integ_app.api.get_payment_status"
                )

                headers = {
                    "Authorization":
                    "token cbdf2692bd670b0:3752219d3d08b14"
                }

                response = requests.post(
                    url,
                    headers=headers,
                    data={
                        "unique_id":
                        transaction.unique_id
                    },
                    timeout=10
                )

                if response.status_code != 200:
                    continue

                result = response.json().get(
                    "message"
                )

                if not result:
                    continue

                payment_status = result.get(
                    "payment_status"
                )

                frappe.log_error(
                    frappe.as_json({
                        "invoice":
                        invoice_doc.name,
                        "unique_id":
                        transaction.unique_id,
                        "bank_status":
                        payment_status
                    }),
                    "Payment Status Check"
                )

                if payment_status == "COMPLETED":

                    frappe.db.set_value(
                        transaction.doctype,
                        transaction.name,
                        "custom_payment_status",
                        "Paid"
                    )

                    frappe.db.commit()

                    frappe.log_error(
                        f"Marked {transaction.unique_id} as Paid",
                        "Payment Status Updated"
                    )

                    try:

                        payment_entry_name = create_payment_entry_for_invoice(
                            invoice_id=invoice_doc.name,
                            transaction_id=transaction.unique_id,
                            amount=transaction.amount,
                            sender_account=transaction.custom_bank_sender,
                            mode_of_payment=transaction.custom_payment_type
                        )

                        frappe.log_error(
                            f"Payment Entry created: {payment_entry_name}",
                            "Payment Entry Success"
                        )

                    except Exception:

                        frappe.log_error(
                            frappe.get_traceback(),
                            "Payment Entry Creation Error"
                        )
                elif payment_status == "FAILED":

                    transaction.custom_payment_status = "Failed"

                    changed = True

            except Exception:

                frappe.log_error(
                    frappe.get_traceback(),
                    "Payment Status Scheduler"
                )

        if changed:

            invoice_doc.save(
                ignore_permissions=True
            )

            frappe.db.commit()

def create_payment_entry_for_invoice(
    invoice_id,
    transaction_id,
    amount,
    sender_account,
    mode_of_payment=None
):

    invoice = frappe.get_doc(
        "Purchase Invoice",
        invoice_id
    )

    if invoice.docstatus != 1:
        frappe.throw(
            "Purchase Invoice must be submitted."
        )

    existing_entry = frappe.db.get_value(
        "Payment Entry",
        {
            "reference_no": transaction_id
        },
        "name"
    )

    if existing_entry:
        return existing_entry

    bank_account_doc = frappe.get_doc(
        "Bank Account",
        sender_account
    )

    bank_gl_account = bank_account_doc.account

    payment_entry = get_payment_entry(
        "Purchase Invoice",
        invoice_id,
        party_amount=amount,
        bank_account=bank_gl_account,
        bank_amount=amount
    )

    payment_entry.paid_from = bank_gl_account

    if mode_of_payment:
        payment_entry.mode_of_payment = mode_of_payment

    payment_entry.reference_no = transaction_id
    payment_entry.reference_date = frappe.utils.today()

    payment_entry.insert(
        ignore_permissions=True
    )

    payment_entry.submit()
    frappe.db.commit()

    return payment_entry.name