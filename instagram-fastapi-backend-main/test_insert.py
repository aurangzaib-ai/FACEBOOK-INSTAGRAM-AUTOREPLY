from utils.google_sheets import append_lead_to_sheet

append_lead_to_sheet({
    "platform": "instagram",
    "user_handle": "demo_user_01",
    "message_text": "Hola, quiero comprar ahora",
    "intent_group": "buying_intent",
    "lead_score": 85,
    "priority_level": "hot",
    "contact_status": "pending",
    "name": "Juan Demo",
    "email": "juan.demo@gmail.com",
    "phone": "+34123456789",
})
