"""
Manually marks an existing account as email-verified.

Use this if you don't have email sending set up yet, but need to unblock
an account that's stuck waiting for verification.

Run with: python -m app.services.verify_my_account
You'll be asked for the email address to verify.
"""
import asyncio

from app.database import database


async def main():
    database.connect()

    email = input("Email address to verify: ").strip()
    user = await database.users.find_one({"email": email})

    if not user:
        print(f"No account found with email: {email}")
        database.close()
        return

    await database.users.update_one(
        {"email": email},
        {"$set": {"email_verified": True, "verification_token": None}},
    )
    print(f"Done -- {email} is now verified and can sign in.")

    database.close()


if __name__ == "__main__":
    asyncio.run(main())
