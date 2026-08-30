// Modèle d'exemple : lettre simple.
//
// Les données sont injectées par app/services/generation_documents.py sous
// forme d'un data.json copié à côté de ce fichier au moment de la fusion
// (voir construire_contexte) : { dossier: {...}, intervenants: {role: [...]},
// extra: {...champs déclarés dans metadata.json...} }.
//
// La mise en page ci-dessous est volontairement simple ; elle sert de base
// à copier pour de nouveaux modèles plutôt qu'à retoucher directement.

#let data = json("data.json")
#let client = data.intervenants.at("client", default: ()).at(0, default: none)

#set page(margin: 2.5cm)
#set text(font: "Libertinus Serif", size: 11pt)
#set par(justify: true)

#let nom_client = if client == none {
  ""
} else if client.type_contact == "personne_physique" {
  client.at("prenom", default: "") + " " + client.at("nom", default: "")
} else {
  client.at("raison_sociale", default: "")
}

#align(right)[
  #datetime.today().display("[day]/[month]/[year]")
]

#if client != none [
  #nom_client \
  #if client.at("adresse", default: none) != none [
    #client.adresse
  ]
]

#v(1em)

= #data.extra.at("objet", default: "")

#if data.extra.at("urgent", default: false) [
  *Pli urgent*
]

#if data.dossier.reference != none [
  Dossier n° #data.dossier.reference
]

#v(1em)

Maître,

#data.extra.at("corps", default: "")

Je vous prie d'agréer, Maître, l'expression de mes salutations distinguées.
