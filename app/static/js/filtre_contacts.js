// Filtrage en direct du tableau de contacts (page contacts.recherche et
// ses raccourcis par qualité contacts.liste_avocats/clients/adversaires) :
// au fil de la frappe dans le champ de recherche, remplace le contenu du
// tableau par les contacts correspondants (sans recharger la page), plutôt
// que d'afficher une liste de suggestions séparée sous le champ. Le champ
// peut porter data-qualite pour restreindre le filtrage à cette qualité
// (avocat/client/adversaire), en plus du terme tapé.

(function () {
    const champ = document.getElementById("recherche-q");
    const zone = document.getElementById("zone-resultats-contacts");
    if (!champ || !zone) {
        return;
    }

    const qualite = champ.dataset.qualite || "";
    const contenuInitial = zone.innerHTML;
    let minuteur = null;

    const icones = {
        personne_physique:
            '<svg class="icone-type" viewBox="0 0 24 24"><title>Personne physique</title>' +
            '<circle cx="12" cy="8" r="3.2"/><path d="M5 20c1-3.8 4-5.8 7-5.8s6 2 7 5.8"/></svg>',
        personne_morale:
            '<svg class="icone-type" viewBox="0 0 24 24"><title>Personne morale</title>' +
            '<path d="M5 21V4h9v17M14 21V9h5v12"/><path d="M8 8h2M8 12h2M8 16h2"/></svg>',
    };

    champ.addEventListener("input", function () {
        clearTimeout(minuteur);
        const terme = champ.value.trim();
        if (terme.length === 0) {
            zone.innerHTML = contenuInitial;
            return;
        }
        minuteur = setTimeout(() => filtrer(terme), 300);
    });

    async function filtrer(terme) {
        try {
            let url = "/contacts/api/tableau?q=" + encodeURIComponent(terme);
            if (qualite) {
                url += "&qualite=" + encodeURIComponent(qualite);
            }
            const reponse = await fetch(url);
            if (!reponse.ok) {
                throw new Error("Réponse HTTP " + reponse.status);
            }
            const resultats = await reponse.json();
            afficher(resultats, terme);
        } catch (erreur) {
            console.error("Erreur filtrage contacts :", erreur);
        }
    }

    function afficher(resultats, terme) {
        if (resultats.length === 0) {
            zone.innerHTML = "<p>Aucun contact ne correspond à « " + echapper(terme) + " ».</p>";
            return;
        }
        const lignes = resultats.map(function (r) {
            const email = r.email
                ? '<a href="mailto:' + echapper(r.email) + '">' + echapper(r.email) + "</a>"
                : "";
            return (
                "<tr>" +
                "<td>" + icones[r.type_contact] + "</td>" +
                '<td><a href="/contacts/' + r.contact_id + '">' + echapper(r.nom) + "</a></td>" +
                "<td>" + echapper(r.prenom || "") + "</td>" +
                "<td>" + echapper(r.telephone || "") + "</td>" +
                "<td>" + email + "</td>" +
                "</tr>"
            );
        });
        zone.innerHTML =
            "<table><thead><tr><th>Type</th><th>Nom / Dénomination</th>" +
            "<th>Prénom</th><th>Téléphone</th><th>Email</th></tr></thead>" +
            "<tbody>" + lignes.join("") + "</tbody></table>";
    }

    function echapper(texte) {
        const div = document.createElement("div");
        div.textContent = texte;
        return div.innerHTML;
    }
})();
