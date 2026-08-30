"""Script de validation manuelle du modèle de contacts (phase 2).
Pas un test automatisé formel (pytest viendra plus tard) : juste un
scénario qui exerce chaque mécanisme un par un, avec des affichages clairs."""

from app import create_app
from app.repositories import contacts, coordonnees, qualifications, reference, roles

app = create_app()

with app.app_context():
    UID = 1  # l'utilisateur Clement créé via `flask creer-utilisateur`

    print("=== 1. Création d'une personne physique complète ===")
    jean = contacts.creer_personne_physique(
        nom="Dupont",
        utilisateur_id=UID,
        prenom="Jean",
        genre="M",
        civilite_id="M",
        date_naissance="1980-03-12",
        ville_naissance="Lyon",
        departement_naissance_id="69",
        nationalite_id="FR",
        profession="Ingénieur",
    )
    print(f"  {jean.prenom} {jean.nom}, né à {jean.ville_naissance} ({jean.departement_naissance_id})")
    assert jean.nom == "DUPONT" and jean.departement_naissance_id == "69"

    print("\n=== 2. Personne physique née à l'étranger ===")
    marie = contacts.creer_personne_physique(
        nom="Dupont",
        utilisateur_id=UID,
        prenom="Marie",
        genre="F",
        civilite_id="MME",
        ville_naissance="Bruxelles",
        pays_naissance_id="BE",
        nationalite_id="BE",
    )
    print(f"  {marie.prenom} {marie.nom}, née à {marie.ville_naissance} ({marie.pays_naissance_id})")
    assert marie.pays_naissance_id == "BE" and marie.departement_naissance_id is None

    print("\n=== 3. Personne morale ===")
    cabinet = contacts.creer_personne_morale(
        raison_sociale="Cabinet Martin & Associés",
        utilisateur_id=UID,
        forme="SELARL",
    )
    print(f"  {cabinet.raison_sociale} ({cabinet.forme})")

    print("\n=== 4. Adresse partagée entre Jean et Marie (couple) ===")
    adresse, lien_jean = coordonnees.ajouter_adresse(
        contact_id=jean.contact_id,
        utilisateur_id=UID,
        numero_voie="12",
        libelle_voie="Rue de la République",
        code_postal="69002",
        commune="Lyon",
    )
    lien_marie = coordonnees.lier_adresse_existante(
        contact_id=marie.contact_id,
        adresse_id=adresse.id,
        utilisateur_id=UID,
    )
    print(f"  Adresse id={adresse.id} : {adresse.numero_voie} {adresse.libelle_voie}, {adresse.commune}")
    print(f"  Liée à Jean (lien {lien_jean.id}) et à Marie (lien {lien_marie.id}), date_fin des deux : "
          f"{lien_jean.date_fin} / {lien_marie.date_fin}")
    assert lien_jean.adresse_id == lien_marie.adresse_id == adresse.id

    print("\n=== 5. Adresse CEDEX + BP pour le cabinet ===")
    adresse_cabinet, _ = coordonnees.ajouter_adresse(
        contact_id=cabinet.contact_id,
        utilisateur_id=UID,
        numero_voie="1",
        libelle_voie="Rue François Vidal",
        mention_distribution_type="CS",
        mention_distribution_valeur="30238",
        code_cedex="33506",
        commune="Libourne",
    )
    print(f"  {adresse_cabinet.numero_voie} {adresse_cabinet.libelle_voie} - "
          f"{adresse_cabinet.mention_distribution_type} {adresse_cabinet.mention_distribution_valeur} - "
          f"{adresse_cabinet.code_cedex} {adresse_cabinet.commune} CEDEX")

    print("\n=== 6. Marie déménage : on clôt son lien, Jean garde le sien ===")
    coordonnees.terminer_lien_adresse(lien_marie.id, UID)
    actives_jean = coordonnees.lister_adresses(jean.contact_id)
    actives_marie = coordonnees.lister_adresses(marie.contact_id)
    toutes_marie = coordonnees.lister_adresses(marie.contact_id, actives_seulement=False)
    print(f"  Adresses actives de Jean : {len(actives_jean)}")
    print(f"  Adresses actives de Marie : {len(actives_marie)} (doit être 0)")
    print(f"  Adresses historiques de Marie (avec la clôturée) : {len(toutes_marie)} (doit être 1)")
    assert len(actives_jean) == 1 and len(actives_marie) == 0 and len(toutes_marie) == 1

    print("\n=== 7. Téléphone et email ===")
    coordonnees.ajouter_telephone(jean.contact_id, "0472000000", UID)
    coordonnees.ajouter_email(jean.contact_id, "jean.dupont@example.fr", UID)
    tels = coordonnees.lister_telephones(jean.contact_id)
    emails = coordonnees.lister_emails(jean.contact_id)
    print(f"  Téléphones de Jean : {[t.numero for t, _ in tels]}")
    print(f"  Emails de Jean : {[e.adresse_email for e, _ in emails]}")

    print("\n=== 8. Recherche anti-conflit d'intérêts ===")
    resultats_dupont = contacts.rechercher_par_nom("Dupont")
    resultats_martin = contacts.rechercher_par_nom("Martin")
    print(f"  'Dupont' -> {[(r.type_contact, r.libelle) for r in resultats_dupont]}")
    print(f"  'Martin' -> {[(r.type_contact, r.libelle) for r in resultats_martin]}")
    assert len(resultats_dupont) == 2
    assert len(resultats_martin) == 1 and resultats_martin[0].type_contact == "personne_morale"

    print("\n=== 9. Rôles : cas valides ===")
    role_avocat_type = next(t for t in reference.lister_types_role() if t.libelle == "avocat")
    role_demandeur_type = next(t for t in reference.lister_types_role() if t.libelle == "demandeur")
    role_enfant_type = next(t for t in reference.lister_types_role() if t.libelle == "enfant")

    r1 = roles.attribuer_role(jean.contact_id, role_avocat_type.id, UID, contact_lie_id=marie.contact_id)
    print(f"  'avocat' de Marie pour Jean : OK (role_contact id={r1.id})")

    r2 = roles.attribuer_role(jean.contact_id, role_demandeur_type.id, UID, dossier_id=999)
    print(f"  'demandeur' avec dossier_id=999 pour Jean : OK (role_contact id={r2.id})")

    r3 = roles.attribuer_role(marie.contact_id, role_enfant_type.id, UID, contact_lie_id=jean.contact_id)
    print(f"  'enfant' de Jean pour Marie : OK (role_contact id={r3.id})")

    print("\n=== 10. Rôles : cas qui doivent échouer ===")
    try:
        roles.attribuer_role(jean.contact_id, role_demandeur_type.id, UID)
        print("  ERREUR : aurait dû échouer (demandeur sans dossier)")
    except roles.RegleRoleViolee as e:
        print(f"  'demandeur' sans dossier : refusé comme prévu ({e})")

    try:
        roles.attribuer_role(jean.contact_id, role_enfant_type.id, UID)
        print("  ERREUR : aurait dû échouer (enfant sans contact lié)")
    except roles.RegleRoleViolee as e:
        print(f"  'enfant' sans contact lié : refusé comme prévu ({e})")

    print("\n=== 11. Qualification professionnelle : Jean devient avocat ===")
    barreau_lyon = next(b for b in reference.lister_barreaux() if b.libelle == "barreau de Lyon")
    avocat_jean = qualifications.enregistrer_avocat(
        jean.contact_id, UID, barreau_id=barreau_lyon.id, cabinet_id=cabinet.contact_id
    )
    print(f"  Jean est avocat au {barreau_lyon.libelle}, cabinet {cabinet.raison_sociale}")
    assert avocat_jean.barreau_id == barreau_lyon.id and avocat_jean.cabinet_id == cabinet.contact_id

    print("\n=== 12. Modification de la qualification (même contact, deux fois) ===")
    barreau_paris = next(b for b in reference.lister_barreaux() if b.libelle == "barreau de Paris")
    avocat_jean_modifie = qualifications.enregistrer_avocat(
        jean.contact_id, UID, barreau_id=barreau_paris.id, cabinet_id=cabinet.contact_id
    )
    print(f"  Jean change de barreau : {barreau_paris.libelle}")
    assert avocat_jean_modifie.barreau_id == barreau_paris.id
    assert qualifications.recuperer_profession(jean.contact_id) == "avocat"

    print("\n=== 13. Exclusivité mutuelle : Jean devient notaire à la place ===")
    notaire_jean = qualifications.enregistrer_notaire(jean.contact_id, UID, office_id=cabinet.contact_id)
    assert qualifications.recuperer_avocat(jean.contact_id) is None
    assert qualifications.recuperer_profession(jean.contact_id) == "notaire"
    print("  Jean est maintenant notaire, la qualification avocat a été retirée automatiquement")

    print("\n=== 14. Retrait de la qualification ===")
    qualifications.supprimer_notaire(jean.contact_id)
    assert qualifications.recuperer_notaire(jean.contact_id) is None
    assert qualifications.recuperer_profession(jean.contact_id) is None
    print("  Qualification notaire retirée avec succès")

    print("\n=== Tout est passé ===")
