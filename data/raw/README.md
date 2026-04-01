# PCForge AI — Dataset Format Specification

Drop your dataset file here as **`pc_parts.json`** (or `pc_parts.csv`).

## Expected JSON Format

```json
{
  "version": "1.0",
  "components": [
    {
      "type": "cpu",
      "brand": "Intel",
      "model": "Core i5-13600K",
      "socket": "LGA1700",
      "cores": 14,
      "threads": 20,
      "base_clock": 3.5,
      "boost_clock": 5.1,
      "tdp": 125,
      "price": 319.99,
      "year": 2022
    },
    {
      "type": "gpu",
      "brand": "NVIDIA",
      "model": "GeForce RTX 4090",
      "vram": 24,
      "memory_type": "GDDR6X",
      "tdp": 450,
      "length": 336,
      "price": 1599.99,
      "year": 2022
    },
    {
      "type": "motherboard",
      "brand": "ASUS",
      "model": "ROG Strix Z790-E Gaming WiFi",
      "socket": "LGA1700",
      "chipset": "Z790",
      "form_factor": "ATX",
      "ram_type": "DDR5",
      "max_ram": 128,
      "price": 449.99,
      "year": 2022
    },
    {
      "type": "ram",
      "brand": "Corsair",
      "model": "Vengeance DDR5-6000 32GB",
      "ram_type": "DDR5",
      "capacity": 32,
      "speed": 6000,
      "modules": 2,
      "price": 109.99,
      "year": 2022
    },
    {
      "type": "storage",
      "brand": "Samsung",
      "model": "990 Pro NVMe",
      "interface": "PCIe 4.0",
      "capacity": 1024,
      "price": 99.99,
      "year": 2022
    },
    {
      "type": "psu",
      "brand": "Corsair",
      "model": "RM850x",
      "wattage": 850,
      "efficiency": "80+ Gold",
      "modular": true,
      "price": 149.99,
      "year": 2021
    },
    {
      "type": "case",
      "brand": "Lian Li",
      "model": "PC-O11 Dynamic EVO",
      "supported_form_factors": ["ATX", "mATX", "E-ATX"],
      "gpu_clearance": 435,
      "cooler_clearance": 167,
      "price": 169.99,
      "year": 2022
    },
    {
      "type": "cooler",
      "brand": "Noctua",
      "model": "NH-D15",
      "cooler_type": "air",
      "tdp_rating": 250,
      "height": 165,
      "price": 99.99,
      "year": 2017
    }
  ]
}
```

## Supported Field Aliases

The preprocessor accepts many common naming conventions automatically.
All of the following resolve to the same canonical field:

| Canonical | Accepted aliases |
|-----------|-----------------|
| `type` | `category`, `component_type`, `part_type`, `class` |
| `brand` | `manufacturer`, `make`, `vendor` |
| `model` | `model_name`, `name`, `product`, `part_name` |
| `price` | `price_usd`, `msrp`, `cost`, `retail_price` |
| `year` | `release_year`, `launch_year` |
| `tdp` (CPU) | `tdp_w`, `power`, `thermal_design_power` |
| `vram` | `vram_gb`, `memory`, `gpu_memory`, `memory_gb` |
| `tdp` (GPU) | `power_draw`, `tgp`, `total_graphics_power` |
| `length` | `length_mm`, `card_length`, `gpu_length` |
| `ram_type` | `memory_type`, `memory_standard`, `ddr_type` |
| `max_ram` | `max_ram_gb`, `max_memory`, `memory_capacity` |
| `capacity` | `capacity_gb`, `size`, `size_gb` |
| `speed` | `speed_mhz`, `frequency`, `clock_speed` |
| `wattage` | `wattage_w`, `rated_power`, `capacity_w` |
| `efficiency` | `rating`, `80plus`, `certification` |
| `gpu_clearance` | `gpu_clearance_mm`, `max_gpu_length` |
| `cooler_clearance` | `cooler_clearance_mm`, `max_cooler_height` |
| `height` | `height_mm`, `cooler_height`, `tower_height` |

## CSV Format

Also supported. Columns = canonical field names or any alias from the table above.
First column should be `type` (component category).

```
type,brand,model,socket,cores,threads,tdp,price,year
cpu,Intel,Core i5-13600K,LGA1700,14,20,125,319.99,2022
gpu,NVIDIA,GeForce RTX 4090,,,,450,1599.99,2022
```

## Filtering Rules Applied

- **Year filter**: components released before 2016 are excluded
  (PSU, Cases, Coolers are year-exempt)
- **Completeness**: entries missing required fields are discarded
  - CPU: socket + cores required
  - GPU: vram + power_draw required
  - Motherboard: socket + chipset required
  - RAM: ram_type + capacity required
  - Storage: interface + capacity required
  - PSU: wattage required
  - Case: supported_form_factors required
- **Deduplication**: exact same brand+model+key-spec entries removed

## Variant Expansion (automatic)

The preprocessor automatically expands:
- **GPUs** → VRAM variants (8GB, 12GB, 16GB, 24GB, etc.) + 4 AIB brand sub-models
  per VRAM tier (ASUS TUF, MSI Gaming X, Gigabyte AORUS, etc.)
- **RAM** → capacity variants (8/16/32/64/128GB) from each base entry
- **Storage** → capacity variants (256GB/512GB/1TB/2TB/4TB) from each base entry

You do NOT need to include every variant in your dataset — just one entry per
base model. The system handles the rest.
