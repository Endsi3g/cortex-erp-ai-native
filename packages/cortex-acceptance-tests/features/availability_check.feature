# language: fr
Fonctionnalité: Calcul précis de la disponibilité calendrier
  En tant qu'opérateur de comptoir ou agent IA
  Je veux connaître instantanément le stock disponible pour une période donnée
  Afin de ne jamais sur-engager l'inventaire

  Scénario: Équipement disponible sans conflit
    Étant donné un parc de 5 optiques "Cooke S4/i 50mm"
    Et 2 optiques actuellement réservées du "2026-09-01" au "2026-09-05"
    Quand je demande la disponibilité du "2026-09-02" au "2026-09-04"
    Alors la quantité restante disponible est de 3 unités
