Pyhyves is een onofficiële Python-client voor de de API van Hyves (de nieuwe, uit 2026).

!!! warning "Waarschuwing"
    Volgens de gebruiksvoorwaarden van Mediahuis is "Het gebruik van software of enig geautomatiseerde tool (waaronder bots, crawlers of scrapers)om toegang te verkrijgen tot of informatie te verkrijgen uit de Uitgavenis uitdrukkelijk verboden" (op 9 oktober 2026). Je bent gewaarschuwd.

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

## Inloggen

Hyves heeft geen speciale bot-accounts, dus je logt in als een normale gebruiker:

- **Gebruikersnaam en wachtwoord:** doet de normale web app na om in te loggen.
- **Access token gekopieerd vanuit DevTools:** vervalt na een uur.

Pyhyves logt in zodra je je eerste request doet. Sommige endpoints werken ook zonder in te loggen, maar dat is momenteel alleen het aantal geregistreerde
gebruikers.

## Gebruik

De meeste objecten in deze library hebben drie varianten. Bijvoorbeeld voor een profiel:

- `Account`: volledig profiel met alle gegevens
- `AccountPreview`: gedeeltelijk profiel, door sommige endpoints meegegeven
- `AccountRef`: alleen een referentie naar een profiel, ook in sommige endpoints teruggegeven

Gebruik `.fetch()` om het hele object te krijgen of te verversen.

Alle errors vanuit de API worden een `HyvesAPIException`.