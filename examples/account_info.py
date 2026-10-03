import asyncio
import logging
import os

from pyhyves import Pyhyves, PasswordCredentials

USER_EMAIL = os.environ["HYVES_USER"]
USER_PASSWORD = os.environ["HYVES_PASS"]


async def main():
    pyhyves = Pyhyves(
        credentials=PasswordCredentials(login_id=USER_EMAIL, password=USER_PASSWORD)
    )
    me = await pyhyves.current_user()

    full_name = " ".join(x for x in [me.firstName, me.middleName, me.lastName] if x)
    print(
        f"Logged in as {me.name}\n"
        f"Name: {full_name}\n"
        f"Email: {me.email}\n"
    )


logging.basicConfig(level=logging.INFO)
if __name__ == "__main__":
    asyncio.run(main())
