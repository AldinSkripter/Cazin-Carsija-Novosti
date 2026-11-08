"""Upisuje pravne i informativne stranice portala. Pokretanje: python legal_pages.py"""
import asyncio
import os

from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

NAME = "Cazin Čaršija Novosti (CČN)"
OWNER = "Arif Civić"
EMAIL = "portalcazin@gmail.com"
PHONE = "+387 61 524 552"
WEB = "cazin-carsija.ba"
UPDATED = "8. novembra 2026."
MAIL = f'<a href="mailto:{EMAIL}">{EMAIL}</a>'
TEL = f'<a href="tel:+38761524552">{PHONE}</a>'

PAGES = {
    "impresum": ("Impresum", "Impresum portala Cazin Čaršija Novosti – izdavač, glavni urednik i kontakt.", f"""
<h2>Osnovni podaci</h2>
<ul>
<li><strong>Naziv medija:</strong> {NAME}</li>
<li><strong>Internet adresa:</strong> https://{WEB}</li>
<li><strong>Vrsta medija:</strong> informativni internetski portal</li>
<li><strong>Osnivač i izdavač:</strong> {OWNER}, Cazin, Bosna i Hercegovina</li>
<li><strong>Glavni i odgovorni urednik:</strong> {OWNER}</li>
<li><strong>Sjedište redakcije:</strong> Cazin, Unsko-sanski kanton, Bosna i Hercegovina</li>
</ul>
<h2>Kontakt</h2>
<ul>
<li><strong>Redakcija:</strong> {MAIL}</li>
<li><strong>Telefon:</strong> {TEL}</li>
<li><strong>Marketing i oglašavanje:</strong> {MAIL}</li>
<li><strong>Prijava vijesti:</strong> <a href="/prijavite-vijest">obrazac za prijavu vijesti</a></li>
</ul>
<h2>Uređivačka odgovornost</h2>
<p>Za sadržaj objavljen na portalu odgovoran je glavni i odgovorni urednik. Autorski tekstovi potpisani su imenom autora. Komentari čitalaca izražavaju isključivo mišljenje njihovih autora.</p>
<p>U radu se pridržavamo načela Kodeksa za štampu i online medije Bosne i Hercegovine. Pritužbe na sadržaj možete uputiti redakciji na {MAIL}, a čitaoci se mogu obratiti i Vijeću za štampu i online medije u BiH.</p>
<h2>Autorska prava</h2>
<p>Sav sadržaj portala zaštićen je autorskim pravom. Preuzimanje je dozvoljeno samo uz uvjete navedene u <a href="/stranica/uslovi-koristenja">Uslovima korištenja</a>: obavezno navođenje imena autora i aktivan link na izvorni članak.</p>
"""),

    "politika-privatnosti": ("Politika privatnosti", "Kako portal Cazin Čaršija Novosti prikuplja, koristi i štiti lične podatke.", f"""
<p><em>Posljednja izmjena: {UPDATED}</em></p>
<p>Ova politika objašnjava koje lične podatke prikupljamo kada koristite portal {NAME}, zašto ih koristimo i koja prava imate. Podatke obrađujemo u skladu s važećim Zakonom o zaštiti ličnih podataka Bosne i Hercegovine, a za posjetioce iz Evropske unije i u skladu s Općom uredbom o zaštiti podataka (GDPR).</p>
<h2>1. Ko je odgovoran za vaše podatke</h2>
<p>Kontrolor podataka je {OWNER}, Cazin, Bosna i Hercegovina. Kontakt: {MAIL}, {TEL}.</p>
<h2>2. Koje podatke prikupljamo i zašto</h2>
<ul>
<li><strong>Čitanje portala:</strong> ne tražimo nikakve lične podatke. Za statistiku čitanosti bilježimo anonimni identifikator preglednika, stranicu koju ste otvorili, stranicu s koje ste došli i vrstu uređaja (mobitel ili računar). Iz tih podataka ne možemo utvrditi vaš identitet.</li>
<li><strong>Newsletter:</strong> e-mail adresu, izabranu učestalost (dnevni ili sedmični pregled), vrijeme i potvrdu pristanka. Osnov obrade je vaš pristanak, koji potvrđujete klikom na link u e-mailu.</li>
<li><strong>Komentari:</strong> ime ili nadimak, e-mail adresu (ne objavljuje se) i tekst komentara. Koristimo ih za objavu i moderaciju komentara i sprečavanje zloupotrebe.</li>
<li><strong>Prijava vijesti:</strong> ime, kontakt koji ostavite, opis događaja i priložene fotografije ili video. Koristimo ih isključivo za provjeru i eventualnu objavu vijesti, uz vaš izričit pristanak.</li>
<li><strong>Zahtjevi za privatnost i kontakt:</strong> e-mail adresu i sadržaj poruke, kako bismo vam odgovorili.</li>
</ul>
<p>Radi zaštite od zloupotrebe (npr. spama u komentarima) IP adresu ne čuvamo u izvornom obliku, nego samo kao jednosmjerni šifrovani zapis (hash).</p>
<h2>3. Kolačići i lokalna pohrana</h2>
<p>Detalje o tome šta se pohranjuje u vašem pregledniku pročitajte u <a href="/stranica/politika-kolacica">Politici kolačića</a>. Analitičke alate trećih strana (npr. Google Analytics) učitavamo samo ako za to date pristanak u obavijesti o kolačićima.</p>
<h2>4. S kim dijelimo podatke</h2>
<p>Vaše podatke ne prodajemo i ne ustupamo oglašivačima. Portal i baza podataka nalaze se na našem vlastitom serveru, a e-mailove šaljemo s vlastitog poslužitelja pošte. Podatke možemo dati nadležnim organima samo kada to zakon izričito nalaže.</p>
<p>Slike s kamera na graničnim prijelazima i vremenska prognoza preuzimaju se preko našeg servera, tako da vaš preglednik ne komunicira direktno s tim izvorima. Ugrađeni YouTube video sadržaji koriste način rada s pojačanom privatnošću (youtube-nocookie.com).</p>
<h2>5. Koliko dugo čuvamo podatke</h2>
<ul>
<li>Newsletter: do odjave. Link za odjavu nalazi se u svakom e-mailu.</li>
<li>Komentari: dok je članak objavljen ili do vašeg zahtjeva za brisanje.</li>
<li>Prijave vijesti i poruke: koliko je potrebno za njihovu obradu, nakon čega ih na zahtjev brišemo.</li>
<li>Anonimna statistika: bez vremenskog ograničenja, jer ne sadrži lične podatke.</li>
</ul>
<h2>6. Vaša prava</h2>
<p>Imate pravo da zatražite pristup svojim podacima, njihovu ispravku ili brisanje, ograničenje obrade, te da u svakom trenutku povučete dati pristanak. Zahtjev možete poslati na {MAIL} ili putem obrasca na dnu ove stranice. Odgovaramo u najkraćem mogućem roku, a najkasnije u roku od 30 dana.</p>
<p>Ako smatrate da su vaša prava povrijeđena, možete se obratiti Agenciji za zaštitu ličnih podataka u Bosni i Hercegovini.</p>
<h2>7. Sigurnost</h2>
<p>Portal koristi šifrovanu vezu (HTTPS). Pristup bazi i administraciji imaju samo ovlaštene osobe redakcije, uz zaštićene lozinke.</p>
<h2>8. Izmjene politike</h2>
<p>Ovu politiku možemo povremeno izmijeniti. Važeća verzija uvijek je objavljena na ovoj stranici, s datumom posljednje izmjene.</p>
"""),

    "politika-kolacica": ("Politika kolačića", "Koje kolačiće i lokalnu pohranu koristi portal Cazin Čaršija Novosti.", f"""
<p><em>Posljednja izmjena: {UPDATED}</em></p>
<p>Kolačići (cookies) i lokalna pohrana su mali zapisi koje stranica sprema u vaš preglednik. Portal {NAME} koristi ih minimalno i isključivo za rad stranice i anonimnu statistiku.</p>
<h2>Neophodni zapisi (uvijek aktivni)</h2>
<ul>
<li><strong>ccn_consent</strong> – pamti vaš izbor u obavijesti o kolačićima.</li>
<li><strong>ccn_theme</strong> – pamti da li ste izabrali svijetli ili tamni izgled portala.</li>
<li><strong>ccn_vid</strong> i <strong>ccn_sid</strong> – anonimni nasumični identifikatori za brojanje čitanosti članaka. Ne sadrže lične podatke.</li>
<li><strong>access_token</strong> i <strong>refresh_token</strong> – samo za članove redakcije prijavljene u administraciju. Čitaoci ih ne dobijaju.</li>
</ul>
<h2>Analitički kolačići (samo uz pristanak)</h2>
<p>Ako redakcija uključi Google Analytics, on se učitava samo kada u obavijesti kliknete „Prihvati sve“. Tada Google postavlja svoje kolačiće (npr. <strong>_ga</strong>), uz anonimizaciju IP adrese. Isto vrijedi i za Plausible statistiku, koja ne koristi kolačiće.</p>
<h2>Sadržaj trećih strana</h2>
<p>Ugrađeni YouTube video koristi youtube-nocookie.com i ne postavlja kolačiće dok video ne pokrenete.</p>
<h2>Kako promijeniti izbor</h2>
<p>Izbor možete promijeniti u svakom trenutku klikom na „Postavke kolačića“ u dnu stranice ili brisanjem podataka stranice u postavkama preglednika.</p>
"""),

    "uslovi-koristenja": ("Uslovi korištenja", "Pravila korištenja i preuzimanja sadržaja portala Cazin Čaršija Novosti.", f"""
<p><em>Posljednja izmjena: {UPDATED}</em></p>
<p>Korištenjem portala {NAME} (https://{WEB}) prihvatate ove uslove.</p>
<h2>1. Autorska prava</h2>
<p>Tekstovi, fotografije, video i grafike objavljeni na portalu zaštićeni su autorskim pravom i vlasništvo su portala ili autora, osim ako je drugačije navedeno.</p>
<h2>2. Preuzimanje sadržaja</h2>
<p>Dozvoljeno je preuzimanje i dijeljenje naših sadržaja na drugim portalima, društvenim mrežama i u medijima, <strong>isključivo uz ispunjenje sljedećih uvjeta</strong>:</p>
<ul>
<li><strong>obavezno navođenje imena autora</strong> tačno onako kako je potpisan na našem portalu,</li>
<li><strong>obavezan aktivan (klikabilan) link na izvorni članak</strong> na {WEB}, vidljivo postavljen uz preuzeti sadržaj,</li>
<li>navođenje naziva izvora: „Cazin Čaršija Novosti“ ili „CČN“,</li>
<li>sadržaj se ne smije mijenjati na način koji iskrivljuje smisao ili kontekst.</li>
</ul>
<p>Preuzimanje bez navođenja autora i linka na izvor nije dozvoljeno i smatra se povredom autorskih prava. Fotografije i sadržaji koji su na portalu označeni kao vlasništvo agencija ili trećih osoba ne smiju se preuzimati bez njihove dozvole. Zabranjeno je automatsko masovno preuzimanje sadržaja (scraping) i njegovo korištenje u komercijalne svrhe bez pismenog dogovora s redakcijom.</p>
<p>Dijeljenje linkova na naše članke putem društvenih mreža i aplikacija za dopisivanje je slobodno i dobrodošlo.</p>
<h2>3. Komentari</h2>
<p>Komentari izražavaju mišljenje njihovih autora, a ne redakcije. Zabranjeni su govor mržnje, prijetnje, vrijeđanje, kleveta, spam i objavljivanje tuđih ličnih podataka. Redakcija zadržava pravo da takve komentare ukloni i blokira autora.</p>
<h2>4. Prijava vijesti</h2>
<p>Slanjem vijesti, fotografija ili videa potvrđujete da imate pravo na taj sadržaj i dozvoljavate portalu njegovu objavu uz navođenje vas kao izvora, ako to želite.</p>
<h2>5. Odgovornost</h2>
<p>Sadržaj objavljujemo s pažnjom i provjeravamo ga, ali ne odgovaramo za štetu nastalu korištenjem informacija s portala. Ne odgovaramo za sadržaj vanjskih stranica na koje vode linkovi. Uočene greške ispravljamo prema pravilima sa stranice <a href="/stranica/ispravke-i-demantiji">Ispravke i demantiji</a>.</p>
<h2>6. Kontakt</h2>
<p>Pitanja o ovim uslovima i zahtjeve za preuzimanje sadržaja šaljite na {MAIL}.</p>
"""),

    "ispravke-i-demantiji": ("Ispravke i demantiji", "Kako zatražiti ispravku ili objavu demantija na portalu Cazin Čaršija Novosti.", f"""
<p>Trudimo se da svaka informacija bude tačna i provjerena. Ako smatrate da je objavljena netačna informacija ili da su povrijeđena vaša prava, pošaljite nam zahtjev za ispravku ili demanti.</p>
<h2>Kako poslati zahtjev</h2>
<ul>
<li>E-mail: {MAIL}, uz naznaku „Ispravka“ ili „Demanti“ u naslovu poruke.</li>
<li>Navedite link na članak, tačno šta je netačno i kako glasi ispravna informacija.</li>
<li>Ostavite ime i kontakt, kako bismo mogli provjeriti zahtjev.</li>
</ul>
<h2>Šta mi radimo</h2>
<p>Svaki zahtjev provjeravamo bez odlaganja. Ako je informacija bila netačna, ispravku objavljujemo u samom članku, uz jasnu napomenu o tome šta je i kada ispravljeno, a po potrebi i kao posebnu objavu. Demanti objavljujemo u pravilu u izvornom obliku, osim dijelova koji sadrže uvrede ili nisu u vezi s objavljenim tekstom.</p>
<p>U radu se pridržavamo načela Kodeksa za štampu i online medije Bosne i Hercegovine.</p>
"""),

    "redakcija": ("Redakcija", "Redakcija portala Cazin Čaršija Novosti – urednik i kontakt.", f"""
<p>Portal {NAME} uređuje mali lokalni tim iz Cazina, uz pomoć saradnika i čitalaca koji nam šalju vijesti iz svojih mjesta.</p>
<h2>Uredništvo</h2>
<ul>
<li><strong>Osnivač, glavni i odgovorni urednik:</strong> {OWNER}</li>
<li><strong>E-mail redakcije:</strong> {MAIL}</li>
<li><strong>Telefon:</strong> {TEL}</li>
</ul>
<h2>Saradnici i autori</h2>
<p>Svi autorski tekstovi potpisani su imenom autora, a popis autora i njihovih članaka nalazi se na stranici <a href="/autori">Autori</a>.</p>
<h2>Postanite saradnik</h2>
<p>Pišete, fotografišete ili snimate i želite sarađivati s nama? Javite se na {MAIL} s kratkim predstavljanjem i primjerom svog rada.</p>
"""),

    "kontakt": ("Kontakt", "Kontakt redakcije portala Cazin Čaršija Novosti.", f"""
<p>Imate vijest, pitanje, prijedlog ili primjedbu? Javite nam se.</p>
<ul>
<li><strong>E-mail redakcije:</strong> {MAIL}</li>
<li><strong>Telefon / Viber / WhatsApp:</strong> {TEL}</li>
<li><strong>Glavni i odgovorni urednik:</strong> {OWNER}</li>
<li><strong>Lokacija:</strong> Cazin, Unsko-sanski kanton, Bosna i Hercegovina</li>
</ul>
<h2>Prijavite vijest</h2>
<p>Bili ste svjedok događaja? Pošaljite nam informaciju, fotografiju ili video putem <a href="/prijavite-vijest">obrasca za prijavu vijesti</a>. Ako želite, vaše ime neće biti objavljeno.</p>
<h2>Oglašavanje</h2>
<p>Za ponudu oglasnog prostora pogledajte stranicu <a href="/stranica/oglasavanje">Oglašavanje</a> ili pišite na {MAIL}.</p>
"""),

    "o-nama": ("O nama", "Cazin Čaršija Novosti – lokalni informativni portal za Cazin i Krajinu.", f"""
<p><strong>{NAME}</strong> je nezavisni informativni portal iz Cazina. Pratimo dešavanja u Cazinu i Unsko-sanskom kantonu, ali i važne vijesti iz Bosne i Hercegovine, regiona i svijeta.</p>
<h2>Šta donosimo</h2>
<ul>
<li>lokalne vijesti, hroniku, sport, kulturu i dešavanja u zajednici,</li>
<li>aktuelne informacije o stanju na graničnim prijelazima, saobraćaju i vremenu,</li>
<li>priče o ljudima, poduzetnicima i mjestima našeg kraja.</li>
</ul>
<h2>Naša načela</h2>
<p>Informacije provjeravamo prije objave, jasno odvajamo vijesti od mišljenja i reklamnog sadržaja, i ispravljamo greške čim ih uočimo. Vjerujemo da lokalna zajednica zaslužuje brzo, tačno i odgovorno informisanje.</p>
<p>Portal je osnovao i uređuje {OWNER}. Kontakt: {MAIL}.</p>
"""),

    "oglasavanje": ("Oglašavanje", "Oglašavanje na portalu Cazin Čaršija Novosti.", f"""
<p>Želite da vaša firma, usluga ili događaj dopru do čitalaca iz Cazina i Krajine? Nudimo oglasni prostor na portalu {NAME}.</p>
<h2>Mogućnosti</h2>
<ul>
<li>baneri na naslovnici, u rubrikama i u člancima, prilagođeni i za mobitele,</li>
<li>sponzorisani članci i promotivne objave,</li>
<li>najave događaja i posebne kampanje.</li>
</ul>
<h2>Pravila</h2>
<p>Sav plaćeni sadržaj jasno je označen kao „Sponzorisano“ ili „Oglas“ i odvojen od uređivačkog sadržaja. Zadržavamo pravo da odbijemo oglase koji su obmanjujući, uvredljivi ili u suprotnosti sa zakonom.</p>
<h2>Kontakt za oglašavanje</h2>
<p>Ponudu i cijene šaljemo na upit: {MAIL}, {TEL}.</p>
"""),
}


async def apply():
    db = AsyncIOMotorClient(os.environ["MONGO_URL"])[os.environ["DB_NAME"]]
    from core import new_id, iso
    old = await db.pages.find_one({"slug": "impressum"})
    if old and not await db.pages.find_one({"slug": "impresum"}):
        await db.pages.update_one({"slug": "impressum"}, {"$set": {"slug": "impresum"}})
    for slug, (title, desc, html) in PAGES.items():
        await db.pages.update_one({"slug": slug}, {"$set": {"title": title, "content": html.strip(), "seo_title": title, "seo_description": desc,
                                                           "published": True, "updated_at": iso()},
                                                  "$setOnInsert": {"id": new_id(), "created_at": iso()}}, upsert=True)
    s = await db.settings.find_one({"key": "site"})
    if s:
        v = s.get("value", {})
        v["contact_email"], v["phone"], v["address"] = EMAIL, PHONE, "Cazin, Unsko-sanski kanton, Bosna i Hercegovina"
        if v.get("social_image") in (None, "", "/icon-512.png"):
            v["social_image"] = "/og-image.jpg"
        for item in v.get("footer_menu", []):
            if item.get("url") == "/stranica/impressum":
                item["url"], item["label"] = "/stranica/impresum", "Impresum"
        await db.settings.update_one({"key": "site"}, {"$set": {"value": v}})
    print(f"Upisano {len(PAGES)} stranica")


if __name__ == "__main__":
    asyncio.run(apply())
