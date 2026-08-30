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
    });
})();
