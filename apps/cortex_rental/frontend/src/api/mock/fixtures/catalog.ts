import type { EquipmentItem, KitPackage } from '@/types/inventory'

export const initialCatalog: EquipmentItem[] = [
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    item_code: 'DEMO-ITM-ALX35',
    item_name: 'ARRI Alexa 35 Camera Package',
    category: 'Cameras',
    brand: 'ARRI',
    daily_rate: 1500,
    weekly_rate: 4500,
    monthly_rate: 13500,
    currency: 'CAD',
    is_serialized: true,
    total_fleet_quantity: 4,
    available_quantity: 2,
    maintenance_quantity: 1,
    rented_quantity: 1,
    required_accessories: ['ARRI LPL Mount', 'ARRI Codex Compact Drive 2TB (x2)', 'ARRI B-Mount Battery Plate'],
    optional_accessories: ['ARRI Electronic Viewfinder MVF-2', 'ARRI Hi-5 Wireless Hand Unit']
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    item_code: 'DEMO-ITM-VRP8K',
    item_name: 'RED V-Raptor XL 8K Production Pack',
    category: 'Cameras',
    brand: 'RED Digital Cinema',
    daily_rate: 1200,
    weekly_rate: 3600,
    monthly_rate: 10800,
    currency: 'CAD',
    is_serialized: true,
    total_fleet_quantity: 2,
    available_quantity: 2,
    maintenance_quantity: 0,
    rented_quantity: 0,
    required_accessories: ['RED Pro CFexpress 2TB (x2)', 'RED DSMC3 Touch 7.0 Monitor'],
    optional_accessories: ['RED Compact Dual V-Lock Charger']
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    item_code: 'DEMO-ITM-CKE-S4',
    item_name: 'Cooke S4/i Prime Lens Set (18/25/32/50/75/100mm)',
    category: 'Lenses',
    brand: 'Cooke Optics',
    daily_rate: 950,
    weekly_rate: 2850,
    monthly_rate: 8550,
    currency: 'CAD',
    is_serialized: true,
    total_fleet_quantity: 2,
    available_quantity: 1,
    maintenance_quantity: 0,
    rented_quantity: 1,
    required_accessories: ['Custom Flight Case', '110mm Lens Caps & Rear Caps'],
    optional_accessories: ['Arri LMB 4x5 Matte Box']
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    item_code: 'DEMO-ITM-APU-600',
    item_name: 'Aputure Electro Storm CS15 LED Kit',
    category: 'Lighting',
    brand: 'Aputure',
    daily_rate: 350,
    weekly_rate: 1050,
    monthly_rate: 3150,
    currency: 'CAD',
    is_serialized: false,
    total_fleet_quantity: 12,
    available_quantity: 8,
    maintenance_quantity: 0,
    rented_quantity: 4,
    required_accessories: ['Control Box', 'Reflector 35°', 'Head Cable 7.5m'],
    optional_accessories: ['Motorized F14 Fresnel', 'Spotlight Max']
  },
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    item_code: 'DEMO-ITM-DJI-RS3',
    item_name: 'DJI Ronin 2 Professional Combo',
    category: 'Grip & Support',
    brand: 'DJI Pro',
    daily_rate: 450,
    weekly_rate: 1350,
    monthly_rate: 4050,
    currency: 'CAD',
    is_serialized: true,
    total_fleet_quantity: 3,
    available_quantity: 3,
    maintenance_quantity: 0,
    rented_quantity: 0,
    required_accessories: ['Grip Ring', 'Remote Controller', 'TB50 Batteries (x4)'],
    optional_accessories: ['Ready Rig GS + ProArm', 'Cinemilled Universal Mount']
  }
]

export const initialKits: KitPackage[] = [
  {
    provenance: 'demo',
    last_synced_at: '2026-09-02T16:00:00Z',
    kit_code: 'DEMO-KIT-CINEMA-ULTIMA',
    kit_name: 'Cinema Ultima Camera & Glass Package',
    category: 'Complete Packages',
    bundle_daily_rate: 2200,
    components: [
      { item_code: 'DEMO-ITM-ALX35', item_name: 'ARRI Alexa 35 Camera Package', quantity: 1, is_mandatory: true },
      { item_code: 'DEMO-ITM-CKE-S4', item_name: 'Cooke S4/i Prime Lens Set', quantity: 1, is_mandatory: true },
      { item_code: 'DEMO-ITM-DJI-RS3', item_name: 'DJI Ronin 2 Professional Combo', quantity: 1, is_mandatory: false }
    ]
  }
]
