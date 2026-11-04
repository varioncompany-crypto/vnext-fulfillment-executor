---
name: varion-fulfillment-worklist
description: "Fuehrt offene Zahlungsstatus-, Warenuebergabe-, Versand-, Reservierungs- und Retourenfaelle in einer belegten Arbeitsliste zusammen. Nutzen fuer Operations-Triage; keine zusaetzliche Rechnung, Erstattung oder Kundenkommunikation."
metadata:
  owner_role: operations
  version: "1.0.0"
---

# varion-fulfillment-worklist

## Auftrag: Offene Auftragsliste

1. Lade neben dem Rollenvertrag die aktuelle customerService- und
   companyInboxWorkflow-Regelung derselben Revision. Verwende bestehende
   Auftrags-, Zahlungs-, Rechnungs-, Reservierungs-, Versand- und Fallleser.
   Benenne nicht gelesene Bereiche statt eine vollständige Liste zu behaupten.
2. Verbinde dieselben Fälle ausschließlich über stabile Quell-/Auftrags-/Fall-IDs
   oder belegte Zuordnungen. Vereine Duplikate; ein Zahlungsstatus, eine Rechnung,
   eine Bankbestätigung, ein Versandlabel und eine Warenübergabe sind verschiedene
   Ereignisse. Vorhandene Buchhaltung und Rechnungen wiederverwenden.
3. Trenne Vor-Ort-Verkauf, Abholung und Versand. „Lokal Kunde“ kann eine gültige
   anonyme Käuferzuordnung sein und ist keine Zahlungsart. Fehlende Adresse
   ist bei einer abgeschlossenen anonymen Warenübergabe kein Versandfehler.
4. Markiere bei echten offenen Fällen die fehlende nächste Leistung, Abhängigkeit,
   aktuelle Zuständigkeit und belegte Frist. Ein Alter allein beweist weder
   Zahlungsverzug noch Reklamationsberechtigung oder Nichterfüllung.
5. Lies vorhandene Entscheidungen zu eigenen Fällen nach aktuellem Inbox-Vertrag.
   Freigabe, physische Rückgabe, bestätigte Erstattung und Ersatzversand bleiben
   getrennt. Der Listenlauf führt keine dieser Aktionen aus; die bestehenden
   genehmigten Kundendienstabläufe behalten ihre eigenen aktuellen Regeln.

Ergebnis: priorisierte, deduplizierte Fallliste mit Statusherkunft, owner,
fehlendem Nachweis, nächstem Schritt und vorhandener Entscheidung. Höchstens
drei dringliche Punkte hervorheben; übrige tatsächliche Fälle zugänglich halten.
Keine neuen Kundenanschreiben, Mahnungen, Rechnungserstellungen, Lagerbewegungen,
Kulanzentscheidungen, Erstattungen oder Bewertungsveröffentlichungen aus dieser
Auswertung ableiten. Eine interne Fallliste ist keine ausgeführte Kundenleistung.

## Einordnung und bestehender Kontext

Dieser zusätzliche Skill arbeitet im Auftrag der jeweiligen Rolle. Lies deren
aktuelle AGENTS.md und ROLE-REFERENCE.md und führe den dort vorgegebenen gemeinsamen
Kontext-/Memory-Start aus. Verwende die aktuelle Vertragsrevision und bestehende
Fach-Reader. Der Skill erweitert deren Berechtigungen nicht und ersetzt keinen
vorhandenen Skill, fachlichen Ablauf oder Freigabeprozess.

Sein eigener Umfang ist Lesen, Prüfen und ein interner Bericht oder Entwurf.
Schon autorisierte andere Abläufe bleiben getrennt gültig. Er richtet keine neue
Automatik, Infrastruktur, Erinnerung, kostenpflichtige API oder Nachrichtenroutine ein.
Keine private Kunden-, Finanz- oder Lieferanteninformation, Rohantwort oder Zugangsdaten
in dieses Rollen-Repository schreiben. Ergebnisse gehören in die bestehende,
tatsächlich als privat bestätigte Auftrags-/Ergebnisablage. Die Bezeichnung „privat“
in einer alten Notiz ersetzt keine Zugriffsprüfung.

## Nachweis und Abschluss

- Binde Erkenntnisse an tatsächliche Quellen-IDs, deren ursprüngliche Beobachtungszeit,
  den Prüfzeitpunkt, die Vertragsrevision sowie den gelesenen Ausschnitt und seine Abdeckung.
  Ein interner Status, Cache, HTTP 200 oder vorhandener Schlüssel belegt keinen Facherfolg.
- Fehlende Daten bleiben unbekannt. Veraltete, historische und synthetische Quellen
  ausdrücklich kennzeichnen; Testdaten autorisieren keine echte Geschäftsaktion.
- Berichte evidenceStatus complete, partial oder unavailable für den geprüften Umfang;
  wechsle deshalb nicht eigenmächtig das Statusschema der bestehenden Aufgaben.
- Liefere die wesentlichen Befunde mit owner, sourceRefs, nächstem konkretem Schritt
  und einem tatsächlich prüfbaren Ergebnisverweis. Zeige nur belegte Beträge und Wirkungen.
- Nutze für zugeordnete Aufgaben den bestehenden shared_tasks.py-/TaskPort-Vertrag
  einschließlich erwarteter Version, operationId und Ergebnis-Readback. Ein unklarer
  Schreibausgang wird vor Wiederholung abgeglichen. Ohne aktuelle Aufgabe keine
  beliebige fremde Aufgabe übernehmen oder als abgeschlossen markieren.
- Beende den gemeinsamen Kontextlauf wie in AGENTS.md vorgesehen. Fehlt ein Zugriff,
  benenne den genauen Reader/Scope/Fehler, setze nur abhängige Arbeit aus und behaupte
  weder gespeicherte Ergebnisse noch eine erfolgreiche Live-Abnahme.
