# Source-backed player-entry correction — Batch 2B

Local diagnostic correction on branch `source-backed-entry-fix`, based on merged Batch 2A `81a23aeb4c5e64c4aebba188aca602254a8ad3b3`. The prerequisite is the validated, documented implementation merged through PR #9; no formal GitHub review is claimed. Original worktrees, uncommitted work, source bytes, published ratings and frozen populations are preserved. No commit, push, merge, PR, release or deployment was made.

**All ten proposed published appearances are independently supported and recovered.** Zero of the ten remain excluded for participation. Added elapsed exposure: `6517279/12000` minutes = **543.1065833333 minutes**. This does not clear separate player/metric exclusions or grant ranking membership.

## Root cause and implementation

The adapter resolved the original first Tactical Shift endpoint correctly but classified it as `position_change`. The participation validator requires a prior position-change exit, so a first shift was rejected as `unsupported_position_change`; incoming substitutions also produced an unrepresented original-entry check. Original XI/substitution evidence already existed at the exact same period-local clock.

`statsbomb_participation._source_backed_entry` constructs one frozen `ReconstructedEntry` only after unique stable-ID original entry support, exact entry/shift clock equality, agreeing initial XI position for starters, unique compatible shift, all positional snapshots, complete boundaries, existing source checks, normal participation validation, and a separate original-event entry/exit walk with exact interval-union equality. Reversed chronology, missing/duplicate transitions, permanent-exit conflicts, overlaps, dismissals continuing through lineup intervals and snapshot contradictions remain blocking. Unknown source categories are unchanged.

Only the first internal Stint entry category and its original evidence references change. Provider lineup labels, raw positions, UUIDs, fixture/team/player identities, exact endpoint geometry and provenance remain intact. `AdaptedPlayer.reconstructed_entries` and `source_reconstruction.appearance_rows` retain the explicit entry/shift binding. No player list, tolerance, fuzzy-name rule or permanent-exit policy is added to production. Metric-specific admission runs unchanged after participation recovery.

## Original source evidence

The independent checker identifies entries directly from pinned original bytes without importing the production adapter or decision helper. Its event state machine and lineup endpoint reconstruction agree on exact unions. The full replay compares the actually loaded merged Batch 2A module against proposed production code; source schema validation remains complete.

| Player / fixture | Original entry UUID | First shift UUID | Exact period / clock | Exact seconds | Minutes |
| --- | --- | --- | --- | ---: | ---: |
| Joe Ledley (4817) / 3754026 | `0e27da71-11fe-4702-823d-f8b27e2e657d` (Substitution) | `0f07cac8-b81d-404a-8070-b869cfe27717` | 2 / 00:00:00.000 | 4895/8 | 10.1979166667 |
| Sung-Yeung Ki (3605) / 3754047 | `e34bfa03-3377-4d94-9e0f-379bef12365e` (Starting XI) | `bd48939f-b7a2-483d-9f63-6ab647af05b0` | 1 / 00:00:00.000 | 1447613/250 | 96.5075333333 |
| Ashley Williams (3644) / 3754047 | `e34bfa03-3377-4d94-9e0f-379bef12365e` (Starting XI) | `bd48939f-b7a2-483d-9f63-6ab647af05b0` | 1 / 00:00:00.000 | 1447613/250 | 96.5075333333 |
| Valon Behrami (5540) / 3754080 | `ab2134a6-f26c-4eee-b7a4-ddc873c52e64` (Substitution) | `bc7f8233-a976-42b8-acac-bb6d403e8469` | 2 / 00:00:00.000 | 375238/125 | 50.0317333333 |
| José Antonio García Rabasco (24149) / 3825640 | `2cec3aae-6b1a-4bf7-9dd3-ad82c41c9cff` (Substitution) | `80b7dd8f-7f81-4c06-b4d2-6d417711c401` | 2 / 00:00:00.000 | 2858703/1000 | 47.6450500000 |
| Manuel Trigueros Muñoz (6771) / 3825684 | `52bec2b7-1c23-436e-8868-1b19ec92e6b2` (Substitution) | `96d5860c-b8dc-4e23-a2de-f28fe599fd8a` | 2 / 00:00:00.000 | 2884821/1000 | 48.0803500000 |
| Jordan Ferri (3118) / 3829502 | `51d17214-7146-43f5-ab5c-59c95c3d732a` (Substitution) | `352ab212-1af7-4b7b-bc27-9707d9bc3a15` | 2 / 00:00:00.000 | 723247/250 | 48.2164666667 |
| Dario Dainelli (7771) / 3879611 | `51d288d1-8b22-4894-aa1c-5fec00508463` (Substitution) | `c1dae206-4aa4-4520-9c27-7881cb2bbc9f` | 2 / 00:00:00.000 | 1467591/500 | 48.9197000000 |
| Luca Rigoni (7461) / 3879666 | `ed5051b1-51cc-4a34-b9a7-63fe137b4f91` (Substitution) | `d2caa8a6-ea95-495b-bc3f-e7195f54cb86` | 2 / 00:00:00.000 | 587647/200 | 48.9705833333 |
| Bryan Dabo (3421) / 3900560 | `152fcd05-c8f0-4535-8c50-c6c98cb2be7a` (Substitution) | `37943e3e-b514-4167-990b-cfe154250012` | 2 / 00:00:00.000 | 2881783/1000 | 48.0297166667 |

| Player / fixture | Original events SHA256 | Original lineups SHA256 |
| --- | --- | --- |
| 4817 / 3754026 | `45b18f54bd5532e9c0247d1cb40f9591e17e5d169f35fd78b2ddc16b2d4aea94` | `81fac90088f3396132e49ba9f65889e80390718933e4a15b27601c74847b7e98` |
| 3605 / 3754047 | `7a4f89a7d787e68026fa224252e241fc15ddb0e25b25776f66dc7809dc19e41d` | `7c46f6f1647506da86c46efac31db36b8b0cc1430d9c7989f3391bc5ac770f78` |
| 3644 / 3754047 | `7a4f89a7d787e68026fa224252e241fc15ddb0e25b25776f66dc7809dc19e41d` | `7c46f6f1647506da86c46efac31db36b8b0cc1430d9c7989f3391bc5ac770f78` |
| 5540 / 3754080 | `82214da80ae4bac03bf902f80d2f18e85ab4554c3622cd018dd60b759d0308ec` | `09b0f0abdf7a11e0576956f93cc4a81cdc8bab6944cc4c4686130bc6b8ded430` |
| 24149 / 3825640 | `e6f050de6dffd1d80e98f2e70b52f32be259a90999ac200bff104a373dc42172` | `fb5452d50122b85bd5fdf1883ceb6907f268c056330308b627cf8868a5d05e59` |
| 6771 / 3825684 | `e62624fb80975f6d970439c248dca5016f1363e52130818a754f8bc21b827342` | `0ab203d600034741f7193582bf3657e999c627db28cb2da0e73bc858c0878495` |
| 3118 / 3829502 | `d8ad2f42faeed9fffbd76a91a1e4559483012127e8db7f2b45bf731ee52e13b0` | `9dcfdfc5ecb380287d05e2e445bb6636cb62bdb67965a7a89937e974581262ef` |
| 7771 / 3879611 | `2fcecb88fe022bfb4e495f48bee25a52dd0ab57ada4e360665926283bea1fa4b` | `a46d5975c94a4db10987f71d8e14c235291cdb9fe4edd68f0f6c9d92e46954d1` |
| 7461 / 3879666 | `1e42dd1cfb002f11abb9f8c37db1c32843d8e941a34c2db2b6cf2faf9380395e` | `358e3d99b34f33bfcbb06f51d22abba3cd0c21ff9cc5cde4a0de9e05bd4da2ac` |
| 3421 / 3900560 | `15c39936da86101e22f8403d76fc262e501bb60cda263ef13be1330a3489e713` | `20dcbde1ee09603da76b03ed094d5b5cd095788a2b7c6d6f47bcfdc0dcebbb55` |

`entry-evidence.csv` retains full original entry and shift records, indices, team IDs, positions, source document paths/hashes and proof references. `appearance-comparison.csv` retains every changed source appearance, prior issue arrays and exact before/after exposure. `entry-independent-source-checks.json` independently retains full event/lineup interval geometry, snapshot/boundary UUIDs and original positions. No original observation is rewritten.

## Four-state population and rating comparisons

A = original published V1; B = corrected Batch 1; C = merged Batch 2A; D = proposed Batch 2B. All 691 players are recalculated in all four states, using independently transcribed raw UUID counts, rational exposure/rates, frozen percentiles, ratings, eligibility and Formula B. Original inputs reproduce published values; B and C reproduce sealed prior diagnostics. All 14,979 historical contribution keys remain accounted for; C and D both contain 14,978 active keys after Batch 2A’s proved Juanfran nonappearance removal.

| Player | A minutes | B minutes | C minutes | D minutes | C Formula B | D Formula B | D − C |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Jordan Ferri (3118) | 2521.21215000 | 2521.21215000 | 2521.21215000 | 2569.42861667 | 67.767694932174 | 67.748336809559 | -0.019358122615 |
| Bryan Dabo (3421) | 2938.70171667 | 2938.70171667 | 2938.70171667 | 2986.73143333 | 63.831595208569 | 63.613019282785 | -0.218575925784 |
| Sung-Yeung Ki (3605) | 1850.45233333 | 1850.45233333 | 1850.45233333 | 1946.95986667 | 66.389950088494 | 66.610645051674 | 0.220694963180 |
| Ashley Williams (3644) | 3283.19335000 | 3283.19335000 | 3283.19335000 | 3379.70088333 | 70.288203449489 | 70.045766834031 | -0.242436615458 |
| Joe Ledley (4817) | 1039.63538333 | 1039.63538333 | 1039.63538333 | 1049.83330000 | 60.697791141618 | 60.567484175795 | -0.130306965823 |
| Valon Behrami (5540) | 1153.27396667 | 1245.93873333 | 1245.93873333 | 1295.97046667 | 68.166399912616 | 67.417730441470 | -0.748669471146 |
| Manuel Trigueros Muñoz (6771) | 2163.83741667 | 2163.83741667 | 2163.83741667 | 2211.91776667 | 66.261534354911 | 66.391610628828 | 0.130076273917 |
| Luca Rigoni (7461) | 1670.67316667 | 1765.47420000 | 1765.47420000 | 1814.44478333 | 56.449456710965 | 56.089382811668 | -0.360073899297 |
| Dario Dainelli (7771) | 1372.27791667 | 1372.27791667 | 1372.27791667 | 1421.19761667 | 69.472143623614 | 69.645764304780 | 0.173620681165 |
| José Antonio García Rabasco (24149) | 2176.96448333 | 2176.96448333 | 2176.96448333 | 2224.60953333 | 67.971389180015 | 68.166896961916 | 0.195507781901 |

Largest absolute Formula B changes: Valon Behrami (-0.748669471146); Luca Rigoni (-0.360073899297); Ashley Williams (-0.242436615458). Ratings are not assumed to increase.

### Attribute, numerator and denominator alignment

The following compares C → D. Rates use only accepted action UUIDs and their matching supported exposure. Press resistance remains successful pressured actions / attempted pressured actions, independently of elapsed minutes. CSV population records retain all four states, exact rates, per-attribute supported/excluded match IDs, attempts, counts, exposure, ratings and percentiles.

| Player | Attribute | Numerator (press attempts) | Supported minutes | Exact value | Rating | Percentile |
| --- | --- | --- | --- | --- | --- | --- |
| 3118 | tackles | 35 → 35 | 2521.21215000 → 2569.42861667 | `21000000/16808081` → `189000000/154165717` | 59.277462184922 → 58.883382592145 | 32.000000000000 → 29.600000000000 |
| 3118 | interceptions | 6 → 7 | 2521.21215000 → 2569.42861667 | `3600000/16808081` → `37800000/154165717` | 49.452519185261 → 50.131808264664 | 0.800000000000 → 1.600000000000 |
| 3118 | recoveries | 156 → 159 | 2521.21215000 → 2569.42861667 | `93600000/16808081` → `858600000/154165717` | 67.671059541647 → 67.676421923207 | 62.096774193548 → 62.096774193548 |
| 3118 | press_resistance | 270/346 → 270/346 | 2521.21215000 → 2569.42861667 | `13500/173` → `13500/173` | 73.034927692228 → 73.034927692228 | 79.200000000000 → 79.200000000000 |
| 3118 | progressive_passing | 125 → 127 | 2521.21215000 → 2569.42861667 | `75000000/16808081` → `685800000/154165717` | 73.792932848412 → 73.695440955241 | 83.200000000000 → 82.400000000000 |
| 3421 | tackles | 47 → 47 | 2938.70171667 → 2986.73143333 | `253800000/176322103` → `126900000/89601943` | 62.471244129189 → 62.082178674818 | 45.600000000000 → 44.800000000000 |
| 3421 | interceptions | 27 → 27 | 2938.70171667 → 2986.73143333 | `145800000/176322103` → `72900000/89601943` | 62.875157522947 → 62.583854252508 | 44.000000000000 → 43.200000000000 |
| 3421 | recoveries | 186 → 187 | 2938.70171667 → 2986.73143333 | `1004400000/176322103` → `504900000/89601943` | 68.847797914064 → 68.281102172947 | 66.935483870968 → 62.903225806452 |
| 3421 | press_resistance | 280/446 → 280/446 | 2938.70171667 → 2986.73143333 | `14000/223` → `14000/223` | 49.495219662642 → 49.495219662642 | 8.000000000000 → 8.000000000000 |
| 3421 | progressive_passing | 106 → 109 | 2938.70171667 → 2986.73143333 | `572400000/176322103` → `294300000/89601943` | 65.128062976469 → 65.400276051648 | 58.400000000000 → 59.200000000000 |
| 3605 | tackles | 14 → 15 | 1850.45233333 → 1946.95986667 | `540000/793051` → `10125000/14602199` | 49.722201663057 → 49.931870504269 | 4.000000000000 → 4.000000000000 |
| 3605 | interceptions | 10 → 12 | 1850.45233333 → 1946.95986667 | `2700000/5551357` → `8100000/14602199` | 55.415243548596 → 56.912435041827 | 17.600000000000 → 22.400000000000 |
| 3605 | recoveries | 106 → 111 | 1850.45233333 → 1946.95986667 | `28620000/5551357` → `74925000/14602199` | 63.861284432078 → 63.636159642637 | 44.354838709677 → 42.741935483871 |
| 3605 | press_resistance | 156/191 → 156/191 | 1850.45233333 → 1946.95986667 | `15600/191` → `15600/191` | 78.653056961680 → 78.653056961680 | 93.600000000000 → 93.600000000000 |
| 3605 | progressive_passing | 72 → 76 | 1850.45233333 → 1946.95986667 | `19440000/5551357` → `51300000/14602199` | 66.949077659916 → 67.029774911766 | 65.600000000000 → 66.400000000000 |
| 3644 | tackles | 43 → 44 | 3283.19335000 → 3379.70088333 | `77400000/65663867` → `237600000/202782053` | 71.429727896346 → 71.228775087092 | 73.394495412844 → 71.559633027523 |
| 3644 | interceptions | 40 → 40 | 3283.19335000 → 3379.70088333 | `72000000/65663867` → `216000000/202782053` | 72.730743707833 → 71.790879062783 | 77.064220183486 → 76.146788990826 |
| 3644 | recoveries | 105 → 106 | 3283.19335000 → 3379.70088333 | `189000000/65663867` → `572400000/202782053` | 60.244493196991 → 59.676681384579 | 34.259259259259 → 33.333333333333 |
| 3644 | press_resistance | 147/211 → 147/211 | 3283.19335000 → 3379.70088333 | `14700/211` → `14700/211` | 72.179041422337 → 72.179041422337 | 76.851851851852 → 76.851851851852 |
| 3644 | progressive_passing | 117 → 124 | 3283.19335000 → 3379.70088333 | `210600000/65663867` → `669600000/202782053` | 67.425500550577 → 68.206076571721 | 71.559633027523 → 74.311926605505 |
| 4817 | tackles | 13 → 13 | 1039.63538333 → 1049.83330000 | `70200000/62378123` → `11700000/10498333` | 57.193157069168 → 57.009410227695 | 20.800000000000 → 20.800000000000 |
| 4817 | interceptions | 12 → 12 | 1039.63538333 → 1049.83330000 | `64800000/62378123` → `10800000/10498333` | 67.517884427653 → 67.296822191144 | 66.400000000000 → 65.600000000000 |
| 4817 | recoveries | 32 → 32 | 1039.63538333 → 1049.83330000 | `172800000/62378123` → `28800000/10498333` | 41.871320113486 → 41.623243904258 | 0.000000000000 → 0.000000000000 |
| 4817 | press_resistance | 54/72 → 54/72 | 1039.63538333 → 1049.83330000 | `75` → `75` | 68.351985776231 → 68.351985776231 | 62.800000000000 → 62.800000000000 |
| 4817 | progressive_passing | 15 → 15 | 1039.63538333 → 1049.83330000 | `81000000/62378123` → `13500000/10498333` | 51.246405844357 → 51.156509727834 | 0.000000000000 → 0.000000000000 |
| 5540 | tackles | 37 → 37 | 1245.93873333 → 1295.97046667 | `49950000/18689081` → `49950000/19439557` | 83.200465276173 → 81.466174361910 | 92.800000000000 → 92.800000000000 |
| 5540 | interceptions | 15 → 15 | 1245.93873333 → 1295.97046667 | `20250000/18689081` → `20250000/19439557` | 68.497004773386 → 67.580640250394 | 69.600000000000 → 66.400000000000 |
| 5540 | recoveries | 68 → 71 | 1245.93873333 → 1295.97046667 | `91800000/18689081` → `95850000/19439557` | 61.616121490783 → 61.788598303466 | 38.709677419355 → 39.516129032258 |
| 5540 | press_resistance | 73/107 → 73/107 | 1245.93873333 → 1295.97046667 | `7300/107` → `7300/107` | 57.896124809363 → 57.896124809363 | 20.800000000000 → 20.800000000000 |
| 5540 | progressive_passing | 17 → 17 | 1245.93873333 → 1295.97046667 | `22950000/18689081` → `22950000/19439557` | 50.743661168562 → 50.405796882007 | 0.000000000000 → 0.000000000000 |
| 6771 | tackles | 32 → 32 | 2163.83741667 → 2211.91776667 | `34560000/25966049` → `86400000/66357533` | 60.648511277686 → 60.162226737168 | 36.800000000000 → 33.600000000000 |
| 6771 | interceptions | 18 → 18 | 2163.83741667 → 2211.91776667 | `19440000/25966049` → `48600000/66357533` | 61.161472662645 → 60.804964257644 | 40.000000000000 → 39.200000000000 |
| 6771 | recoveries | 118 → 124 | 2163.83741667 → 2211.91776667 | `127440000/25966049` → `334800000/66357533` | 61.579137518348 → 62.846269084510 | 38.709677419355 → 41.129032258065 |
| 6771 | press_resistance | 184/245 → 184/245 | 2163.83741667 → 2211.91776667 | `3680/49` → `3680/49` | 68.509449129286 → 68.509449129286 | 64.000000000000 → 64.000000000000 |
| 6771 | progressive_passing | 101 → 103 | 2163.83741667 → 2211.91776667 | `109080000/25966049` → `278100000/66357533` | 71.930908472514 → 71.860090724137 | 77.600000000000 → 76.800000000000 |
| 7461 | tackles | 21 → 22 | 1765.47420000 → 1814.44478333 | `150000/140117` → `118800000/108866687` | 56.271042543886 → 56.619125696747 | 18.400000000000 → 18.400000000000 |
| 7461 | interceptions | 11 → 11 | 1765.47420000 → 1814.44478333 | `550000/980819` → `59400000/108866687` | 57.044859702181 → 56.713311954729 | 22.400000000000 → 22.400000000000 |
| 7461 | recoveries | 90 → 90 | 1765.47420000 → 1814.44478333 | `4500000/980819` → `486000000/108866687` | 58.629574688188 → 57.488017347435 | 24.193548387097 → 20.161290322581 |
| 7461 | press_resistance | 82/131 → 82/131 | 1765.47420000 → 1814.44478333 | `8200/131` → `8200/131` | 49.209971292271 → 49.209971292271 | 6.400000000000 → 6.400000000000 |
| 7461 | progressive_passing | 39 → 40 | 1765.47420000 → 1814.44478333 | `1950000/980819` → `216000000/108866687` | 56.161091606391 → 56.132182334525 | 17.600000000000 → 17.600000000000 |
| 7771 | tackles | 10 → 10 | 1275.33196667 → 1324.25166667 | `27000000/38259959` → `540000/794551` | 57.906428457983 → 57.161139294482 | 25.688073394495 → 24.770642201835 |
| 7771 | interceptions | 12 → 12 | 1275.33196667 → 1324.25166667 | `32400000/38259959` → `648000/794551` | 65.236690245265 → 64.297637280408 | 54.128440366972 → 50.458715596330 |
| 7771 | recoveries | 71 → 76 | 1275.33196667 → 1324.25166667 | `191700000/38259959` → `4104000/794551` | 82.034665029994 → 83.615875459295 | 96.296296296296 → 96.296296296296 |
| 7771 | press_resistance | 45/69 → 45/69 | 1275.33196667 → 1324.25166667 | `1500/23` → `1500/23` | 66.235688621495 → 66.235688621495 | 49.074074074074 → 49.074074074074 |
| 7771 | progressive_passing | 38 → 39 | 1275.33196667 → 1324.25166667 | `102600000/38259959` → `2106000/794551` | 63.098940429273 → 62.842920840584 | 47.706422018349 → 45.871559633028 |
| 24149 | tackles | 35 → 36 | 2176.96448333 → 2224.60953333 | `189000000/130617869` → `48600000/33369143` | 62.598277950356 → 62.757392470110 | 45.600000000000 → 46.400000000000 |
| 24149 | interceptions | 23 → 23 | 2176.96448333 → 2224.60953333 | `124200000/130617869` → `31050000/33369143` | 65.590944742633 → 65.144812371818 | 63.200000000000 → 59.200000000000 |
| 24149 | recoveries | 115 → 117 | 2176.96448333 → 2224.60953333 | `621000000/130617869` → `157950000/33369143` | 60.162911747915 → 59.970128342192 | 33.064516129032 → 33.064516129032 |
| 24149 | press_resistance | 148/191 → 148/191 | 2176.96448333 → 2224.60953333 | `14800/191` → `14800/191` | 72.189639747281 → 72.189639747281 | 77.600000000000 → 77.600000000000 |
| 24149 | progressive_passing | 99 → 105 | 2176.96448333 → 2224.60953333 | `534600000/130617869` → `141750000/33369143` | 71.161101759836 → 72.266342819988 | 76.800000000000 → 79.200000000000 |

### Ranking and position implications

Ranking eligibility changes under frozen membership: **0**. Comparison-group changes: **0**. Dominant fine-position changes after both batches’ recovered exposure: `[{"player_id": 5540, "before": ["CM"], "after": ["DM"]}, {"player_id": 7461, "before": ["CM"], "after": ["DM"]}]`. These remain diagnostic metadata; frozen CB/MID groups are unchanged.

Players clearing other checked conditions while still lacking existing frozen membership: `[3118, 3421, 4817, 6771, 24149]`. This is a future reference-membership question, not admission to current rankings. No comparison population is refitted.

| Player | Remaining D exclusions |
| --- | --- |
| Jordan Ferri (3118) | tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER |
| Bryan Dabo (3421) | tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER |
| Sung-Yeung Ki (3605) | INCOMPLETE_OBSERVED_EXPOSURE; tackles:NOT_NORMAL_REFERENCE_CANDIDATE; tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; tackles:INCOMPLETE_METRIC_SCOPE; tackles:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; interceptions:NOT_NORMAL_REFERENCE_CANDIDATE; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:INCOMPLETE_METRIC_SCOPE; interceptions:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; recoveries:NOT_NORMAL_REFERENCE_CANDIDATE; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:INCOMPLETE_METRIC_SCOPE; recoveries:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; press_resistance:NOT_NORMAL_REFERENCE_CANDIDATE; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:NOT_NORMAL_REFERENCE_CANDIDATE; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:INCOMPLETE_METRIC_SCOPE; progressive_passing:FIXTURE_SCOPE_NOT_FULLY_ALIGNED |
| Ashley Williams (3644) | INCOMPLETE_OBSERVED_EXPOSURE; tackles:NOT_NORMAL_REFERENCE_CANDIDATE; tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; tackles:INCOMPLETE_METRIC_SCOPE; tackles:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; interceptions:NOT_NORMAL_REFERENCE_CANDIDATE; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:INCOMPLETE_METRIC_SCOPE; interceptions:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; recoveries:NOT_NORMAL_REFERENCE_CANDIDATE; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:INCOMPLETE_METRIC_SCOPE; recoveries:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; press_resistance:NOT_NORMAL_REFERENCE_CANDIDATE; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:NOT_NORMAL_REFERENCE_CANDIDATE; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:INCOMPLETE_METRIC_SCOPE; progressive_passing:FIXTURE_SCOPE_NOT_FULLY_ALIGNED |
| Joe Ledley (4817) | tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER |
| Valon Behrami (5540) | INCOMPLETE_OBSERVED_EXPOSURE; tackles:NOT_NORMAL_REFERENCE_CANDIDATE; tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; tackles:INCOMPLETE_METRIC_SCOPE; tackles:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; interceptions:NOT_NORMAL_REFERENCE_CANDIDATE; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:INCOMPLETE_METRIC_SCOPE; interceptions:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; recoveries:NOT_NORMAL_REFERENCE_CANDIDATE; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:INCOMPLETE_METRIC_SCOPE; recoveries:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; press_resistance:NOT_NORMAL_REFERENCE_CANDIDATE; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:NOT_NORMAL_REFERENCE_CANDIDATE; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:INCOMPLETE_METRIC_SCOPE; progressive_passing:FIXTURE_SCOPE_NOT_FULLY_ALIGNED |
| Manuel Trigueros Muñoz (6771) | tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER |
| Luca Rigoni (7461) | INCOMPLETE_OBSERVED_EXPOSURE; tackles:NOT_NORMAL_REFERENCE_CANDIDATE; tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; tackles:INCOMPLETE_METRIC_SCOPE; tackles:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; interceptions:NOT_NORMAL_REFERENCE_CANDIDATE; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:INCOMPLETE_METRIC_SCOPE; interceptions:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; recoveries:NOT_NORMAL_REFERENCE_CANDIDATE; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:INCOMPLETE_METRIC_SCOPE; recoveries:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; press_resistance:NOT_NORMAL_REFERENCE_CANDIDATE; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:NOT_NORMAL_REFERENCE_CANDIDATE; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:INCOMPLETE_METRIC_SCOPE; progressive_passing:FIXTURE_SCOPE_NOT_FULLY_ALIGNED |
| Dario Dainelli (7771) | INCOMPLETE_OBSERVED_EXPOSURE; INVALID_OR_PENDING_FIXTURE_SCOPE; tackles:NOT_NORMAL_REFERENCE_CANDIDATE; tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; tackles:INCOMPLETE_METRIC_SCOPE; tackles:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; tackles:METRIC_EXPOSURE_NOT_COMPLETE_900_MINUTES; interceptions:NOT_NORMAL_REFERENCE_CANDIDATE; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:INCOMPLETE_METRIC_SCOPE; interceptions:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; interceptions:METRIC_EXPOSURE_NOT_COMPLETE_900_MINUTES; recoveries:NOT_NORMAL_REFERENCE_CANDIDATE; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:INCOMPLETE_METRIC_SCOPE; recoveries:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; recoveries:METRIC_EXPOSURE_NOT_COMPLETE_900_MINUTES; press_resistance:NOT_NORMAL_REFERENCE_CANDIDATE; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; press_resistance:INCOMPLETE_METRIC_SCOPE; press_resistance:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; press_resistance:METRIC_EXPOSURE_NOT_COMPLETE_900_MINUTES; progressive_passing:NOT_NORMAL_REFERENCE_CANDIDATE; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:INCOMPLETE_METRIC_SCOPE; progressive_passing:FIXTURE_SCOPE_NOT_FULLY_ALIGNED; progressive_passing:METRIC_EXPOSURE_NOT_COMPLETE_900_MINUTES |
| José Antonio García Rabasco (24149) | tackles:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; interceptions:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; recoveries:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; press_resistance:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER; progressive_passing:NOT_EXISTING_VERIFIED_ATTRIBUTE_MEMBER |

## Whole-population preservation and investigated effects

All **14,537 Batch 2A accepted appearances** retain identical validation results and exact intervals; the **91 Batch 1 recoveries** and Pallois’s Batch 2A recovery remain intact. Juanfran and the three supplemental unused-roster bench cards remain nonappearances with retained disciplinary provenance. D has **14,547 supported published appearances** and **431 active appearances with unresolved/unsupported exposure**. All other **681 published players** are exactly unchanged from C across metrics, scores, identity, eligibility and exclusions. Unexpected published changes: **0**.

A general source rule also corroborates **26 nonpublished roster appearances**. The first was Łukasz Fabiański `3262/3754047`, sharing the original zero-clock XI/shift with Ki and Williams. The initial all-roster assertion stopped on this case; independent event/lineup geometry and source positions established why it changed. Every supplemental row is checked by the same independent raw-source reconstruction and recorded below; none enters the 691-player score calculation, reference membership or published JSON.

| Nonpublished actor | Fixture | Exact seconds |
| --- | --- | ---: |
| Łukasz Fabiański (3262) | 3754047 | 1447613/250 |
| Kyle Naughton (3340) | 3754047 | 1447613/250 |
| André Ayew Pelé (3347) | 3754047 | 1447613/250 |
| Wayne Routledge (3449) | 3754047 | 21842/5 |
| Gylfi Þór Sigurðsson (3944) | 3754047 | 1447613/250 |
| Kyle Bartley (4726) | 3754047 | 1447613/250 |
| Neil Taylor (9627) | 3754047 | 1447613/250 |
| Éderzito António Macedo Lopes (15996) | 3754047 | 832447/200 |
| Luis Antonio Valencia Mosquera (3267) | 3754171 | 706173/250 |
| Martin Kelly (3448) | 3754181 | 367052/125 |
| Hugo Miguel Almeida Costa Lopes (20064) | 3825570 | 1473623/500 |
| Alen Halilović (6926) | 3825596 | 4040441/1000 |
| Alberto García Cabrera (11537) | 3825596 | 5772819/1000 |
| Alejandro Menéndez Díez (23994) | 3825596 | 5772819/1000 |
| Ricky van Wolfswinkel (27348) | 3825750 | 2826147/1000 |
| Juan Rafael Fuentes Hernández (4741) | 3825757 | 2826653/1000 |
| Pau López Sabata (6792) | 3825767 | 2829177/1000 |
| João Pedro Cavaco Cancelo (7005) | 3825899 | 1441009/500 |
| Roberto Inglese (7043) | 3879662 | 2941601/1000 |
| Paul-José M''Poku Ebunge (18946) | 3879748 | 3032117/1000 |
| Maicon Douglas Sisenando (19299) | 3879845 | 1444787/500 |
| Joris Gnagnon (18921) | 3900583 | 2884239/1000 |
| Evaeverson Lemos da Silva Brandão (401541) | 3900611 | 72014/25 |
| Vincent Bessat (2992) | 3900620 | 593913/200 |
| Salvatore Sirigu (7469) | 3901208 | 2878663/1000 |
| Adrien Thomasson (3375) | 3901222 | 566339/200 |

These source-only recoveries are retained leads for a separate future upstream admission assessment. No future reference-membership claim or new score is made for those actors.

Ramos (both cases), Francis, Mendy, Pajot and all four Batch 1 residual cases retain their previous rejection issues. All three clean permanent-exit policy cases remain withheld. Fernandinho’s source-name restriction and metric-specific scope/geometry restrictions remain unchanged. No unsupported Tactical Shift alone becomes an entry. No contradictory source is clipped, guessed or silently replaced.

Independent raw UUID inventory: **5,436,699 original events / 1,551 fixtures**, duplicate/missing/extra UUIDs **0/0/0**. A second disk-backed inventory built directly from hash-bound original bytes agrees bidirectionally with the replay UUID inventory. All **74,895 raw metric UUID sets** and **3,036,652 delivered event contexts** are checked in the replay. The additional checker verifies **3,626,433 Parquet projections** and all **2,514 frozen-reference candidate/membership predicates**, with zero discrepancies.

Frozen semantic fingerprint remains `403c1d9ab93defecd4f03e98e98c6b71a2e53c603c4e38b16c1e884038457efd`. Public ratings SHA256 remains `9a5d101cd9f15af456f58c39a7053a22db16ac99f2864bbf5252733fb97ecc2e`. Original source receipts and prior artifact hashes are rechecked before finalization; no data source/reference/population is rewritten.

## Tests and execution limits

| Verification | Passed | Failed | Skipped | Blocked | Deselected |
| --- | ---: | ---: | ---: | ---: | ---: |
| public_backend | 1095 | 0 | 0 | 0 | 0 |
| private_backend | 51 | 0 | 0 | 0 | 125 |
| targeted_regressions | 109 | 0 | 0 | 0 | 0 |
| original_source_regressions | 16 | 0 | 0 | 0 | 0 |
| retained_independent_regressions | 12 | 0 | 0 | 0 | 0 |
| identity_join_probes | 12 | 0 | 0 | 0 | 0 |
| public_frontend | 211 | 0 | 0 | 0 | 0 |
| private_frontend | 33 | 1 | 0 | 0 | 0 |
| production_build | 1 | 0 | 0 | 0 | 0 |
| independent_candidate_checks | 10 | 0 | 0 | 0 | 0 |
| full_population_replay | 1 | 0 | 0 | 0 | 0 |
| independent_uuid_conservation | 1 | 0 | 0 | 0 | 0 |
| raw_delivery_and_reference_checks | 1 | 0 | 0 | 0 | 0 |

The 30 new synthetic regressions are included in the public total; the 109 targeted cases overlap that total. The 16 retained-original tests include ten entry-candidate subcases, the Batch 2A cases and specific exclusions; subcases are not extra top-level unit tests. Private deselections are outside the declared suite and are not skips. The single private frontend failure is the previously reported badge-label expectation at `provisionalOvr.test.js:61` (case begins at line 44); no UI or numerical change was made to satisfy it.

Prior incomplete attempts remain preserved: initial source checks passed but receipt writing lacked its output directory; one synthetic chronology control failed before the proof included XI/boundary chronology; the original full replay exhausted memory; initial private backend import and public frontend esbuild failed during resource contention; private frontend initially lacked its ignored fixture/support modules. The large memory/setup command was declined at the prior usage limit and did not execute. Resumed edits were small and separately reviewed. The bounded replay uses fixture-scoped indexed reads from the immutable source DB plus a new disk-backed UUID primary key. The first bounded attempt then stopped on the investigated nonpublished goalkeeper scope assertion. The completed replay and final logs alone support the final numerical results. Earlier reports and attempts are not overwritten.

The independent path does not call the production entry proof. It retains its own original-event state machine and separately resolved lineup geometry. Same-provider source reconciliation does not resolve genuine contradictions or certify historically complete seasons.

## Reproduction

Use Python 3.13, retained sibling evidence workspaces and existing locked frontend dependencies. Output-generating commands refuse existing completed directories/files; use a fresh worktree or preserve each old output under a distinct attempt name before repeating. Private harness inputs are individually fingerprint-bound in the ignored provenance manifests.

```powershell
python -B -m pytest tests/test_source_backed_entry.py tests/test_off_field_cards.py tests/test_statsbomb_participation.py -q -p no:cacheprovider
python -B -m scripts.check_off_field_card_sources
python -B -m scripts.check_source_backed_entries
python -B -m scripts.verify_source_backed_entry_fix
python -B -m scripts.check_entry_uuid_conservation
python -B -m scripts.check_entry_uuid_conservation --compare-only
python -B -m scripts.run_backend_tests public -q
python -B audit-output/run-private-backend.py
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/test_independent_audit.py
python -B -c "import src, runpy; runpy.run_path('../Soccer-Impact-Engine-Index-player-data-integrity-audit/audit-output/full-player-audit-tests/identity_probes.py', run_name='__main__')"
python -B ../Soccer-Impact-Engine-Index-player-data-integrity-audit/scripts/audit_full_player_additional_checks.py --source-root ../Soccer-Impact-Engine-Index --checkout . --output audit-output/entry-additional
npm.cmd run test:public --prefix frontend
npm.cmd run test:private --prefix audit-output/private-suite-checkout/frontend
npm.cmd run build --prefix frontend
python -B -m scripts.finalize_source_backed_entry_fix
```

## Modified files and artifact inventory

- `docs/source-backed-entry-fix-report.md`
- `scripts/check_entry_uuid_conservation.py`
- `scripts/check_off_field_card_sources.py`
- `scripts/check_source_backed_entries.py`
- `scripts/finalize_source_backed_entry_fix.py`
- `scripts/verify_source_backed_entry_fix.py`
- `src/source_reconstruction.py`
- `src/statsbomb_participation.py`
- `tests/suite_inventory.json`
- `tests/test_source_backed_entry.py`

Required ignored outputs under `audit-output/source-backed-entry-fix/`: `appearance-comparison.csv`, `player-impact.csv`, `full-population-comparison.csv`, `entry-evidence.csv`, `summary.json`, `input-hashes.json`, `test-results.json`. Supplemental files include `all-appearance-comparison.csv`, baseline/pending diagnostic facts, the merged adapter snapshot, `uuid-conservation.sqlite`, `output-hashes.json` and `artifact-inventory.json`. Independent source/UUID evidence, additional raw/reference checks, private harness provenance, logs and failed attempts remain under `audit-output/`. Large files and source evidence remain ignored.

Recommended next correction batch: separately review the three source-corroborated permanent-exit support-policy cases, with explicit terminal-exit semantics and conflict regressions. Keep genuine source contradictions and nickname policy outside that batch. Published numerical changes and any new reference population require separate approval.
