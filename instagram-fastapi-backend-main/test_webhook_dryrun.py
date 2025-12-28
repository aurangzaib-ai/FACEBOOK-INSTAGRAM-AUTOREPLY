import asyncio
from services.webhook_service import process_instagram_comment

sample_payload = {
    "username": "test_user",
    "text": "Hi, I'm Maria. I want to buy a horno. My email is maria@example.com",
    "comment_id": "17899999999999999",
    "timestamp": "2025-11-21T12:00:00"
}

async def run_test():
    try:
        result = await process_instagram_comment(sample_payload, signature=None, raw_body=None, dry_run=True)
        print('Result:', result)
    except Exception as e:
        print('Error:', e)

if __name__ == '__main__':
    asyncio.run(run_test())
