// Suggestions de contacts au fil de la frappe, réutilisable partout où on
// cherche un contact par nom (recherche principale, partage d'adresse,
// ajout d'un intervenant à un dossier). Chaque champ concerné porte :
//   data-suggestions="id-de-la-zone-qui-affichera-les-suggestions"
//   data-mode="naviguer"     -> clic = va directement sur la fiche du contact
//   data-mode="remplir"      -> clic = remplit le champ et soumet son formulaire
//   data-mode="selectionner" -> clic = remplit ce champ ET un champ cible
//                                (data-cible-id), sans rien soumettre —
//                                utile quand d'autres choix (un rôle...)
//                                restent à faire avant validation.
//   data-mode="partage-adresse" -> clic = affiche les adresses actives du
//                                contact choisi, chacune avec un bouton
//                                "Lier cette adresse" qui la rattache par
//                                fetch (data-lier-url), sans jamais recharger
//                                la page ni perdre le contact sélectionné.

(function () {
    const champs = document.querySelectorAll("[data-suggestions]");

    champs.forEach(function (champ) {
        const zone = document.getElementById(champ.dataset.suggestions);
        const mode = champ.dataset.mode || "naviguer";
        const champCible = champ.dataset.cibleId
            ? document.getElementById(champ.dataset.cibleId)
            : null;
        if (!zone) {
            return;
        }

        let minuteur = null;

        champ.addEventListener("input", function () {
            clearTimeout(minuteur);
            const terme = champ.value.trim();
            if (terme.length < 2) {
                zone.innerHTML = "";
                return;
            }
            minuteur = setTimeout(() => chercher(terme), 300);
        });

        async function chercher(terme) {
            try {
                const reponse = await fetch(
                    "/contacts/api/suggestions?q=" + encodeURIComponent(terme)
                );
                if (!reponse.ok) {
                    throw new Error("Réponse HTTP " + reponse.status);
                }
                const resultats = await reponse.json();
                afficher(resultats);
            } catch (erreur) {
                zone.innerHTML = "";
                console.error("Erreur suggestions contact :", erreur);
            }
        }

        function afficher(resultats) {
            if (resultats.length === 0) {
                zone.innerHTML = "<p>Aucune suggestion.</p>";
                return;
            }
            const liste = document.createElement("ul");
            resultats.forEach(function (r) {
                const item = document.createElement("li");
                const bouton = document.createElement("button");
                bouton.type = "button";
                bouton.textContent = r.libelle
                    + (r.type_contact === "personne_morale" ? " (personne morale)" : "");
                bouton.addEventListener("click", function () {
                    if (mode === "naviguer") {
                        window.location.href = "/contacts/" + r.contact_id;
                    } else if (mode === "selectionner") {
                        champ.value = r.libelle;
                        if (champCible) {
                            champCible.value = r.contact_id;
                        }
                        zone.innerHTML = "";
                    } else if (mode === "partage-adresse") {
                        afficherAdressesPartageables(r);
                    } else {
                        champ.value = r.libelle;
                        zone.innerHTML = "";
                        champ.form.submit();
                    }
                });
                item.appendChild(bouton);
                liste.appendChild(item);
            });
            zone.innerHTML = "";
            zone.appendChild(liste);
        }

        async function afficherAdressesPartageables(r) {
            zone.innerHTML = "<p>Chargement…</p>";
            try {
                const reponse = await fetch(
                    "/contacts/api/adresses?contact_id=" + r.contact_id
                );
                if (!reponse.ok) {
                    throw new Error("Réponse HTTP " + reponse.status);
                }
                const adresses = await reponse.json();
                zone.innerHTML = "";

                const titre = document.createElement("p");
                titre.textContent = r.libelle;
                zone.appendChild(titre);

                if (adresses.length === 0) {
                    const vide = document.createElement("p");
                    vide.className = "aide";
                    vide.textContent = "Aucune adresse active pour ce contact.";
                    zone.appendChild(vide);
                    return;
                }

                const liste = document.createElement("ul");
                adresses.forEach(function (a) {
                    const item = document.createElement("li");
                    item.textContent = a.libelle + " ";
                    const lier = document.createElement("button");
                    lier.type = "button";
                    lier.textContent = "Lier cette adresse";
                    lier.addEventListener("click", function () {
                        lierAdresse(a.adresse_id, lier);
                    });
                    item.appendChild(lier);
                    liste.appendChild(item);
                });
                zone.appendChild(liste);
            } catch (erreur) {
                zone.innerHTML = "";
                console.error("Erreur adresses partageables :", erreur);
            }
        }

        async function lierAdresse(adresseId, bouton) {
            bouton.disabled = true;
            bouton.textContent = "Liaison…";
            try {
                const reponse = await fetch(champ.dataset.lierUrl, {
                    method: "POST",
                    headers: {"Content-Type": "application/x-www-form-urlencoded"},
                    body: "adresse_id=" + encodeURIComponent(adresseId),
                });
                if (!reponse.ok) {
                    throw new Error("Réponse HTTP " + reponse.status);
                }
                window.location.reload();
            } catch (erreur) {
                console.error("Erreur liaison adresse :", erreur);
                bouton.disabled = false;
                bouton.textContent = "Lier cette adresse";
            }
        }
    });
})();
