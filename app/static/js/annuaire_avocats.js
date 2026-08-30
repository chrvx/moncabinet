// Recherche ponctuelle dans l'Annuaire national des avocats (page
// contacts.nouveau_avocat_annuaire_recherche) : au fil de la frappe sur le
// nom (et le prénom optionnel), interroge /contacts/api/annuaire-avocats
// et affiche les résultats ; un clic remplit le champ caché code_cnbf et
// soumet le formulaire de création (voir contacts.nouveau_avocat_annuaire).

(function () {
    const champNom = document.getElementById("annuaire-nom");
    const champPrenom = document.getElementById("annuaire-prenom");
    const zone = document.getElementById("annuaire-resultats");
    const champCodeCnbf = document.getElementById("annuaire-code-cnbf");
    const formulaireCreation = document.getElementById("annuaire-formulaire-creation");

    if (!champNom || !zone) {
        return;
    }

    let minuteur = null;

    function declencherRecherche() {
        clearTimeout(minuteur);
        const nom = champNom.value.trim();
        if (nom.length < 2) {
            zone.innerHTML = "";
            return;
        }
        minuteur = setTimeout(() => chercher(nom, champPrenom.value.trim()), 300);
    }

    champNom.addEventListener("input", declencherRecherche);
    champPrenom.addEventListener("input", declencherRecherche);

    async function chercher(nom, prenom) {
        try {
            const parametres = new URLSearchParams({ nom });
            if (prenom) {
                parametres.set("prenom", prenom);
            }
            const reponse = await fetch("/contacts/api/annuaire-avocats?" + parametres.toString());
            if (!reponse.ok) {
                throw new Error("Réponse HTTP " + reponse.status);
            }
            afficher(await reponse.json());
        } catch (erreur) {
            zone.innerHTML = "<p>La recherche dans l'annuaire national a échoué.</p>";
            console.error("Erreur recherche annuaire avocats :", erreur);
        }
    }

    function afficher(resultats) {
        if (resultats.length === 0) {
            zone.innerHTML = "<p>Aucun résultat dans l'annuaire national.</p>";
            return;
        }
        const liste = document.createElement("ul");
        resultats.forEach(function (r) {
            const item = document.createElement("li");
            const bouton = document.createElement("button");
            bouton.type = "button";
            const details = [r.barreau, r.cabinet, r.ville].filter(Boolean).join(" — ");
            bouton.textContent = r.prenom + " " + r.nom + (details ? " (" + details + ")" : "");
            bouton.addEventListener("click", function () {
                champCodeCnbf.value = r.code_cnbf;
                formulaireCreation.submit();
            });
            item.appendChild(bouton);
            liste.appendChild(item);
        });
        zone.innerHTML = "";
        zone.appendChild(liste);
    }
})();
