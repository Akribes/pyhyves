# Pyhyves: Python-client voor Hyves

Dit is een onofficiële Python-client voor de de API van Hyves (de nieuwe, uit 2026).

> [!WARNING]  
> Volgens de gebruiksvoorwaarden van Mediahuis is "Het gebruik van software of enig geautomatiseerde tool (waaronder bots, crawlers of scrapers)om toegang te verkrijgen tot of informatie te verkrijgen uit de Uitgavenis uitdrukkelijk verboden" (op 9 oktober 2026). Je bent gewaarschuwd.

## Links
- [Documentatie](https://pyhyves.readthedocs.io/nl/latest/)
- [Hyves](https://hyves.nl/)

## Demo

```python
import asyncio
from pyhyves import PasswordCredentials, Pyhyves


async def main():
    credentials = PasswordCredentials(login_id="...", password="...")
    
    async with Pyhyves(credentials) as hyves:
        # Post een WieWatWaar
        await hyves.create_timeline_post(":dancing_banana:")
        
        account = await hyves.get_account(204)
        print(account.first_name)  # Hyves 
        
        # Lijsten worden in batches geladen
        async for group in hyves.get_client_groups():
            print(group.name)
            
            # Soms stuurt Hyves alleen een ID terug, gebruik fetch() voor het hele profiel
            owner = group.owner  # AccountRef
            print((await owner.fetch()).first_name)

asyncio.run(main())
```

## Installatie

Gebruik Python 3.12 of hoger.

```bash
pip install "pyhyves @ git+https://github.com/Akribes/pyhyves.git"
```

## Development

```bash
poetry install
make verify   # tests + mypy --strict + ruff
```