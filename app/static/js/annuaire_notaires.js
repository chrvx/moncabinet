// Recherche ponctuelle dans le répertoire local des offices notariaux (page
// contacts.nouveau_notaire_annuaire_recherche) : au fil de la frappe sur un
// terme unique (nom ou commune), interroge /contacts/api/annuaire-notaires
// et affiche les résultats ; un clic remplit les champs cachés du résultat
// choisi et soumet le formulaire de création (voir
// contacts.nouveau_notaire_annuaire). Contrairement à l'annuaire des
// avocats, il n'y a pas de code à re-résoudre côté serveur : tous les
// champs du résultat sont transmis directement.

(function () {
    const champTerme = document.getElementById("annuaire-terme");
    const zone = document.getElementById("annuaire-resultats");
    const formulaireCreation = document.getElementById("annuaire-formulaire-creation");

    if (!champTerme || !zone) {
        return;
    }

    const champs = {
        nom: document.getElementById("annuaire-nom"),
        siren: document.getElementById("annuaire-siren"),
        numero_voie: document.getElementById("annuaire-numero-voie"),
        libelle_voie: document.getElementById("annuaire-libelle-voie"),
        code_postal: document.getElementById("annuaire-code-postal"),
        commune: document.getElementById("annuaire-commune"),
    };

    let minuteur = null;

    champTerme.addEventListener("input", function () {
        clearTimeout(minuteur);
        const terme = champTerme.value.trim();
        if (terme.length < 2) {
            zone.innerHTML = "";
            return;
        }
        minuteur = setTimeout(() => chercher(terme), 300);
    });

    async function chercher(terme) {
        try {
            const parametres = new URLSearchParams({ q: terme });
            const reponse = await fetch("/contacts/api/annuaire-notaires?" + parametres.toString());
            if (!reponse.ok) {
                throw new Error("Réponse HTTP " + reponse.status);
            }
            afficher(await reponse.json());
        } catch (erreur) {
            zone.innerHTML = "<p>La recherche dans le répertoire local a échoué.</p>";
            console.error("Erreur recherche répertoire notaires :", erreur);
        }
    }

    function afficher(resultats) {
        if (resultats.length === 0) {
            zone.innerHTML = "<p>Aucun résultat dans le répertoire local (département non couvert, ou aucune correspondance).</p>";
            return;
        }
        const liste = document.createElement("ul");
        resultats.forEach(function (r) {
            const item = document.createElement("li");
            const bouton = document.createElement("button");
            bouton.type = "button";
            const details = [r.commune, r.siren ? "SIREN " + r.siren : null].filter(Boolean).join(" — ");
            bouton.textContent = r.nom + (details ? " (" + details + ")" : "");
            bouton.addEventListener("click", function () {
                Object.keys(champs).forEach(function (cle) {
                    champs[cle].value = r[cle] || "";
                });
                formulaireCreation.submit();
            });
            item.appendChild(bouton);
            liste.appendChild(item);
        });
        zone.innerHTML = "";
        zone.appendChild(liste);
    }
})();
