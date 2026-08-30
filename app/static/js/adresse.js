// Autocomplétion d'adresse : interroge l'API de géocodage de la
// Géoplateforme (remplaçante de l'ancienne api-adresse.data.gouv.fr,
// décommissionnée) et pré-remplit les champs du formulaire d'adresse au
// clic sur une suggestion. Tout reste éditable ensuite à la main : cette
// API ne connaît ni les compléments d'appartement, ni les mentions BP/TSA/CS,
// ni le CEDEX.

(function () {
    const champRecherche = document.getElementById("adresse-recherche");
    const zoneSuggestions = document.getElementById("adresse-suggestions");
    if (!champRecherche || !zoneSuggestions) {
        return;
    }

    let minuteur = null;

    champRecherche.addEventListener("input", function () {
        clearTimeout(minuteur);
        const requete = champRecherche.value.trim();
        if (requete.length < 3) {
            zoneSuggestions.innerHTML = "";
            return;
        }
        // On attend 300ms après la dernière frappe avant d'interroger
        // l'API, pour ne pas envoyer une requête à chaque lettre tapée.
        minuteur = setTimeout(() => rechercherAdresse(requete), 300);
    });

    async function rechercherAdresse(requete) {
        const url = "https://data.geopf.fr/geocodage/search?q="
            + encodeURIComponent(requete) + "&limit=5";
        try {
            const reponse = await fetch(url);
            if (!reponse.ok) {
                throw new Error("Réponse HTTP " + reponse.status);
            }
            const donnees = await reponse.json();
            afficherSuggestions(donnees.features || []);
        } catch (erreur) {
            zoneSuggestions.innerHTML =
                "<p>Autocomplétion indisponible pour l'instant : saisissez l'adresse à la main ci-dessous.</p>";
            console.error("Erreur autocomplétion adresse :", erreur);
        }
    }

    function afficherSuggestions(features) {
        if (features.length === 0) {
            zoneSuggestions.innerHTML = "<p>Aucune suggestion.</p>";
            return;
        }
        const liste = document.createElement("ul");
        features.forEach(function (feature) {
            const item = document.createElement("li");
            const bouton = document.createElement("button");
            bouton.type = "button";
            bouton.textContent = feature.properties.label;
            bouton.addEventListener("click", () => choisirSuggestion(feature));
            item.appendChild(bouton);
            liste.appendChild(item);
        });
        zoneSuggestions.innerHTML = "";
        zoneSuggestions.appendChild(liste);
    }

    function remplir(id, valeur) {
        const champ = document.getElementById(id);
        if (champ) {
            champ.value = valeur || "";
        }
    }

    function choisirSuggestion(feature) {
        const p = feature.properties;
        const coordonnees = feature.geometry.coordinates; // [longitude, latitude]

        remplir("champ-numero-voie", p.housenumber);
        remplir("champ-libelle-voie", p.street || p.name);
        remplir("champ-code-postal", p.postcode);
        remplir("champ-commune", p.city);
        remplir("code_insee_commune", p.citycode);
        remplir("longitude", coordonnees[0]);
        remplir("latitude", coordonnees[1]);
        remplir("libelle_complet_ban", p.label);

        champRecherche.value = p.label;
        zoneSuggestions.innerHTML = "";
    }
})();
