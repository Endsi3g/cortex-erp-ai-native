# language: fr
Fonctionnalité: Calcul immuable du split de commission pour équipement en consignation
  En tant que gestionnaire de flotte Cortex
  Je veux que les revenus générés par du matériel sous-loué soient reversés selon le taux convenu
  Afin de produire des rapports propriétaires exacts et traçables

  Scénario: Calcul d'un split de 70/30 sur un boîtier en consignation
    Étant donné un équipement "Sony FX6" avec numéro de série "SN-FX6-998811" appartenant au propriétaire "Tiers Alpha"
    Et que le contrat de consignation stipule une commission propriétaire de 70%
    Quand une location de 5 jours est facturée à 1000.00 CAD
    Alors le montant alloué au propriétaire est de 700.00 CAD
    Et la marge Cortex enregistrée est de 300.00 CAD
    Et un snapshot immuable est lié à l'événement de facturation
