# Player portrait sources and identity mapping

Retrieved 2026-11-13. All 691 profiles have locally stored portraits: 678 from FIFA 16, 12 from FIFA 17 and 1 from FIFA 18.

Portraits come from `https://cdn.sofifa.net/players/{six_digit_id_first_3}/{last_3}/16_240.png`, with 120px and 60px FIFA 16 fallbacks checked when unavailable. The 13 documented FIFA 17/18 fallbacks below fill unavailable FIFA 16 images. No images are generated or retouched. Requests used a browser User-Agent and the SoFIFA site Referer, spaced at least 0.4 seconds apart.

Stable FIFA IDs were matched to canonical names and the existing reviewed display aliases. Shared names, spelling variants and transliterations were reviewed against club context. Adjacent-year records confirm identities only: image editions are recorded below. The live website imports none of the FIFA scoring fields.

## Identity reference snapshots

Pinned public CSV sources from AMRYB/FIFA-Dashboard (SoFIFA-derived records). Only name, ID, club, date of birth and nationality fields were used locally; the source CSVs are not published with the website.

- https://raw.githubusercontent.com/AMRYB/FIFA-Dashboard/63dfdeccb80cf68d7cd116cbac88e206a0fe3e31/players_15.csv — SHA-256 `5766a7c044437862bbabfc838236630dd3fa535417f048d0bafcdd17b5d2f43e`
- https://raw.githubusercontent.com/AMRYB/FIFA-Dashboard/63dfdeccb80cf68d7cd116cbac88e206a0fe3e31/players_16.csv — SHA-256 `3c46151e0f99513bb3168044b1106ac3c4dca9be66d8baf05a5eed294be00c55`
- https://raw.githubusercontent.com/AMRYB/FIFA-Dashboard/63dfdeccb80cf68d7cd116cbac88e206a0fe3e31/players_17.csv — SHA-256 `87b8f293174321630844c48829dc866e4d14215ff3105a41c6e6cf466e644c9b`

## Reviewed fallbacks for unavailable FIFA 16 portraits

Player | Source player ID | FIFA ID | Reason
--- | --- | --- | ---
Alberto Grassi | 6952 | 220475 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Amadou Diawara | 8284 | 230613 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Cédric Yambéré | 3779 | 225934 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Frédéric Guilbert | 2946 | 227222 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Gonzalo Escalante | 6712 | 219391 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Hotaru Yamaguchi | 5694 | 222987 | FIFA 18 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Issa Diop | 4349 | 231633 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Jaba Kankava | 46801 | 167194 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
László Kleinheisler | 16502 | 231493 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Marcel  Hilßner | 47881 | 231197 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Pablo Fornals Malla | 6764 | 226456 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Pablo Nascimento Castro | 4542 | 201315 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels
Petros Matheus dos Santos Araújo | 27346 | 222709 | FIFA 17 fallback; FIFA 16 unavailable at 240, 120 or 60 pixels

## Reviewed mapping

Source IDs below belong to the project; FIFA IDs belong to the portrait source. Each successful image has a separately pinned hash in `build/playerPortraitAssets.js`.

Project player ID | Canonical name | FIFA ID | Reference name / club | Evidence | Image
--- | --- | --- | --- | --- | ---
2936 | Christophe Kerbrat | 204338 | Christophe Kerbrat / En Avant de Guingamp | FIFA 16 CSV: exact_unique_full_name | `204338.png`
2943 | Lucas Deaux | 178051 | Lucas Deaux / FC Nantes | FIFA 16 CSV: exact_unique_full_name | `178051.png`
2946 | Frédéric Guilbert | 227222 | Frédéric Guilbert / FC Girondins de Bordeaux | FIFA 16 CSV: exact_unique_full_name | `227222.png`
2950 | Jonas Martin | 197813 | Jonas Martin / Montpellier HSC | FIFA 16 CSV: exact_unique_full_name | `197813.png`
2953 | Abdou Kader Mangane | 47860 | Abdou Kader Mangane / GFC Ajaccio | FIFA 16 CSV: exact_unique_full_name | `047860.png`
2959 | Julien Féret | 163804 | Julien Féret / Stade Malherbe Caen | FIFA 16 CSV: exact_unique_full_name | `163804.png`
2961 | Yann Bodiger | 224591 | Yann Bodiger / Toulouse Football Club | FIFA 16 CSV: exact_unique_full_name | `224591.png`
2971 | Romain Genevois | 181456 | Romain Genevois / OGC Nice | FIFA 16 CSV: exact_unique_full_name | `181456.png`
2979 | Jonathan Delaplace | 199195 | Jonathan Delaplace / Stade Malherbe Caen | FIFA 16 CSV: exact_unique_full_name | `199195.png`
2990 | Benjamin André | 190674 | Benjamin André / Stade Rennais FC | FIFA 16 CSV: exact_unique_full_name | `190674.png`
3004 | Oswaldo Augusto Vizcarrondo Araújo | 175462 | Oswaldo Augusto Vizcarrondo Araújo / FC Nantes | FIFA 16 CSV: exact_unique_full_name | `175462.png`
3011 | Daniel Congré | 163665 | Daniel Congré / Montpellier HSC | FIFA 16 CSV: exact_unique_full_name | `163665.png`
3022 | Fallou Diagne | 194196 | Fallou Diagne / Stade Rennais FC | FIFA 16 CSV: exact_unique_full_name | `194196.png`
3026 | Adrien Rabiot | 210008 | Adrien Rabiot / Paris Saint-Germain | FIFA 16 CSV: exact_unique_full_name | `210008.png`
3034 | Kamil Glik | 190547 | Kamil Glik / Torino | FIFA 16 CSV: exact_unique_full_name | `190547.png`
3036 | Alexis Blin | 222982 | Alexis Blin / Toulouse Football Club | FIFA 16 CSV: exact_unique_full_name | `222982.png`
3037 | Mousa Sidi Yaya Dembélé | 162240 | Moussa Sidi Yaya Dembélé / Tottenham Hotspur | FIFA identity reference CSVs; name variant and recorded club reviewed | `162240.png`
3041 | Ciaran Clark | 183129 | Ciaran Clark / Aston Villa | FIFA 16 CSV: exact_unique_full_name | `183129.png`
3044 | Chancel Mbemba Mangulu | 210897 | Chancel Mbemba / Newcastle United | FIFA 16 CSV: exact_unique_name | `210897.png`
3045 | Ismaël Traoré | 184873 | Ismaël Traoré / Angers SCO | FIFA 16 CSV: exact_unique_full_name | `184873.png`
3054 | Fernando Luiz Rosa | 135507 | Fernando Luiz Rosa / Manchester City | FIFA 16 CSV: exact_unique_full_name | `135507.png`
3057 | Jonjo Shelvey | 189165 | Jonjo Shelvey / Swansea City | FIFA 16 CSV: exact_unique_full_name | `189165.png`
3077 | Jan Vertonghen | 172871 | Jan Vertonghen / Tottenham Hotspur | FIFA 16 CSV: exact_unique_full_name | `172871.png`
3081 | Jamaal Lascelles | 203487 | Jamaal Lascelles / Newcastle United | FIFA 16 CSV: exact_unique_full_name | `203487.png`
3087 | Gnégnéri Yaya Touré | 20289 | Gnégnéri Yaya Touré / Manchester City | FIFA 16 CSV: exact_unique_full_name | `020289.png`
3090 | Nicolás Hernán Otamendi | 192366 | Nicolás Hernán Otamendi / Manchester City | FIFA 16 CSV: exact_unique_full_name | `192366.png`
3097 | Pascal Groß | 190765 | Pascal Groß / FC Ingolstadt 04 | FIFA 16 CSV: exact_unique_full_name | `190765.png`
3098 | Victor Wanyama | 188942 | Victor Wanyama / Southampton | FIFA 16 CSV: exact_unique_full_name | `188942.png`
3101 | Vincent Kompany | 139720 | Vincent Kompany / Manchester City | FIFA 16 CSV: exact_unique_full_name | `139720.png`
3103 | Milan Biševac | 178111 | Milan Biševac / Olympique Lyonnais | FIFA 16 CSV: exact_unique_full_name | `178111.png`
3118 | Jordan Ferri | 206306 | Jordan Ferri / Olympique Lyonnais | FIFA 16 CSV: exact_unique_full_name | `206306.png`
3121 | Moustapha Elhadji Diallo | 192673 | Mustapha Diallo / En Avant de Guingamp | FIFA 16 CSV: exact_unique_name | `192673.png`
3124 | Jérémy Sorbon | 167936 | Jérémy Sorbon / En Avant de Guingamp | FIFA 16 CSV: exact_unique_full_name | `167936.png`
3140 | François Bellugou | 181559 | François Bellugou / FC Lorient | FIFA 16 CSV: exact_unique_full_name | `181559.png`
3150 | Jaroslav Plašil | 112244 | Jaroslav Plašil / FC Girondins de Bordeaux | FIFA 16 CSV: exact_unique_full_name | `112244.png`
3160 | Rene Krhin | 192205 | Rene Krhin / Granada CF | FIFA 16 CSV: exact_unique_full_name | `192205.png`
3164 | Marcelo Antônio Guedes Filho | 180334 | Marcelo Antônio Guedes Filho / Hannover 96 | FIFA 16 CSV: exact_unique_full_name | `180334.png`
3166 | Marco Verratti | 199556 | Marco Verratti / Paris Saint-Germain | FIFA 16 CSV: exact_unique_full_name | `199556.png`
3167 | Antonio Rüdiger | 205452 | Antonio Rüdiger / Roma | FIFA 16 CSV: exact_unique_full_name | `205452.png`
3168 | João Filipe Iria Santos Moutinho | 162347 | João Filipe Iria Santos Moutinho / AS Monaco | FIFA 16 CSV: exact_unique_full_name | `162347.png`
3174 | Lévy Koffi Djidji | 203884 | Lévy Koffi Djidji / FC Nantes | FIFA 16 CSV: exact_unique_full_name | `203884.png`
3181 | Lassana Diarra | 163711 | Lassana Diarra / Olympique de Marseille | FIFA 16 CSV: exact_unique_full_name | `163711.png`
3185 | Thomas Mangani | 178160 | Thomas Mangani / Angers SCO | FIFA 16 CSV: exact_unique_full_name | `178160.png`
3189 | Étienne Didot | 49488 | Étienne Didot / Toulouse Football Club | FIFA 16 CSV: exact_unique_full_name | `049488.png`
3197 | Dante Bonfim da Costa Santos | 158625 | Dante Bonfim da Costa Santos / FC Bayern München | FIFA 15 CSV: exact_unique_full_name | `158625.png`
3200 | Renaud Cohade | 112365 | Renaud Cohade / AS Saint-Étienne | FIFA 16 CSV: exact_unique_full_name | `112365.png`
3211 | Florent Balmont | 52126 | Florent Balmont / LOSC Lille | FIFA 16 CSV: exact_unique_full_name | `052126.png`
3229 | Maxime Le Marchand | 192725 | Maxime Le Marchand / OGC Nice | FIFA 16 CSV: exact_unique_full_name | `192725.png`
3236 | Sergi Darder Moll | 202648 | Sergi Darder Moll / Málaga CF | FIFA 15 CSV: exact_unique_full_name | `202648.png`
3244 | John Stones | 203574 | John Stones / Everton | FIFA 16 CSV: exact_unique_full_name | `203574.png`
3250 | Edson André Sitoe | 196801 | Edson Andre Sitoe / Stade Rennais FC | FIFA 16 CSV: exact_unique_full_name | `196801.png`
3253 | Adil Rami | 183280 | Adil Rami / Sevilla FC | FIFA 16 CSV: exact_unique_full_name | `183280.png`
3256 | Nicolas Pallois | 199393 | Nicolas Pallois / FC Girondins de Bordeaux | FIFA 16 CSV: exact_unique_full_name | `199393.png`
3263 | Craig Cathcart | 180706 | Craig Cathcart / Watford | FIFA 16 CSV: exact_unique_full_name | `180706.png`
3272 | Oriol Romeu Vidal | 199576 | Oriol Romeu Vidal / Southampton | FIFA 16 CSV: exact_unique_full_name | `199576.png`
3277 | Yohan Cabaye | 167943 | Yohan Cabaye / Crystal Palace | FIFA 16 CSV: exact_unique_full_name | `167943.png`
3288 | Miguel Ángel Britos Cabrera | 189067 | Miguel Ángel Britos Cabrera / Watford | FIFA 16 CSV: exact_unique_full_name | `189067.png`
3290 | Federico Fernández | 201988 | Federico Fernández / Swansea City | FIFA 16 CSV: exact_unique_full_name | `201988.png`
3292 | Abdoulaye Doucouré | 208135 | Abdoulaye Doucouré / Stade Rennais FC | FIFA 16 CSV: exact_unique_full_name | `208135.png`
3295 | Thiago Emiliano da Silva | 164240 | Thiago Emiliano da Silva / Paris Saint-Germain | FIFA 16 CSV: exact_unique_full_name | `164240.png`
3296 | Marouane Fellaini-Bakkioui | 176944 | Marouane Fellaini-Bakkioui / Manchester United | FIFA 16 CSV: exact_unique_full_name | `176944.png`
3300 | Maya Yoshida | 191648 | 吉田 麻也 / Southampton | FIFA identity reference CSVs; name variant and recorded club reviewed | `191648.png`
3304 | Harry Arter | 184469 | Harry Arter / Bournemouth | FIFA 16 CSV: exact_unique_full_name | `184469.png`
3309 | Sebastian Prödl | 177578 | Sebastian Prödl / Watford | FIFA 16 CSV: exact_unique_full_name | `177578.png`
3311 | Daley Blind | 190815 | Daley Blind / Manchester United | FIFA 16 CSV: exact_unique_full_name | `190815.png`
3324 | Eric Bertrand Bailly | 225508 | Eric Bertrand Bailly / Villarreal CF | FIFA 16 CSV: exact_unique_full_name | `225508.png`
3328 | James Ward-Prowse | 205569 | James  Ward-Prowse / Southampton | FIFA 16 CSV: exact_unique_full_name | `205569.png`
3341 | Steve Cook | 193011 | Steve Cook / Bournemouth | FIFA 16 CSV: exact_unique_full_name | `193011.png`
3343 | Dan Gosling | 184749 | Dan Gosling / Bournemouth | FIFA 16 CSV: exact_unique_full_name | `184749.png`
3344 | Andrew Surman | 172768 | Andrew Surman / Bournemouth | FIFA 16 CSV: exact_unique_full_name | `172768.png`
3348 | Younousse Sankharé | 184271 | Younousse Sankharé / En Avant de Guingamp | FIFA 16 CSV: exact_unique_full_name | `184271.png`
3359 | Jean Michaël Seri | 216451 | Jean Michaël Seri / OGC Nice | FIFA 16 CSV: exact_unique_full_name | `216451.png`
3361 | Clément Grenier | 187924 | Clément Grenier / Olympique Lyonnais | FIFA 16 CSV: exact_unique_full_name | `187924.png`
3374 | Andrea Raggi | 163407 | Andrea Raggi / AS Monaco | FIFA 16 CSV: exact_unique_full_name | `163407.png`
3381 | Nemanja Matić | 191202 | Nemanja Matić / Chelsea | FIFA 16 CSV: exact_unique_full_name | `191202.png`
3389 | Eliaquim Mangala | 190531 | Eliaquim Mangala / Manchester City | FIFA 16 CSV: exact_unique_full_name | `190531.png`
3394 | Laurent Koscielny | 165229 | Laurent Koscielny / Arsenal | FIFA 16 CSV: exact_unique_full_name | `165229.png`
3406 | Jérémy Toulalan | 112253 | Jérémy Toulalan / AS Monaco | FIFA 16 CSV: exact_unique_full_name | `112253.png`
3407 | Scott Dann | 157665 | Scott Dann / Crystal Palace | FIFA 16 CSV: exact_unique_full_name | `157665.png`
3414 | Vincent Pajot | 198836 | Vincent Pajot / AS Saint-Étienne | FIFA 16 CSV: exact_unique_full_name | `198836.png`
3421 | Bryan Dabo | 199170 | Bryan Dabo / Montpellier HSC | FIFA 16 CSV: exact_unique_full_name | `199170.png`
3436 | Idrissa Gana Gueye | 193474 | Idrissa Gana Gueye / Aston Villa | FIFA 16 CSV: exact_unique_full_name | `193474.png`
3437 | Francis Joseph Coquelin | 189271 | Francis Coquelin / Arsenal | FIFA identity reference CSVs; name variant and recorded club reviewed | `189271.png`
3456 | Kurt Happy Zouma | 204311 | Kurt Happy Zouma / Chelsea | FIFA 16 CSV: exact_unique_full_name | `204311.png`
3462 | Jack Frank Porteous Cork | 169706 | Jack Cork / Swansea City | FIFA 16 CSV: exact_unique_name | `169706.png`
3464 | James McArthur | 171972 | James McArthur / Crystal Palace | FIFA 16 CSV: exact_unique_full_name | `171972.png`
3471 | Dejan Lovren | 195086 | Dejan Lovren / Liverpool | FIFA 16 CSV: exact_unique_full_name | `195086.png`
3473 | James Philip Milner | 138412 | James Philip Milner / Liverpool | FIFA 16 CSV: exact_unique_full_name | `138412.png`
3475 | Per Mertesacker | 53612 | Per Mertesacker / Arsenal | FIFA 16 CSV: exact_unique_full_name | `053612.png`
3478 | Francesc Fàbregas i Soler | 162895 | Francesc Fàbregas i Soler / Chelsea | FIFA 16 CSV: exact_unique_full_name | `162895.png`
3480 | Geoff Cameron | 186672 | Geoff Cameron / Stoke City | FIFA 16 CSV: exact_unique_full_name | `186672.png`
3482 | James Collins | 19292 | James  Collins / West Ham United | FIFA identity reference CSVs; name variant and recorded club reviewed | `019292.png`
3483 | Mamadou Sakho | 183285 | Mamadou Sakho / Liverpool | FIFA 16 CSV: exact_unique_full_name | `183285.png`
3490 | James Morrison | 162981 | James  Morrison / West Bromwich Albion | FIFA 16 CSV: exact_unique_full_name | `162981.png`
3493 | Emre Can | 208333 | Emre Can / Liverpool | FIFA 16 CSV: exact_unique_full_name | `208333.png`
3500 | Granit Xhaka | 199503 | Granit Xhaka / Borussia Mönchengladbach | FIFA 16 CSV: exact_unique_full_name | `199503.png`
3502 | Joël Andre Job Matip | 197061 | Joël Andre Job Matip / FC Schalke 04 | FIFA 16 CSV: exact_unique_full_name | `197061.png`
3517 | Aaron Ramsey | 186561 | Aaron Ramsey / Arsenal | FIFA 16 CSV: exact_unique_full_name | `186561.png`
3532 | Jordan Brian Henderson | 183711 | Jordan Brian Henderson / Liverpool | FIFA 16 CSV: exact_unique_full_name | `183711.png`
3545 | Luiz Gustavo Dias | 185221 | Luiz Gustavo Dias / VfL Wolfsburg | FIFA 16 CSV: exact_unique_full_name | `185221.png`
3549 | Romain Thomas | 184190 | Romain Thomas / Angers SCO | FIFA 16 CSV: exact_unique_full_name | `184190.png`
3570 | Pierre-Emile Højbjerg | 213648 | Pierre-Emile Højbjerg / FC Schalke 04 | FIFA 16 CSV: exact_unique_full_name | `213648.png`
3577 | Molla Wagué | 205243 | Molla Wagué / Udinese | FIFA 16 CSV: exact_unique_full_name | `205243.png`
3583 | Ashley Westwood | 189280 | Ashley Westwood / Aston Villa | FIFA 16 CSV: exact_unique_full_name | `189280.png`
3588 | Wesley Hoedt | 216774 | Wesley Hoedt / Lazio | FIFA 16 CSV: exact_unique_full_name | `216774.png`
3595 | Manuel Lanzini | 188988 | Manuel Lanzini / West Ham United | FIFA 16 CSV: exact_unique_full_name | `188988.png`
3596 | Gareth McAuley | 109852 | Gareth McAuley / West Bromwich Albion | FIFA 16 CSV: exact_unique_full_name | `109852.png`
3600 | Morgan Schneiderlin | 177358 | Morgan Schneiderlin / Manchester United | FIFA 16 CSV: exact_unique_full_name | `177358.png`
3605 | Sung-Yeung Ki | 180283 | 기성용 寄诚庸 / Swansea City | FIFA identity reference CSVs; name variant and recorded club reviewed | `180283.png`
3607 | James McCarthy | 188253 | James McCarthy / Everton | FIFA 16 CSV: exact_unique_full_name | `188253.png`
3608 | Simon Francis | 135883 | Simon Francis / Bournemouth | FIFA 16 CSV: exact_unique_full_name | `135883.png`
3610 | Roque Mesa Quevedo | 204277 | Roque Mesa Quevedo / UD Las Palmas | FIFA 17 CSV: exact_unique_full_name | `204277.png`
3626 | Ben Watson | 160292 | Ben Watson / Watford | FIFA 16 CSV: exact_unique_full_name | `160292.png`
3633 | Gareth Barry | 6826 | Gareth Barry / Everton | FIFA 16 CSV: exact_unique_full_name | `006826.png`
3636 | Charlie Adam | 155976 | Charlie Adam / Stoke City | FIFA 16 CSV: exact_unique_full_name | `155976.png`
3637 | Grzegorz Krychowiak | 197242 | Grzegorz Krychowiak / Sevilla FC | FIFA 16 CSV: exact_unique_full_name | `197242.png`
3638 | Shkodran Mustafi | 192227 | Shkodran Mustafi / Valencia CF | FIFA 16 CSV: exact_unique_full_name | `192227.png`
3644 | Ashley Williams | 163824 | Ashley Williams / Swansea City | FIFA 16 CSV: exact_unique_full_name | `163824.png`
3645 | Gary Cahill | 164468 | Gary Cahill / Chelsea | FIFA 16 CSV: exact_unique_full_name | `164468.png`
3662 | Danny Drinkwater | 186132 | Danny Drinkwater / Leicester City | FIFA 16 CSV: exact_unique_full_name | `186132.png`
3665 | Andrew Philip King | 186578 | Andy King / Leicester City | FIFA 16 CSV: exact_unique_name | `186578.png`
3669 | Virgil van Dijk | 203376 | Virgil van Dijk / Celtic | FIFA 15 CSV: exact_unique_full_name | `203376.png`
3674 | Vitorino Hilton da Silva | 153260 | Vitorino Hilton da Silva / Montpellier HSC | FIFA 16 CSV: exact_unique_full_name | `153260.png`
3677 | Bakary Adama Soumaoro | 200353 | Adama Soumaoro / LOSC Lille | FIFA 16 CSV: exact_unique_name | `200353.png`
3684 | Cheikhou Kouyaté | 186801 | Cheikhou Kouyaté / West Ham United | FIFA 16 CSV: exact_unique_full_name | `186801.png`
3693 | Damien Delaney | 159577 | Damien Delaney / Crystal Palace | FIFA 16 CSV: exact_unique_full_name | `159577.png`
3721 | Etienne Capoue | 178213 | Etienne Capoue / Watford | FIFA 16 CSV: exact_unique_full_name | `178213.png`
3753 | Pedro Filipe Teodósio Mendes | 200677 | Pedro Filipe Teodósio Mendes / Stade Rennais FC | FIFA 16 CSV: exact_unique_full_name | `200677.png`
3769 | Wesley Lautoa | 199511 | Wesley Lautoa / FC Lorient | FIFA 16 CSV: exact_unique_full_name | `199511.png`
3774 | Papiss Mison Djilobodji | 197937 | Papiss Mison Djilobodji / FC Nantes | FIFA 15 CSV: exact_unique_full_name | `197937.png`
3779 | Cédric Yambéré | 225934 | Cédric Yambéré / FC Girondins de Bordeaux | FIFA 16 CSV: exact_unique_full_name | `225934.png`
3813 | Wes Morgan | 136113 | Wes Morgan / Leicester City | FIFA 16 CSV: exact_unique_full_name | `136113.png`
3843 | Angelo Obinze Ogbonna | 183855 | Angelo Obinze Ogbonna / West Ham United | FIFA 16 CSV: exact_unique_full_name | `183855.png`
3874 | Mark Noble | 152879 | Mark Noble / West Ham United | FIFA 16 CSV: exact_unique_full_name | `152879.png`
3897 | Pedro Mba Obiang Avomo | 200054 | Pedro  Mba Obiang Avomo / West Ham United | FIFA 16 CSV: exact_unique_full_name | `200054.png`
3951 | Mario Lemina | 212811 | Mario Lemina / Juventus | FIFA 16 CSV: exact_unique_full_name | `212811.png`
3955 | Tiemoué Bakayoko | 219809 | Tiémoué Bakayoko / AS Monaco | FIFA 16 CSV: exact_unique_full_name | `219809.png`
3956 | David Luiz Moreira Marinho | 179944 | David Luiz Moreira Marinho / Paris Saint-Germain | FIFA 16 CSV: exact_unique_full_name | `179944.png`
3959 | Andreas Christensen | 213661 | Andreas Christensen / Borussia Mönchengladbach | FIFA 16 CSV: exact_unique_full_name | `213661.png`
3960 | José Miguel da Rocha Fonte | 171791 | José Miguel da Rocha Fonte / Southampton | FIFA 16 CSV: exact_unique_full_name | `171791.png`
3961 | N''Golo Kanté | 215914 | N'Golo Kanté / Leicester City | FIFA 16 CSV: exact_unique_full_name | `215914.png`
3967 | Claudio Ariel Yacob | 183893 | Claudio Ariel Yacob / West Bromwich Albion | FIFA 16 CSV: exact_unique_full_name | `183893.png`
4022 | Darren Fletcher | 138782 | Darren  Fletcher / West Bromwich Albion | FIFA 16 CSV: exact_unique_full_name | `138782.png`
4035 | Ryan Shawcross | 169596 | Ryan Shawcross / Stoke City | FIFA 16 CSV: exact_unique_full_name | `169596.png`
4174 | Ragnar Klavan | 140620 | Ragnar Klavan / FC Augsburg | FIFA 16 CSV: exact_unique_full_name | `140620.png`
4263 | Loïc Perrin | 159147 | Loïc Perrin / AS Saint-Étienne | FIFA 16 CSV: exact_unique_full_name | `159147.png`
4264 | Vincent Koziello | 225199 | Vincent Koziello / OGC Nice | FIFA 16 CSV: exact_unique_full_name | `225199.png`
4280 | Winston Reid | 176285 | Winston  Reid / West Ham United | FIFA 16 CSV: exact_unique_full_name | `176285.png`
4325 | Thiago Motta | 49370 | Thiago Motta / Paris Saint-Germain | FIFA 16 CSV: exact_unique_full_name | `049370.png`
4346 | Gilbert Gianelli Imbula Wanga | 197681 | Gilbert Gianelli Imbula Wanga / FC Porto | FIFA 16 CSV: exact_unique_full_name | `197681.png`
4349 | Issa Diop | 231633 | Issa Diop / Toulouse Football Club | FIFA 17 CSV: exact_unique_full_name | `231633.png`
4350 | Yannick Cahuzac | 167933 | Yannick Cahuzac / Bastia | https://fifaindex.com/players/167933-yannick-cahuzac/fifa16 | `167933.png`
4353 | Aymeric Laporte | 212218 | Aymeric  Laporte / Athletic Club de Bilbao | FIFA 16 CSV: exact_unique_full_name | `212218.png`
4372 | Marcos Aoás Corrêa | 207865 | Marcos  Aoás Corrêa / Paris Saint-Germain | FIFA 16 CSV: exact_unique_full_name | `207865.png`
4373 | Mathieu Bodmer | 51123 | Mathieu Bodmer / OGC Nice | FIFA 16 CSV: exact_unique_full_name | `051123.png`
4375 | Blaise Matuidi | 170890 | Blaise Matuidi / Paris Saint-Germain | FIFA 16 CSV: exact_unique_full_name | `170890.png`
4380 | Guillaume Gillet | 163186 | Guillaume Gillet / RSC Anderlecht | FIFA 16 CSV: exact_unique_full_name | `163186.png`
4386 | Damien Da Silva | 179789 | Damien Da Silva / Stade Malherbe Caen | FIFA 16 CSV: exact_unique_full_name | `179789.png`
4406 | Aymen Abdennour | 198076 | Aymen Abdennour / AS Monaco | FIFA 15 CSV: exact_unique_full_name | `198076.png`
4429 | Yann Gérard M''Vila | 187052 | Yann Gérard M'Vila / Sunderland | FIFA 16 CSV: exact_unique_full_name | `187052.png`
4430 | Neven Subotić | 183556 | Neven Subotić / Borussia Dortmund | FIFA 16 CSV: exact_unique_full_name | `183556.png`
4443 | Paul Baysse | 178031 | Paul Baysse / OGC Nice | FIFA 16 CSV: exact_unique_full_name | `178031.png`
4463 | Mapou Yanga-Mbiwa | 181560 | Mapou Yanga-M'Biwa / Olympique Lyonnais | FIFA 16 CSV: exact_unique_full_name | `181560.png`
4498 | Jean-Sylvain Claude Babin | 176693 | Jean-Sylvain Claude Babin / Granada CF | FIFA 16 CSV: exact_unique_full_name | `176693.png`
4506 | Nampalys Mendy | 198861 | Nampalys Mendy / OGC Nice | FIFA 16 CSV: exact_unique_full_name | `198861.png`
4542 | Pablo Nascimento Castro | 201315 | Pablo Nascimento Castro / FC Girondins de Bordeaux | FIFA 17 CSV: exact_unique_full_name | `201315.png`
4545 | Prince Oniangué | 183453 | Prince Oniangué / Stade de Reims | FIFA 16 CSV: exact_unique_full_name | `183453.png`
4629 | José Ramiro Funes Mori | 199667 | José Ramiro Funes Mori / River Plate | FIFA 15 CSV: exact_unique_full_name | `199667.png`
4631 | Leon Britton | 140415 | Leon Britton / Swansea City | FIFA 16 CSV: exact_unique_full_name | `140415.png`
4669 | William Jean Rémy | 188602 | William Rémy / Montpellier HSC | FIFA identity reference CSVs; name variant and recorded club reviewed | `188602.png`
4746 | Younes Kaboul | 163418 | Younès Kaboul / Sunderland | FIFA 16 CSV: exact_unique_full_name | `163418.png`
4751 | Michael Carrick | 21146 | Michael Carrick / Manchester United | FIFA 16 CSV: exact_unique_full_name | `021146.png`
4802 | Florentin Pogba | 198688 | Florentin Pogba / AS Saint-Étienne | FIFA 16 CSV: exact_unique_full_name | `198688.png`
4817 | Joe Ledley | 165190 | Joe Ledley / Crystal Palace | FIFA 16 CSV: exact_unique_full_name | `165190.png`
4926 | Francisco Román Alarcón Suárez | 197781 | Francisco Román Alarcón Suárez / Real Madrid | FIFA 16 CSV: exact_unique_full_name | `197781.png`
5110 | Henri Saivet | 183256 | Henri Saivet / FC Girondins de Bordeaux | FIFA 16 CSV: exact_unique_full_name | `183256.png`
5201 | Sergio Ramos García | 155862 | Sergio Ramos García / Real Madrid | FIFA 16 CSV: exact_unique_full_name | `sergio-ramos.png`
5202 | José Ignacio Fernández Iglesias | 200724 | José Ignacio Fernández Iglesias / Real Madrid | FIFA 16 CSV: exact_unique_full_name | `200724.png`
5203 | Sergio Busquets i Burgos | 189511 | Sergio Busquets i Burgos / FC Barcelona | FIFA 16 CSV: exact_unique_full_name | `sergio-busquets.png`
5204 | Bruno Miguel Borges Fernandes | 212198 | Bruno Miguel Borges Fernandes / Udinese | FIFA 16 CSV: exact_unique_full_name | `212198.png`
5208 | Thiago Alcântara do Nascimento | 189509 | Thiago Alcântara do Nascimento / FC Bayern München | FIFA 16 CSV: exact_unique_full_name | `189509.png`
5213 | Gerard Piqué Bernabéu | 152729 | Gerard Piqué Bernabéu / FC Barcelona | FIFA 16 CSV: exact_unique_full_name | `152729.png`
5216 | Andrés Iniesta Luján | 41 | Andrés Iniesta Luján / Barcelona | https://www.fifarosters.com/players?futid=41&player=41&v=16 | `000041.png`
5219 | Romain Saïss | 208295 | Romain Saïss / Angers SCO | FIFA 16 CSV: exact_unique_full_name | `208295.png`
5242 | Younès Belhanda | 193738 | Younès Belhanda / OGC Nice | FIFA 17 CSV: exact_unique_full_name | `193738.png`
5249 | Diego Roberto Godín Leal | 182493 | Diego Godín / Atlético Madrid | FIFA 16 CSV: exact_unique_name | `182493.png`
5255 | Matías Vecino Falero | 219985 | Matias Vecino / Fiorentina | FIFA 16 CSV: exact_unique_name | `219985.png`
5259 | José María Giménez de Vargas | 216460 | José María Giménez de Vargas / Atlético Madrid | FIFA 16 CSV: exact_unique_full_name | `216460.png`
5456 | Mateo Kovačić | 207410 | Mateo Kovačić / Real Madrid | FIFA 16 CSV: exact_unique_full_name | `207410.png`
5463 | Luka Modrić | 177003 | Luka Modrić / Real Madrid | FIFA 16 CSV: exact_unique_full_name | `177003.png`
5467 | Leon Aderemi Balogun | 188182 | Leon-Aderemi Balogun / 1. FSV Mainz 05 | FIFA 16 CSV: exact_unique_full_name | `188182.png`
5469 | Marcelo Brozović | 216352 | Marcelo Brozović / Inter | FIFA 16 CSV: exact_unique_full_name | `216352.png`
5470 | Ivan Rakitić | 168651 | Ivan Rakitić / FC Barcelona | FIFA 16 CSV: exact_unique_full_name | `168651.png`
5475 | John Michael Nchekwube Obinna | 164477 | John Michael Nchekwube Obinna / Chelsea | FIFA 16 CSV: exact_unique_full_name | `164477.png`
5480 | Corentin Tolisso | 219683 | Corentin Tolisso / Olympique Lyonnais | FIFA 16 CSV: exact_unique_full_name | `219683.png`
5485 | Raphaël Varane | 201535 | Raphaël Varane / Real Madrid | FIFA 16 CSV: exact_unique_full_name | `201535.png`
5489 | Mile Jedinak | 181483 | Mile Jedinák / Crystal Palace | FIFA 16 CSV: exact_unique_full_name | `181483.png`
5492 | Samuel Yves Umtiti | 205600 | Samuel Umtiti / Olympique Lyonnais | FIFA 16 CSV: exact_unique_name | `205600.png`
5506 | Javier Alejandro Mascherano | 142754 | Javier Alejandro Mascherano / FC Barcelona | FIFA 16 CSV: exact_unique_full_name | `142754.png`
5510 | Lucas Rodrigo Biglia | 158963 | Lucas Rodrigo Biglia / Lazio | FIFA 16 CSV: exact_unique_full_name | `158963.png`
5512 | Emil Hallfreðsson | 133249 | Emil Hallfreðsson / Hellas Verona | FIFA 16 CSV: exact_unique_full_name | `133249.png`
5537 | Fabian Lukas Schär | 210047 | Fabian Schär / TSG 1899 Hoffenheim | FIFA 16 CSV: exact_unique_name | `210047.png`
5539 | Carlos Henrique Casimiro | 200145 | Carlos Henrique Venancio Casimiro / Real Madrid | FIFA 16 CSV: exact_unique_name | `200145.png`
5540 | Valon Behrami | 161805 | Valon Behrami / Watford | FIFA 16 CSV: exact_unique_full_name | `161805.png`
5551 | João Miranda de Souza Filho | 168609 | João Miranda de Souza Filho / Inter | FIFA 16 CSV: exact_unique_full_name | `168609.png`
5554 | Blerim Džemaili | 138699 | Blerim Džemaili / Genoa | FIFA 16 CSV: exact_unique_full_name | `138699.png`
5566 | Sami Khedira | 179846 | Sami Khedira / Juventus | FIFA 16 CSV: exact_unique_full_name | `179846.png`
5572 | Mats Hummels | 178603 | Mats  Hummels / Borussia Dortmund | FIFA 16 CSV: exact_unique_full_name | `178603.png`
5574 | Toni Kroos | 182521 | Toni Kroos / Real Madrid | FIFA 16 CSV: exact_unique_full_name | `182521.png`
5579 | Joshua Kimmich | 212622 | Joshua Kimmich / FC Bayern München | FIFA 16 CSV: exact_unique_full_name | `212622.png`
5582 | Celso Borges Mora | 190799 | Celso Borges Mora / Deportivo de La Coruña | FIFA 16 CSV: exact_unique_full_name | `190799.png`
5584 | Giancarlo González Castro | 208379 | Giancarlo González Castro / Palermo | FIFA 16 CSV: exact_unique_full_name | `208379.png`
5589 | Sergej Milinković-Savić | 223848 | Sergej Milinković-Savić / Lazio | FIFA 16 CSV: exact_unique_full_name | `223848.png`
5598 | Óscar Esau Duarte Gaitán | 212772 | Óscar Duarte / Club Brugge KV | FIFA 16 CSV: exact_unique_name | `212772.png`
5605 | Oscar Hiljemark | 202944 | Oscar Hiljemark / Palermo | FIFA 16 CSV: exact_unique_full_name | `202944.png`
5624 | Albin Ekdal | 181318 | Albin Ekdal / Hamburger SV | FIFA 16 CSV: exact_unique_full_name | `181318.png`
5656 | Syam Ben Youssef | 207788 | Syam Ben Youssef / Stade Malherbe Caen | FIFA 16 CSV: exact_unique_full_name | `207788.png`
5660 | Piotr Zieliński | 210406 | Piotr Zieliński / Empoli | FIFA 16 CSV: exact_unique_full_name | `210406.png`
5664 | Salif Sané | 201956 | Salif Sané / Hannover 96 | FIFA 16 CSV: exact_unique_full_name | `201956.png`
5671 | Alfred John Momar N''Diaye | 188879 | Alfred John Momar N'Diaye / Real Betis | FIFA 16 CSV: exact_unique_full_name | `188879.png`
5675 | Kalidou Koulibaly | 201024 | Kalidou Koulibaly / Napoli | FIFA 16 CSV: exact_unique_full_name | `201024.png`
5676 | Cheikh N''Doye | 219470 | Cheikh N'Doye / Angers SCO | FIFA 16 CSV: exact_unique_full_name | `219470.png`
5678 | Jefferson Andrés Lerma Solís | 213991 | Jefferson Andrés Lerma Solís / Levante UD | FIFA 16 CSV: exact_unique_full_name | `213991.png`
5681 | Makoto Hasebe | 181098 | 長谷 部誠 / Eintracht Frankfurt | FIFA identity reference CSVs; name variant and recorded club reviewed | `181098.png`
5685 | Carlos Alberto Sánchez Moreno | 182882 | Carlos Sánchez / Aston Villa | FIFA 16 CSV: exact_unique_name | `182882.png`
5694 | Hotaru Yamaguchi | 222987 | Hotaru Yamaguchi / Hannover 96 | https://www.futwiz.com/player/history/222987 | `222987.png`
5695 | James David Rodríguez Rubio | 198710 | James David Rodríguez Rubio / Real Madrid | FIFA 16 CSV: exact_unique_full_name | `198710.png`
5737 | Steven N''Kemboanza Mike Christopher Nzonzi | 187936 | Steven N'Kemboanza Mike Christopher Nzonzi / Sevilla FC | FIFA 16 CSV: exact_unique_full_name | `187936.png`
5741 | Enzo Nicolás Pérez | 196432 | Enzo Pérez / Valencia CF | FIFA 16 CSV: exact_unique_name | `196432.png`
6039 | Sebastian Rudy | 189251 | Sebastian Rudy / TSG 1899 Hoffenheim | FIFA 16 CSV: exact_unique_full_name | `189251.png`
6300 | Sebastián Coates Nión | 197655 | Sebastián Coates Nión / Sunderland | FIFA 16 CSV: exact_unique_full_name | `197655.png`
6305 | Milan Badelj | 201144 | Milan Badelj / Fiorentina | FIFA 16 CSV: exact_unique_full_name | `201144.png`
6321 | Milos Veljkovic | 221354 | Milos Veljkovic / Tottenham Hotspur | FIFA 16 CSV: exact_unique_full_name | `221354.png`
6322 | Niklas Süle | 212190 | Niklas Süle / TSG 1899 Hoffenheim | FIFA 16 CSV: exact_unique_full_name | `212190.png`
6324 | Leon Goretzka | 209658 | Leon Goretzka / FC Schalke 04 | FIFA 16 CSV: exact_unique_full_name | `209658.png`
6359 | Johan Danon Djourou-Gbadjere | 162893 | Johan Danon Djourou-Gbadjere / Hamburger SV | FIFA 16 CSV: exact_unique_full_name | `162893.png`
6360 | Cristian Eduardo Zapata Valencia | 177983 | Cristian Eduardo Zapata Valencia / Milan | FIFA 16 CSV: exact_unique_full_name | `177983.png`
6376 | Stefan Savić | 204639 | Stefan Savić / Atlético Madrid | FIFA 16 CSV: exact_unique_full_name | `204639.png`
6379 | Sergi Roberto Carnicer | 199564 | Sergio Roberto Carnicer / FC Barcelona | FIFA 16 CSV: exact_unique_name | `199564.png`
6384 | Gabriel Fernández Arenas | 146954 | Gabriel Fernández Arenas / Atlético Madrid | FIFA 16 CSV: exact_unique_full_name | `146954.png`
6389 | Mikel San José Domínguez | 185132 | Mikel San José Domínguez / Athletic Club de Bilbao | FIFA 16 CSV: exact_unique_full_name | `185132.png`
6396 | Beñat Etxebarria Urkiaga | 177600 | Beñat Etxebarria Urkiaga / Athletic Club de Bilbao | FIFA 16 CSV: exact_unique_full_name | `177600.png`
6560 | Marc Muniesa Martínez | 192766 | Marc Muniesa Martínez / Stoke City | FIFA 16 CSV: exact_unique_full_name | `192766.png`
6561 | Luis Hernández Rodríguez | 205590 | Luis Hernández Rodríguez / Real Sporting de Gijón | FIFA 16 CSV: exact_unique_full_name | `205590.png`
6573 | Bernardo José Espinosa Zúñiga | 186521 | Bernardo José Espinosa Zúñiga / Real Sporting de Gijón | FIFA 16 CSV: exact_unique_full_name | `186521.png`
6577 | Zdravko Kuzmanović | 168650 | Zdravko Kuzmanović / FC Basel 1893 | FIFA 16 CSV: exact_unique_full_name | `168650.png`
6580 | José Luis García del Pozo | 201893 | José Luis García del Pozo / Málaga CF | FIFA 16 CSV: exact_unique_full_name | `201893.png`
6585 | Jeison Fabián Murillo Cerón | 201377 | Jeison Fabián Murillo Cerón / Inter | FIFA 16 CSV: exact_unique_full_name | `201377.png`
6589 | Geoffrey Kondogbia | 201455 | Geoffrey Kondogbia / Inter | FIFA 16 CSV: exact_unique_full_name | `201455.png`
6592 | Rúben Miguel Nunes Vezo | 215399 | Rúben Miguel Nunes Vezo / Valencia CF | FIFA 16 CSV: exact_unique_full_name | `215399.png`
6595 | Daniel Parejo Muñoz | 189513 | Daniel Parejo Muñoz / Valencia CF | FIFA 16 CSV: exact_unique_full_name | `189513.png`
6599 | Rubén Salvador Pérez Del Mármol | 190156 | Rubén Salvador Pérez del Mármol / Granada CF | FIFA 16 CSV: exact_unique_full_name | `190156.png`
6614 | Alexis Ruano Delgado | 135742 | Alexis Ruano Delgado / Getafe CF | FIFA 16 CSV: exact_unique_full_name | `135742.png`
6622 | Tomás Pina Isla | 198368 | Tomás Pina Isla / Villarreal CF | FIFA 16 CSV: exact_unique_full_name | `198368.png`
6631 | Mathieu Flamini | 156722 | Mathieu Flamini / Arsenal | FIFA 16 CSV: exact_unique_full_name | `156722.png`
6633 | Markel Bergara Larrañaga | 155984 | Markel Bergara Larrañaga / Real Sociedad | FIFA 16 CSV: exact_unique_full_name | `155984.png`
6647 | Zouhair Feddal | 205705 | Zouhair Feddal / Levante UD | FIFA 16 CSV: exact_unique_full_name | `205705.png`
6648 | Aïssa Mandi | 201143 | Aïssa Mandi / Stade de Reims | FIFA 16 CSV: exact_unique_full_name | `201143.png`
6659 | Víctor Camarasa Ferrando | 219571 | Víctor Camarasa Ferrando / Levante UD | FIFA 16 CSV: exact_unique_full_name | `219571.png`
6665 | Íñigo Martínez Berridi | 204525 | Íñigo Martínez Berridi / Real Sociedad | FIFA 16 CSV: exact_unique_full_name | `204525.png`
6671 | Asier Illarramendi Andonegi | 190584 | Asier Illarramendi Andonegi / Real Sociedad | FIFA 16 CSV: exact_unique_full_name | `190584.png`
6697 | Daniel Ceballos Fernández | 222509 | Daniel Ceballos Fernández / Real Betis | FIFA 16 CSV: exact_unique_full_name | `222509.png`
6702 | David Rodríguez Lombán | 189701 | David Rodríguez Lombán / Granada CF | FIFA 16 CSV: exact_unique_full_name | `189701.png`
6712 | Gonzalo Escalante | 219391 | Gonzalo Escalante / SD Eibar | FIFA 16 CSV: exact_unique_full_name | `219391.png`
6713 | Diego Javier Llorente Ríos | 212602 | Diego Javier Llorente Ríos / Rayo Vallecano | FIFA 16 CSV: exact_unique_full_name | `212602.png`
6717 | Johannes Geis | 202087 | Johannes Geis / FC Schalke 04 | FIFA 16 CSV: exact_unique_full_name | `202087.png`
6727 | Raúl Albentosa Redal | 207997 | Raúl Albentosa Redal / Málaga CF | FIFA 16 CSV: exact_unique_full_name | `207997.png`
6733 | Pedro Mosquera Parada | 178625 | Pedro Mosquera Parada / Deportivo de La Coruña | FIFA 16 CSV: exact_unique_full_name | `178625.png`
6736 | Álvaro Medrán Just | 212476 | Álvaro Medrán Just / Getafe CF | FIFA 16 CSV: exact_unique_full_name | `212476.png`
6743 | Manuel Rolando Iturra Urrutia | 176903 | Manuel Rolando Iturra Urrutia / Udinese | FIFA 16 CSV: exact_unique_full_name | `176903.png`
6745 | Mehdi Lacen | 169432 | Mehdi Lacen / Getafe CF | FIFA 16 CSV: exact_unique_full_name | `169432.png`
6746 | Gabriel Armando de Abreu | 201305 | Gabriel Armando de Abreu / Arsenal | FIFA 16 CSV: exact_unique_full_name | `201305.png`
6751 | Javier Fuego Martínez | 146460 | Javier Fuego Martínez / Valencia CF | FIFA 16 CSV: exact_unique_full_name | `146460.png`
6752 | Víctor Ruíz Torre | 193469 | Víctor Ruíz Torre / Villarreal CF | FIFA 16 CSV: exact_unique_full_name | `193469.png`
6758 | Víctor Sánchez Mata | 189506 | Víctor Sánchez Mata / RCD Espanyol | FIFA 16 CSV: exact_unique_full_name | `189506.png`
6759 | Roberto Soriano | 193361 | Roberto Soriano / Sampdoria | FIFA 16 CSV: exact_unique_full_name | `193361.png`
6762 | Álvaro González Soberón | 202935 | Álvaro González Soberón / RCD Espanyol | FIFA 16 CSV: exact_unique_full_name | `202935.png`
6764 | Pablo Fornals Malla | 226456 | Pablo Fornals Malla / Málaga CF | FIFA 16 CSV: exact_unique_full_name | `226456.png`
6771 | Manuel Trigueros Muñoz | 206545 | Manuel Trigueros Muñoz / Villarreal CF | FIFA 16 CSV: exact_unique_full_name | `206545.png`
6775 | Daniel García Carrillo | 216194 | Daniel Garcia Carrillo / SD Eibar | FIFA 16 CSV: exact_unique_full_name | `216194.png`
6777 | Sidnei Rechel da Silva Júnior | 182002 | Sidnei Rechel da Silva Júnior / Deportivo de La Coruña | FIFA 16 CSV: exact_unique_full_name | `182002.png`
6778 | Iván Ramis Barrios | 146701 | Iván Ramis Barrios / SD Eibar | FIFA 16 CSV: exact_unique_full_name | `146701.png`
6788 | Xabier Etxeita Gorritxategi | 190507 | Xabier Etxeita Gorritxategi / Athletic Club de Bilbao | FIFA 16 CSV: exact_unique_full_name | `190507.png`
6794 | Gustavo Daniel Cabral Cáceres | 165536 | Gustavo Daniel Cabral Cáceres / RC Celta | FIFA 16 CSV: exact_unique_full_name | `165536.png`
6796 | Nemanja Radoja | 225028 | Nemanja Radoja / RC Celta | FIFA 16 CSV: exact_unique_full_name | `225028.png`
6797 | Daniel Wass | 172522 | Daniel Wass / RC Celta | FIFA 16 CSV: exact_unique_full_name | `172522.png`
6801 | Pedro Pablo Hernández | 199827 | Pedro Pablo Hernández / RC Celta | FIFA 16 CSV: exact_unique_full_name | `199827.png`
6804 | Sergi Gómez Solà | 199577 | Sergi Gómez Solà / RC Celta | FIFA 16 CSV: exact_unique_full_name | `199577.png`
6825 | Daniel Filipe Martins Carriço | 189156 | Daniel Filipe Martins Carriço / Sevilla FC | FIFA 16 CSV: exact_unique_full_name | `189156.png`
6830 | Facundo Sebastián Roncaglia | 183966 | Facundo Sebastián Roncaglia / Fiorentina | FIFA 16 CSV: exact_unique_full_name | `183966.png`
6837 | Mauro Javier Dos Santos | 210787 | Mauro Dos Santos / SD Eibar | FIFA 16 CSV: exact_unique_name | `210787.png`
6861 | Juan Torres Ruiz | 186519 | Juan Torres Ruiz / Getafe CF | FIFA 16 CSV: exact_unique_full_name | `186519.png`
6867 | Papa Kouly Diop | 178250 | Papa Kouli Diop / Levante UD | https://www.futwiz.com/player/history/178250 | `178250.png`
6869 | Alejandro Arribas Garrido | 197890 | Alejandro Arribas Garrido / Deportivo de La Coruña | FIFA 16 CSV: exact_unique_full_name | `197890.png`
6872 | Bruno González Cabrera | 200228 | Bruno González Cabrera / Real Betis | FIFA 16 CSV: exact_unique_full_name | `200228.png`
6894 | Ezequiel Muñoz | 186695 | Ezequiel Muñoz / Genoa | FIFA 16 CSV: exact_unique_full_name | `186695.png`
6899 | Rubén Pardo Gutiérrez | 204523 | Rubén Pardo Gutiérrez / Real Sociedad | FIFA 16 CSV: exact_unique_full_name | `204523.png`
6929 | José Vicente Gómez Umpiérrez | 199977 | José Vicente Gómez Umpiérrez / UD Las Palmas | FIFA 16 CSV: exact_unique_full_name | `199977.png`
6938 | Felipe Dias da Silva dal Belo | 768 | Felipe Dias da Silva dal Belo / Parma | FIFA 15 CSV: exact_unique_full_name | `000768.png`
6941 | Jasmin Kurtič | 202061 | Jasmin Kurtić / Atalanta | FIFA 16 CSV: exact_unique_full_name | `202061.png`
6943 | Andrea Barzagli | 137186 | Andrea Barzagli / Juventus | FIFA 16 CSV: exact_unique_full_name | `137186.png`
6947 | Miralem Pjanić | 180206 | Miralem Pjanić / Roma | FIFA 16 CSV: exact_unique_full_name | `180206.png`
6952 | Alberto Grassi | 220475 | Alberto Grassi / Atalanta | FIFA 16 CSV: exact_unique_full_name | `220475.png`
6953 | Daniele Rugani | 211320 | Daniele Rugani / Juventus | FIFA 16 CSV: exact_unique_full_name | `211320.png`
6954 | Giorgio Chiellini | 138956 | Giorgio Chiellini / Juventus | FIFA 16 CSV: exact_unique_full_name | `138956.png`
6962 | Radja Nainggolan | 178518 | Radja Nainggolan / Roma | FIFA 16 CSV: exact_unique_full_name | `178518.png`
6963 | Lorenzo Pellegrini | 228251 | Lorenzo Pellegrini / Sassuolo | FIFA 16 CSV: exact_unique_full_name | `228251.png`
6969 | Juan Guilherme Nunes Jesus | 200752 | Juan Guilherme Nunes Jesus / Inter | FIFA 16 CSV: exact_unique_full_name | `200752.png`
6982 | Maxime Gonalons | 193116 | Maxime Gonalons / Olympique Lyonnais | FIFA 16 CSV: exact_unique_full_name | `193116.png`
6994 | Marten de Roon | 208461 | Marten de Roon / Atalanta | FIFA 16 CSV: exact_unique_full_name | `208461.png`
6997 | Borja Valero Iglesias | 161956 | Borja Valero Iglesias / Fiorentina | FIFA 16 CSV: exact_unique_full_name | `161956.png`
7002 | Rafael Tolói | 187598 | Rafael Tolói / Atalanta | FIFA 16 CSV: exact_unique_full_name | `187598.png`
7009 | Édgar Osvaldo Barreto Cáceres | 152922 | Édgar Osvaldo Barreto Cáceres / Sampdoria | FIFA 16 CSV: exact_unique_full_name | `152922.png`
7013 | Stefano Sturaro | 202135 | Stefano Sturaro / Juventus | FIFA 16 CSV: exact_unique_full_name | `202135.png`
7016 | Benedikt Höwedes | 179784 | Benedikt Höwedes / FC Schalke 04 | FIFA 16 CSV: exact_unique_full_name | `179784.png`
7019 | Matías Agustín Silvestre | 159028 | Matías Agustín Silvestre / Sampdoria | FIFA 16 CSV: exact_unique_full_name | `159028.png`
7024 | Jorge Luiz Frello Filho | 205498 | Luiz Frello Filho Jorge / Napoli | FIFA identity reference CSVs; name variant and recorded club reviewed | `205498.png`
7025 | Marek Hamšík | 171877 | Marek Hamšík / Napoli | FIFA 16 CSV: exact_unique_full_name | `171877.png`
7030 | Raúl Albiol i Tortajada | 157481 | Raúl Albiol Tortajada / Napoli | FIFA 16 CSV: exact_unique_name | `157481.png`
7034 | Mateo Pablo Musacchio | 186547 | Mateo Pablo Musacchio / Villarreal CF | FIFA 16 CSV: exact_unique_full_name | `186547.png`
7035 | Allan Marques Loureiro | 199914 | Allan Marques Loureiro / Napoli | FIFA 16 CSV: exact_unique_full_name | `199914.png`
7041 | Nicola Rigoni | 190330 | Nicola Rigoni / Chievo Verona | FIFA 16 CSV: exact_unique_full_name | `190330.png`
7042 | Ivan Radovanović | 186589 | Ivan Radovanović / Chievo Verona | FIFA 16 CSV: exact_unique_full_name | `186589.png`
7046 | Perparim Hetemaj | 172233 | Perparim Hetemaj / Chievo Verona | FIFA 16 CSV: exact_unique_full_name | `172233.png`
7048 | Konstantinos Manolas | 192774 | Kostas Manolas / Roma | FIFA identity reference CSVs; name variant and recorded club reviewed | `192774.png`
7049 | Lucas Nahuel Castro | 205633 | Lucas Castro / Chievo Verona | FIFA 16 CSV: exact_unique_name | `205633.png`
7051 | Daniele De Rossi | 53302 | Daniele De Rossi / Roma | FIFA 16 CSV: exact_unique_full_name | `053302.png`
7052 | Alessandro Gamberini | 5213 | Alessandro Gamberini / Chievo Verona | FIFA 16 CSV: exact_unique_full_name | `005213.png`
7056 | Nenad Tomović | 194203 | Nenad Tomović / Fiorentina | FIFA 16 CSV: exact_unique_full_name | `194203.png`
7107 | Danilo Cataldi | 211361 | Danilo Cataldi / Lazio | FIFA 16 CSV: exact_unique_full_name | `211361.png`
7113 | Simone Missiroli | 176553 | Simone Missiroli / Sassuolo | FIFA 16 CSV: exact_unique_full_name | `176553.png`
7119 | Francesco Acerbi | 199845 | Francesco Acerbi / Sassuolo | FIFA 16 CSV: exact_unique_full_name | `199845.png`
7127 | Francesco Magnanelli | 149185 | Francesco Magnanelli / Sassuolo | FIFA 16 CSV: exact_unique_full_name | `149185.png`
7137 | Ervin Zukanović | 190931 | Ervin Zukanović / Sampdoria | FIFA 16 CSV: exact_unique_full_name | `190931.png`
7142 | Luca Rossettini | 185163 | Luca Rossettini / Bologna | FIFA 16 CSV: exact_unique_full_name | `185163.png`
7147 | Andrea Bertolacci | 192073 | Andrea Bertolacci / Milan | FIFA 16 CSV: exact_unique_full_name | `192073.png`
7149 | Marco Benassi | 211354 | Marco Benassi / Torino | FIFA 16 CSV: exact_unique_full_name | `211354.png`
7153 | Jordan Veretout | 201519 | Jordan Veretout / Aston Villa | FIFA 16 CSV: exact_unique_full_name | `201519.png`
7154 | Sebastián Carlos Cristóforo Pepe | 219712 | Sebastián Cristóforo / Sevilla FC | FIFA 16 CSV: exact_unique_name | `219712.png`
7160 | Lorenzo Tonelli | 201049 | Lorenzo Tonelli / Empoli | FIFA 16 CSV: exact_unique_full_name | `201049.png`
7161 | Germán Alejandro Pezzella | 193601 | Germán Alejandro Pezzella / Real Betis | FIFA 16 CSV: exact_unique_full_name | `193601.png`
7166 | Riccardo Montolivo | 159287 | Riccardo Montolivo / Milan | FIFA 16 CSV: exact_unique_full_name | `159287.png`
7172 | Simone Romagnoli | 198857 | Simone Romagnoli / Carpi | FIFA 16 CSV: exact_unique_full_name | `198857.png`
7173 | Leonardo Bonucci | 184344 | Leonardo Bonucci / Juventus | FIFA 16 CSV: exact_unique_full_name | `184344.png`
7176 | Sebastian De Maio | 182179 | Sebastian De Maio / Genoa | FIFA 16 CSV: exact_unique_full_name | `182179.png`
7200 | Fabien Lemoine | 183287 | Fabien Lemoine / AS Saint-Étienne | FIFA 16 CSV: exact_unique_full_name | `183287.png`
7211 | Zargo Touré | 190196 | Zargo Touré / Le Havre AC | FIFA 15 CSV: exact_unique_full_name | `190196.png`
7283 | Thiago Xavier Rodrigues Corrêa | 159168 | Thiago Xavier Rodrigues Corrêa / ESTAC Troyes | FIFA 16 CSV: exact_unique_full_name | `159168.png`
7344 | Jordan Adéoti | 209691 | Jordan Adéoti / Stade Malherbe Caen | FIFA 16 CSV: exact_unique_full_name | `209691.png`
7346 | Lindsay Rose | 199464 | Lindsay Rose / Olympique Lyonnais | FIFA 16 CSV: exact_unique_full_name | `199464.png`
7350 | Birama Touré | 209698 | Birama Touré / FC Nantes | FIFA 16 CSV: exact_unique_full_name | `209698.png`
7389 | Amos Youga | 207744 | Amos Youga / GFC Ajaccio | FIFA 16 CSV: exact_unique_full_name | `207744.png`
7415 | Jessy Pi | 214991 | Jessy Pi / ESTAC Troyes | FIFA 16 CSV: exact_unique_full_name | `214991.png`
7435 | Anthony Weber | 183361 | Anthony Weber / Stade de Reims | FIFA 16 CSV: exact_unique_full_name | `183361.png`
7442 | Jérémy Clément | 163530 | Jérémy Clément / AS Saint-Étienne | FIFA 16 CSV: exact_unique_full_name | `163530.png`
7444 | Alaeddine Yahia | 53027 | Alaeddine Yahia / Stade Malherbe Caen | FIFA 16 CSV: exact_unique_full_name | `053027.png`
7458 | Alessio Romagnoli | 210413 | Alessio Romagnoli / Milan | FIFA 16 CSV: exact_unique_full_name | `210413.png`
7460 | Isaac Cofie | 198908 | Isaac Cofie / Carpi | FIFA 16 CSV: exact_unique_full_name | `198908.png`
7461 | Luca Rigoni | 138918 | Luca Rigoni / Palermo | FIFA 16 CSV: exact_unique_full_name | `138918.png`
7465 | Daniele Baselli | 205407 | Daniele Baselli / Torino | FIFA 16 CSV: exact_unique_full_name | `205407.png`
7467 | Nicolás Andrés Burdisso | 139038 | Nicolás Andrés Burdisso / Genoa | FIFA 16 CSV: exact_unique_full_name | `139038.png`
7472 | Nicolas Alexis Julio N'Koulou Ndoubena | 188829 | Nicolas N'Koulou / Olympique de Marseille | FIFA 16 CSV: exact_unique_name | `188829.png`
7474 | Afriyie Acquah | 201223 | Afriyie Acquah / Torino | FIFA 16 CSV: exact_unique_full_name | `201223.png`
7475 | Tomás Eduardo Rincón Hernández | 191053 | Tomás Eduardo Rincón Hernández / Genoa | FIFA 16 CSV: exact_unique_full_name | `191053.png`
7476 | Emiliano Moretti | 46736 | Emiliano Moretti / Torino | FIFA 16 CSV: exact_unique_full_name | `046736.png`
7498 | Mickaël Tacalfred | 107305 | Mickaël Tacalfred / Stade de Reims | FIFA 16 CSV: exact_unique_full_name | `107305.png`
7552 | Clément Chantôme | 177953 | Clément Chantôme / FC Girondins de Bordeaux | FIFA 16 CSV: exact_unique_full_name | `177953.png`
7594 | Mart Ristl | 229353 | Mart Ristl / VfB Stuttgart | FIFA 16 CSV: exact_unique_full_name | `229353.png`
7603 | Jérémie Bréchet | 4732 | Jérémie Bréchet / GFC Ajaccio | FIFA 16 CSV: exact_unique_full_name | `004732.png`
7698 | Joseph Alfred Duncan | 208535 | Joseph Alfred Duncan / Sassuolo | FIFA 16 CSV: exact_unique_full_name | `208535.png`
7766 | Walid Mesloub | 192824 | Walid Mesloub / FC Lorient | FIFA 16 CSV: exact_unique_full_name | `192824.png`
7770 | Federico Viviani | 202828 | Federico Viviani / Hellas Verona | FIFA 16 CSV: exact_unique_full_name | `202828.png`
7771 | Dario Dainelli | 7647 | Dario Dainelli / Chievo Verona | FIFA 16 CSV: exact_unique_full_name | `007647.png`
7780 | Lucas Pezzini Leiva | 176266 | Lucas  Pezzini Leiva / Liverpool | FIFA 16 CSV: exact_unique_full_name | `176266.png`
7791 | Seko Fofana | 216320 | Seko Fofana / Sporting Club de Bastia | FIFA 16 CSV: exact_unique_full_name | `216320.png`
7799 | Danilo Larangeira | 166072 | Danilo Larangeira / Udinese | FIFA 16 CSV: exact_unique_full_name | `166072.png`
7808 | Roderic Filippi | 209385 | Rodéric Filippi / GFC Ajaccio | FIFA 16 CSV: exact_unique_full_name | `209385.png`
7815 | Antoine Devaux | 169805 | Antoine Devaux / Stade de Reims | FIFA 16 CSV: exact_unique_full_name | `169805.png`
7907 | Pedro Bigas Rigo | 206222 | Pedro Bigas Rigo / UD Las Palmas | FIFA 16 CSV: exact_unique_full_name | `206222.png`
7949 | Artur Ioniţă | 192587 | Artur Ioniţă / Hellas Verona | FIFA 16 CSV: exact_unique_full_name | `192587.png`
7962 | Andrea Ranocchia | 182168 | Andrea Ranocchia / Inter | FIFA 16 CSV: exact_unique_full_name | `182168.png`
7966 | Filip Helander | 207555 | Filip Helander / Hellas Verona | FIFA 16 CSV: exact_unique_full_name | `207555.png`
8102 | Edoardo Goldaniga | 223524 | Edoardo Goldaniga / Palermo | FIFA 16 CSV: exact_unique_full_name | `223524.png`
8173 | Marco Parolo | 183498 | Marco Parolo / Lazio | FIFA 16 CSV: exact_unique_full_name | `183498.png`
8187 | Marcel Büchel | 198079 | Marcel Büchel / Bologna | FIFA 15 CSV: exact_unique_full_name | `198079.png`
8206 | Arturo Erasmo Vidal Pardo | 181872 | Arturo Vidal / FC Bayern München | FIFA 16 CSV: exact_unique_name | `181872.png`
8207 | Dominik Kohr | 212212 | Dominik Kohr / FC Augsburg | FIFA 16 CSV: exact_unique_full_name | `212212.png`
8210 | Charles Mariano Aránguiz Sandoval | 199042 | Charles Mariano Aránguiz Sandoval / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `199042.png`
8216 | Sven Bender | 177458 | Sven Bender / Borussia Dortmund | FIFA 16 CSV: exact_unique_full_name | `177458.png`
8221 | Jonathan Tah | 213331 | Jonathan Tah / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `213331.png`
8222 | Kevin Kampl | 195365 | Kevin Kampl / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `195365.png`
8230 | Josuha Guilavogui | 198118 | Josuha Guilavogui / VfL Wolfsburg | FIFA 16 CSV: exact_unique_full_name | `198118.png`
8231 | Yannick Gerhardt | 212245 | Yannick Gerhardt / 1. FC Köln | FIFA 16 CSV: exact_unique_full_name | `212245.png`
8234 | Ignacio Camacho Barnola | 188005 | Ignacio Camacho Barnola / Málaga CF | FIFA 16 CSV: exact_unique_full_name | `188005.png`
8235 | Maximilian Arnold | 206511 | Maximilian Arnold / VfL Wolfsburg | FIFA 16 CSV: exact_unique_full_name | `206511.png`
8238 | Mahmoud Dahoud | 218339 | Mahmoud Dahoud / Borussia Mönchengladbach | FIFA 16 CSV: exact_unique_full_name | `218339.png`
8239 | Robin Knoche | 203030 | Robin Knoche / VfL Wolfsburg | FIFA 16 CSV: exact_unique_full_name | `203030.png`
8244 | Sokratis Papastathopoulos | 172879 | Sokratis Papastathopoulos / Borussia Dortmund | FIFA 16 CSV: exact_unique_full_name | `172879.png`
8270 | Daniel Schwaab | 183426 | Daniel Schwaab / VfB Stuttgart | FIFA 16 CSV: exact_unique_full_name | `183426.png`
8275 | Davide Astori | 173198 | Davide Astori / Fiorentina | FIFA 16 CSV: exact_unique_full_name | `173198.png`
8277 | Wallace Fortuna dos Santos | 216437 | Wallace Fortuna dos Santos / AS Monaco | FIFA 16 CSV: exact_unique_full_name | `216437.png`
8278 | Nicolás Federico Spolli | 171830 | Nicolás Federico Spolli / Carpi | FIFA 16 CSV: exact_unique_full_name | `171830.png`
8280 | Godfred Donsah | 221695 | Godfred Donsah / Bologna | FIFA 16 CSV: exact_unique_full_name | `221695.png`
8284 | Amadou Diawara | 230613 | Amadou Diawara / Bologna | FIFA 16 CSV: exact_unique_full_name | `230613.png`
8291 | Arlind Afrim Ajeti | 203458 | Arlind Ajeti / FC Basel 1893 | FIFA identity reference CSVs; name variant and recorded club reviewed | `203458.png`
8294 | Claudio Marchisio | 173210 | Claudio Marchisio / Juventus | FIFA 16 CSV: exact_unique_full_name | `173210.png`
8313 | Kyriakos Papadopoulos | 184477 | Kyriakos Papadopoulos / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `184477.png`
8317 | Daniel Baier | 137351 | Daniel Baier / FC Augsburg | FIFA 16 CSV: exact_unique_full_name | `137351.png`
8385 | Ludovic Lamine Sané | 192333 | Ludovic Lamine Sané / FC Girondins de Bordeaux | FIFA 16 CSV: exact_unique_full_name | `192333.png`
8388 | Jérôme Gondorf | 211907 | Jérôme Gondorf / SV Darmstadt 98 | FIFA 16 CSV: exact_unique_full_name | `211907.png`
8394 | Robert Bauer | 223765 | Robert Bauer / FC Ingolstadt 04 | FIFA 16 CSV: exact_unique_full_name | `223765.png`
8395 | Håvard Nordtveit | 182888 | Håvard Nordtveit / Borussia Mönchengladbach | FIFA 16 CSV: exact_unique_full_name | `182888.png`
8397 | Kevin Vogt | 192641 | Kevin Vogt / 1. FC Köln | FIFA 16 CSV: exact_unique_full_name | `192641.png`
8404 | Eugen Polanski | 165174 | Eugen Polanski / TSG 1899 Hoffenheim | FIFA 16 CSV: exact_unique_full_name | `165174.png`
8405 | Benjamin Hübner | 189433 | Benjamin Hübner / FC Ingolstadt 04 | FIFA 16 CSV: exact_unique_full_name | `189433.png`
8420 | Luca Cigarini | 173146 | Luca Cigarini / Atalanta | FIFA 16 CSV: exact_unique_full_name | `173146.png`
8421 | Matteo Bianchetti | 205363 | Matteo Bianchetti / Hellas Verona | FIFA 16 CSV: exact_unique_full_name | `205363.png`
8440 | Aythami Artiles Oliva | 171189 | Aythami Artiles Oliva / UD Las Palmas | FIFA 16 CSV: exact_unique_full_name | `171189.png`
8515 | Benjamin Stambouli | 198200 | Benjamin Stambouli / Paris Saint-Germain | FIFA 16 CSV: exact_unique_full_name | `198200.png`
8516 | Ronaldo Aparecido Rodrigues | 171919 | Ronaldo  Aparecido Rodrigues / VfL Wolfsburg | FIFA 16 CSV: exact_unique_full_name | `171919.png`
8539 | Danny Latza | 189410 | Danny Latza / 1. FSV Mainz 05 | FIFA 16 CSV: exact_unique_full_name | `189410.png`
8543 | Manuel Schmiedebach | 193420 | Manuel Schmiedebach / Hannover 96 | FIFA 16 CSV: exact_unique_full_name | `193420.png`
8556 | Pirmin Schwegler | 158905 | Pirmin Schwegler / TSG 1899 Hoffenheim | FIFA 16 CSV: exact_unique_full_name | `158905.png`
8559 | Stefan Bell | 198352 | Stefan Bell / 1. FSV Mainz 05 | FIFA 16 CSV: exact_unique_full_name | `198352.png`
8561 | Fabian Frei | 183346 | Fabian Frei / 1. FSV Mainz 05 | FIFA 16 CSV: exact_unique_full_name | `183346.png`
8570 | Niklas Stark | 212977 | Niklas Stark / Hertha BSC | FIFA 16 CSV: exact_unique_full_name | `212977.png`
8572 | Karim Rekik | 205193 | Karim Rekik / Olympique de Marseille | FIFA 16 CSV: exact_unique_full_name | `205193.png`
8573 | Ömer Toprak | 185239 | Ömer Toprak / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `185239.png`
8578 | Per Ciljan Skjelbred | 152996 | Per Ciljan Skjelbred / Hertha BSC | FIFA 16 CSV: exact_unique_full_name | `152996.png`
8579 | Vladimír Darida | 201262 | Vladimír Darida / Hertha BSC | FIFA 16 CSV: exact_unique_full_name | `201262.png`
8580 | Sebastian Langkamp | 183568 | Sebastian Langkamp / Hertha BSC | FIFA 16 CSV: exact_unique_full_name | `183568.png`
8664 | Andrea Costa | 178042 | Andrea Costa / Empoli | FIFA 16 CSV: exact_unique_full_name | `178042.png`
8672 | Gélson da Conceição Tavares Fernandes | 158438 | Gélson da Conceição Tavares Fernandes / Stade Rennais FC | FIFA 16 CSV: exact_unique_full_name | `158438.png`
8677 | Marcel Tisserand | 216247 | Marcel Tisserand / Toulouse Football Club | FIFA 16 CSV: exact_unique_full_name | `216247.png`
8678 | David Ángel Abraham | 160741 | David Ángel Abraham / Eintracht Frankfurt | FIFA 16 CSV: exact_unique_full_name | `160741.png`
8762 | Zlatko Junuzović | 173474 | Zlatko Junuzović / SV Werder Bremen | FIFA 16 CSV: exact_unique_full_name | `173474.png`
8805 | Christoph Kramer | 204024 | Christoph Kramer / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `204024.png`
8808 | Matthias Ginter | 207862 | Matthias Ginter / Borussia Dortmund | FIFA 16 CSV: exact_unique_full_name | `207862.png`
8812 | Marco Russ | 157716 | Marco Russ / Eintracht Frankfurt | FIFA 16 CSV: exact_unique_full_name | `157716.png`
8814 | Nico Elvedi | 221491 | Nico Elvedi / Borussia Mönchengladbach | FIFA 16 CSV: exact_unique_full_name | `221491.png`
8815 | Jannik Vestergaard | 202849 | Jannik Vestergaard / SV Werder Bremen | FIFA 16 CSV: exact_unique_full_name | `202849.png`
8816 | Julian Weigl | 222028 | Julian Weigl / Borussia Dortmund | FIFA 16 CSV: exact_unique_full_name | `222028.png`
8818 | Jorge Meré Pérez | 223033 | Jorge Meré Pérez / Real Sporting de Gijón | FIFA 16 CSV: exact_unique_full_name | `223033.png`
8822 | Simon Zoller | 202276 | Simon Zoller / 1. FC Köln | FIFA 16 CSV: exact_unique_full_name | `202276.png`
8827 | Matthias Lehmann | 52498 | Matthias Lehmann / 1. FC Köln | FIFA 16 CSV: exact_unique_full_name | `052498.png`
8828 | Dominique Heintz | 206198 | Dominique Heintz / 1. FC Köln | FIFA 16 CSV: exact_unique_full_name | `206198.png`
8829 | Frederik Hillesborg Sørensen | 201342 | Frederik Hillesborg Sørensen / 1. FC Köln | FIFA 16 CSV: exact_unique_full_name | `201342.png`
8847 | Santiago Juan Gentiletti Selak | 205408 | Santiago Juan Gentiletti Selak / Lazio | FIFA 16 CSV: exact_unique_full_name | `205408.png`
8848 | Paolo Cannavaro | 1178 | Paolo Cannavaro / Sassuolo | FIFA 16 CSV: exact_unique_full_name | `001178.png`
8849 | Domenico Maietta | 137774 | Domenico Maietta / Bologna | FIFA 16 CSV: exact_unique_full_name | `137774.png`
8851 | Saphir Sliti Taïder | 198760 | Saphir Sliti Taïder / Bologna | FIFA 16 CSV: exact_unique_full_name | `198760.png`
8852 | Thomas Heurtaux | 188654 | Thomas Heurtaux / Udinese | FIFA 16 CSV: exact_unique_full_name | `188654.png`
8873 | Marios Oikonomou | 216523 | Marios Oikonomou / Bologna | FIFA 16 CSV: exact_unique_full_name | `216523.png`
8877 | Boštjan Cesar | 139274 | Boštjan Cesar / Chievo Verona | FIFA 16 CSV: exact_unique_full_name | `139274.png`
8890 | Christoph Moritz | 194089 | Christoph Moritz / 1. FSV Mainz 05 | FIFA 16 CSV: exact_unique_full_name | `194089.png`
8891 | Lewis Harry Holtby | 188154 | Lewis Harry Holtby / Hamburger SV | FIFA 16 CSV: exact_unique_full_name | `188154.png`
8956 | Timo Baumgartl | 223641 | Timo Baumgartl / VfB Stuttgart | FIFA 16 CSV: exact_unique_full_name | `223641.png`
8959 | Christian Gentner | 158856 | Christian Gentner / VfB Stuttgart | FIFA 16 CSV: exact_unique_full_name | `158856.png`
8965 | Fabian Lustenberger | 177019 | Fabian Lustenberger / Hertha BSC | FIFA 16 CSV: exact_unique_full_name | `177019.png`
8969 | Lars Bender | 177457 | Lars Bender / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `177457.png`
9106 | Marvin Matip | 161644 | Marvin Matip / FC Ingolstadt 04 | FIFA 16 CSV: exact_unique_full_name | `161644.png`
9140 | Luca-Milan Zander | 222773 | Luca-Milan Zander / SV Werder Bremen | FIFA 16 CSV: exact_unique_full_name | `222773.png`
9178 | Felix Kroos | 191066 | Felix Kroos / SV Werder Bremen | FIFA 16 CSV: exact_unique_full_name | `191066.png`
9216 | Slobodan Medojević | 207523 | Slobodan Medojević / Eintracht Frankfurt | FIFA 16 CSV: exact_unique_full_name | `207523.png`
9217 | Aytac Sulu | 223142 | Aytaç Sulu / SV Darmstadt 98 | FIFA 16 CSV: exact_unique_full_name | `223142.png`
9363 | André Ramalho Silva | 210007 | André Ramalho Silva / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `210007.png`
9404 | Luca Caldirola | 199776 | Luca Caldirola / SV Darmstadt 98 | FIFA 16 CSV: exact_unique_full_name | `199776.png`
9406 | Holger Badstuber | 192620 | Holger Badstuber / FC Bayern München | FIFA 16 CSV: exact_unique_full_name | `192620.png`
9452 | Gary O''Neil | 53593 | Gary O'Neil / Norwich City | FIFA 16 CSV: exact_unique_full_name | `053593.png`
9461 | Timm Klose | 199383 | Timm Klose / VfL Wolfsburg | FIFA 16 CSV: exact_unique_full_name | `199383.png`
9463 | Alexander Banor Tettey | 152567 | Alexander Banor Tettey / Norwich City | FIFA 16 CSV: exact_unique_full_name | `152567.png`
9475 | Moritz Leitner | 200857 | Moritz Leitner / Borussia Dortmund | FIFA 16 CSV: exact_unique_full_name | `200857.png`
9578 | Jonathan Howson | 183422 | Jonathan Howson / Norwich City | FIFA 15 CSV: exact_unique_full_name | `183422.png`
9625 | Glenn Whelan | 163303 | Glenn  Whelan / Stoke City | FIFA 16 CSV: exact_unique_full_name | `163303.png`
9626 | Tommy Elphick | 180635 | Tommy Elphick / Bournemouth | FIFA 16 CSV: exact_unique_full_name | `180635.png`
9649 | Jack Colback | 193942 | Jack Colback / Newcastle United | FIFA 16 CSV: exact_unique_full_name | `193942.png`
9720 | Philipp Ochs | 229701 | Philipp Ochs / TSG 1899 Hoffenheim | FIFA 16 CSV: exact_unique_full_name | `229701.png`
9884 | Niklas Moisander | 172862 | Niklas Moisander / Sampdoria | FIFA 16 CSV: exact_unique_full_name | `172862.png`
9903 | Yussif Raman Chibsah | 206109 | Yussif Raman Chibsah / Frosinone | FIFA 16 CSV: exact_unique_full_name | `206109.png`
9930 | Ryan Bennett | 183774 | Ryan Bennett / Norwich City | FIFA 16 CSV: exact_unique_full_name | `183774.png`
9939 | Maurício dos Santos Nascimento | 187324 | Maurício dos Santos Nascimento / Lazio | FIFA 16 CSV: exact_unique_full_name | `187324.png`
9940 | Armando Izzo | 216145 | Armando Izzo / Genoa | FIFA 16 CSV: exact_unique_full_name | `216145.png`
10030 | Davide Biondini | 162174 | Davide Biondini / Sassuolo | FIFA 16 CSV: exact_unique_full_name | `162174.png`
10036 | Jacques-Alaixys Romao | 159175 | Jacques-Alaixys Romao / Olympique de Marseille | FIFA 16 CSV: exact_unique_full_name | `159175.png`
10037 | Danilo Barbosa da Silva | 223517 | Danilo Barbosa da Silva / Valencia CF | FIFA 16 CSV: exact_unique_full_name | `223517.png`
10287 | İlkay Gündoğan | 186942 | İlkay Gündoğan / Borussia Dortmund | FIFA 16 CSV: exact_unique_full_name | `186942.png`
10476 | Timothée Kolodziejczak | 190034 | Thimothée Kolodziejczak / Sevilla FC | FIFA identity reference CSVs; name variant and recorded club reviewed | `190034.png`
10522 | Mehdi Mostefa Sbaa | 188765 | Mehdi Mostefa Sbaa / FC Lorient | FIFA 15 CSV: exact_unique_full_name | `188765.png`
10530 | Jules Olivier Ntcham | 218745 | Jules Olivier Ntcham / Genoa | FIFA 16 CSV: exact_unique_full_name | `218745.png`
10609 | Jérémy Mathieu | 112316 | Jérémy Mathieu / FC Barcelona | FIFA 16 CSV: exact_unique_full_name | `112316.png`
10783 | Lee Cattermole | 169607 | Lee  Cattermole / Sunderland | FIFA 16 CSV: exact_unique_full_name | `169607.png`
10802 | André Filipe Tavares Gomes | 211575 | André Filipe Tavares Gomes / Valencia CF | FIFA 16 CSV: exact_unique_full_name | `211575.png`
10805 | Ricardo Alberto Silveira de Carvalho | 3622 | Ricardo Alberto Silveira de Carvalho / AS Monaco | FIFA 16 CSV: exact_unique_full_name | `003622.png`
10919 | Juraj Kucka | 190875 | Juraj Kucka / Genoa | FIFA 15 CSV: exact_unique_full_name | `190875.png`
10936 | Lorik Agim Cana | 134956 | Lorik Agim Cana / Lazio | FIFA 15 CSV: exact_unique_full_name | `134956.png`
10956 | Eric Dier | 202335 | Eric Dier / Tottenham Hotspur | FIFA 16 CSV: exact_unique_full_name | `202335.png`
10958 | Chris Smalling | 189881 | Chris Smalling / Manchester United | FIFA 16 CSV: exact_unique_full_name | `189881.png`
11012 | Jonathan Grant Evans | 169588 | Jonny Evans / West Bromwich Albion | FIFA 16 CSV: exact_unique_name | `169588.png`
11286 | Dominik Maroh | 190670 | Dominic Maroh / 1. FC Köln | FIFA identity reference CSVs; name variant and recorded club reviewed | `190670.png`
11332 | Ibrahim Amadou | 211382 | Ibrahim Amadou / LOSC Lille | FIFA 16 CSV: exact_unique_full_name | `211382.png`
11386 | Santiago Cazorla González | 146562 | Santiago Cazorla González / Arsenal | FIFA 16 CSV: exact_unique_full_name | `146562.png`
11395 | Lukas Rupp | 200469 | Lukas Rupp / VfB Stuttgart | FIFA 16 CSV: exact_unique_full_name | `200469.png`
11396 | Florian Grillitsch | 228336 | Florian Grillitsch / SV Werder Bremen | FIFA 16 CSV: exact_unique_full_name | `228336.png`
11499 | Riccardo Gagliolo | 216067 | Riccardo Gagliolo / Carpi | FIFA 16 CSV: exact_unique_full_name | `216067.png`
11603 | Mario Pašalić | 223273 | Mario Pašalić / AS Monaco | FIFA 16 CSV: exact_unique_full_name | `223273.png`
12294 | Andre Hoffmann | 199779 | André Hoffmann / Hannover 96 | FIFA 16 CSV: exact_unique_full_name | `199779.png`
12320 | Tony Jantschke | 190520 | Tony Jantschke / Borussia Mönchengladbach | FIFA 16 CSV: exact_unique_full_name | `190520.png`
12321 | Tobias Strobl | 207894 | Tobias Strobl / TSG 1899 Hoffenheim | FIFA 16 CSV: exact_unique_full_name | `207894.png`
12327 | John Anthony Brooks | 204082 | John Anthony Brooks / Hertha BSC | FIFA 16 CSV: exact_unique_full_name | `204082.png`
12551 | Max Christiansen | 226686 | Max Christiansen / FC Ingolstadt 04 | FIFA 16 CSV: exact_unique_full_name | `226686.png`
12583 | Carlos Armando Gruezo Arboleda | 221860 | Carlos Armando Gruezo Arboleda / VfB Stuttgart | FIFA 16 CSV: exact_unique_full_name | `221860.png`
12599 | Carlos Antonio Ascues Ávila | 212509 | Carlos Ascues / VfL Wolfsburg | FIFA 16 CSV: exact_unique_name | `212509.png`
13107 | Sergio Álvarez Díaz | 199158 | Sergio Álvarez Díaz / Real Sporting de Gijón | FIFA 16 CSV: exact_unique_full_name | `199158.png`
13286 | Lamine Koné | 184082 | Lamine Koné / FC Lorient | FIFA 16 CSV: exact_unique_full_name | `184082.png`
13319 | Niko Bungert | 175962 | Niko Bungert / 1. FSV Mainz 05 | FIFA 16 CSV: exact_unique_full_name | `175962.png`
13332 | Romain Brégerie | 178032 | Romain Brégerie / FC Ingolstadt 04 | FIFA 16 CSV: exact_unique_full_name | `178032.png`
13675 | Mario Vrančić | 177896 | Mario Vrančić / SV Darmstadt 98 | FIFA 16 CSV: exact_unique_full_name | `177896.png`
13730 | Matthieu Saunier | 193081 | Matthieu Saunier / ESTAC Troyes | FIFA 16 CSV: exact_unique_full_name | `193081.png`
13846 | Jan Kirchhoff | 190752 | Jan Kirchhoff / FC Bayern München | FIFA 16 CSV: exact_unique_full_name | `190752.png`
15651 | Juan Bernat Velasco | 205069 | Juan Bernat Velasco / FC Bayern München | FIFA 16 CSV: exact_unique_full_name | `205069.png`
15805 | Hernán Daniel Santana Trujillo | 202413 | Hernán Daniel Santana Trujillo / UD Las Palmas | FIFA 16 CSV: exact_unique_full_name | `202413.png`
16003 | Fernando Francisco Reges | 184134 | Fernando Francisco Reges / Manchester City | FIFA 16 CSV: exact_unique_full_name | `184134.png`
16072 | Vurnon Anita | 183940 | Vurnon Anita / Newcastle United | FIFA 16 CSV: exact_unique_full_name | `183940.png`
16181 | Jordy Clasie | 199422 | Jordy Clasie / Southampton | FIFA 16 CSV: exact_unique_full_name | `199422.png`
16202 | Nikola Maksimović | 215466 | Nikola Maksimović / Torino | FIFA 16 CSV: exact_unique_full_name | `215466.png`
16308 | Leandro Daniel Paredes | 207439 | Leandro Paredes / Empoli | FIFA 16 CSV: exact_unique_name | `207439.png`
16334 | Graham Dorrans | 171321 | Graham Dorrans / Norwich City | FIFA 16 CSV: exact_unique_full_name | `171321.png`
16430 | Uroš Spajić | 215892 | Uroš Spajić / Toulouse Football Club | FIFA 16 CSV: exact_unique_full_name | `215892.png`
16453 | Gary Alexis Medel Soto | 193532 | Gary Alexis Medel Soto / Inter | FIFA 16 CSV: exact_unique_full_name | `193532.png`
16456 | Enzo Pablo Roco Roco | 212225 | Enzo Pablo Roco Roco / RCD Espanyol | FIFA 16 CSV: exact_unique_full_name | `212225.png`
16502 | László Kleinheisler | 231493 | László Kleinheisler / SV Darmstadt 98 | FIFA 17 CSV: exact_unique_full_name | `231493.png`
16522 | Tongo Hamed Doumbia | 192767 | Tongo Doumbia / Toulouse Football Club | FIFA 16 CSV: exact_unique_name | `192767.png`
16534 | Roman Neustädter | 186296 | Roman Neustädter / FC Schalke 04 | FIFA 16 CSV: exact_unique_full_name | `186296.png`
16539 | Diego Antonio Reyes Rosales | 192012 | Diego Antonio Reyes Rosales / Real Sociedad | FIFA 16 CSV: exact_unique_full_name | `192012.png`
16586 | Fernando Lucas Martins | 202642 | Fernando Lucas Martins / Sampdoria | FIFA 16 CSV: exact_unique_full_name | `202642.png`
16622 | Mikel González de Martín Martínez | 172294 | Mikel González de Martín Martínez / Real Sociedad | FIFA 16 CSV: exact_unique_full_name | `172294.png`
16890 | John O''Shea | 3484 | John  O'Shea / Sunderland | FIFA 16 CSV: exact_unique_full_name | `003484.png`
17054 | Emiliano Daniel Velázquez Maldonado | 225299 | Emiliano Velázquez / Getafe CF | FIFA 16 CSV: exact_unique_name | `225299.png`
17520 | Federico Barba | 211557 | Federico Barba / Empoli | FIFA 16 CSV: exact_unique_full_name | `211557.png`
18027 | Matteo Brighi | 45605 | Matteo Brighi / Bologna | FIFA 16 CSV: exact_unique_full_name | `045605.png`
18398 | Omar Mascarell González | 208620 | Omar Mascarell González / Real Sporting de Gijón | FIFA 16 CSV: exact_unique_full_name | `208620.png`
18414 | Bastian Schweinsteiger | 121944 | Bastian Schweinsteiger / Manchester United | FIFA 16 CSV: exact_unique_full_name | `121944.png`
18751 | Jack Rodwell | 183465 | Jack Rodwell / Sunderland | FIFA 16 CSV: exact_unique_full_name | `183465.png`
18872 | Martin Škrtel | 166706 | Martin Škrtel / Liverpool | FIFA 16 CSV: exact_unique_full_name | `166706.png`
18874 | Mauricio Aníbal Isla Isla | 187800 | Mauricio Aníbal Isla Isla / Olympique de Marseille | FIFA 16 CSV: exact_unique_full_name | `187800.png`
18888 | Szabolcs Huszti | 137080 | Szabolcs Huszti / Eintracht Frankfurt | FIFA 17 CSV: exact_unique_full_name | `137080.png`
18925 | Ignacio Cases Mora | 202142 | Ignacio Cases Mora / Real Sporting de Gijón | FIFA 16 CSV: exact_unique_full_name | `202142.png`
19288 | Martín Gastón Demichelis | 134979 | Martín Gastón Demichelis / Manchester City | FIFA 16 CSV: exact_unique_full_name | `134979.png`
19431 | Fernando Damián Tissone | 177981 | Fernando Damián Tissone / Málaga CF | FIFA 16 CSV: exact_unique_full_name | `177981.png`
19454 | Ricardo Miguel Moreira da Costa | 20209 | Ricardo Miguel Moreira da Costa / PAOK | FIFA 16 CSV: exact_unique_full_name | `020209.png`
19668 | Augusto Matías Fernández | 176915 | Augusto Matías Fernández / RC Celta | FIFA 16 CSV: exact_unique_full_name | `176915.png`
19813 | Rolando Jorge Pires da Fonseca | 163083 | Rolando Jorge Pires da Fonseca / FC Porto | FIFA 15 CSV: exact_unique_full_name | `163083.png`
20004 | Paul Pogba | 195864 | Paul Pogba / Juventus | FIFA 16 CSV: exact_unique_full_name | `paul-pogba.png`
20005 | Toby Alderweireld | 184087 | Toby Alderweireld / Tottenham Hotspur | FIFA 16 CSV: exact_unique_full_name | `184087.png`
20010 | Clemens Fritz | 101336 | Clemens Fritz / SV Werder Bremen | FIFA 16 CSV: exact_unique_full_name | `101336.png`
20016 | Kléper Laveran Lima Ferreira | 120533 | Képler Laveran Lima Ferreira / Real Madrid | FIFA 16 CSV: exact_unique_name | `120533.png`
20037 | Julian Baumgartlinger | 189606 | Julian Baumgartlinger / 1. FSV Mainz 05 | FIFA 16 CSV: exact_unique_full_name | `189606.png`
20046 | Phil Jagielka | 53914 | Phil Jagielka / Everton | FIFA 16 CSV: exact_unique_full_name | `053914.png`
20133 | Xabier Alonso Olano | 45197 | Xabier Alonso Olano / FC Bayern München | FIFA 16 CSV: exact_unique_full_name | `045197.png`
20169 | Seydou Kéita | 12259 | Seydou Kéita / Roma | FIFA 16 CSV: exact_unique_full_name | `012259.png`
20285 | Joleon Lescott | 138726 | Joleon Lescott / West Bromwich Albion | FIFA 15 CSV: exact_unique_full_name | `138726.png`
20287 | John Terry | 13732 | John Terry / Chelsea | FIFA 16 CSV: exact_unique_full_name | `013732.png`
20485 | Almog Cohen | 199661 | Almog Cohen / FC Ingolstadt 04 | FIFA 16 CSV: exact_unique_full_name | `199661.png`
20499 | Martin Stranzl | 1611 | Martin Stranzl / Borussia Mönchengladbach | FIFA 16 CSV: exact_unique_full_name | `001611.png`
20527 | Jonas Olsson | 45842 | Jonas Olsson / West Bromwich Albion | FIFA identity reference CSVs; name variant and recorded club reviewed | `045842.png`
20636 | Mirko Gori | 224314 | Mirko Gori / Frosinone | FIFA 16 CSV: exact_unique_full_name | `224314.png`
20669 | Tiago Cardoso Mendes | 4098 | Tiago Cardoso Mendes / Atlético Madrid | FIFA 16 CSV: exact_unique_full_name | `004098.png`
21168 | Marlon Frey | 225564 | Marlon Frey / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `225564.png`
21212 | Russell Martin | 162886 | Russell Martin / Norwich City | FIFA 16 CSV: exact_unique_full_name | `162886.png`
22587 | Didier Ndong Ibrahim | 218359 | Didier  Ndong Ibrahim / FC Lorient | FIFA 16 CSV: exact_unique_full_name | `218359.png`
22819 | Bruno Soriano Llido | 184120 | Bruno  Soriano Llido / Villarreal CF | FIFA 16 CSV: exact_unique_full_name | `184120.png`
22824 | Sebastian Rode | 200215 | Sebastian Rode / FC Bayern München | FIFA 16 CSV: exact_unique_full_name | `200215.png`
22826 | Jan-Ingwer Callsen-Bracker | 137449 | Jan-Ingwer Callsen-Bracker / FC Augsburg | FIFA 16 CSV: exact_unique_full_name | `137449.png`
23329 | Abdelhamid El Kaoutari | 188145 | Abdelhamid El Kaoutari / Palermo | FIFA 16 CSV: exact_unique_full_name | `188145.png`
23349 | Paolo Sammarco | 149572 | Paolo Sammarco / Frosinone | FIFA 16 CSV: exact_unique_full_name | `149572.png`
23488 | Mario Suárez Mata | 171018 | Mario Suárez Mata / Fiorentina | FIFA 16 CSV: exact_unique_full_name | `171018.png`
23806 | Alejandro Bergantiños García | 188931 | Alejandro Bergantiños García / Deportivo de La Coruña | FIFA 16 CSV: exact_unique_full_name | `188931.png`
23850 | Mathieu Peybernes | 195313 | Mathieu Peybernes / Bastia | https://www.futwiz.com/player/history/195313 | `195313.png`
23933 | Abdelaziz Barrada | 192274 | Abdelaziz Barrada / Olympique de Marseille | FIFA 16 CSV: exact_unique_full_name | `192274.png`
24117 | Christoph Janker | 156443 | Christoph Janker / FC Augsburg | FIFA 16 CSV: exact_unique_full_name | `156443.png`
24149 | José Antonio García Rabasco | 142454 | José Antonio García Rabasco / Levante UD | FIFA 16 CSV: exact_unique_full_name | `142454.png`
24244 | Uffe Manich Bech | 201526 | Uffe Manich Bech / Hannover 96 | FIFA 16 CSV: exact_unique_full_name | `201526.png`
24380 | Tetchi Jores Charlemagne Ulrich Okore | 204163 | Tetchi Jores Charlemagne Ulrich Okore / Aston Villa | FIFA 16 CSV: exact_unique_full_name | `204163.png`
24428 | Vladlen Yurchenko | 223759 | Vladlen Yurchenko / Bayer 04 Leverkusen | FIFA 16 CSV: exact_unique_full_name | `223759.png`
24722 | Emmanuel Agyemang-Badu | 192575 | Emmanuel Badu / Udinese | FIFA identity reference CSVs; name variant and recorded club reviewed | `192575.png`
25199 | Lucas Silva Borges | 209749 | Lucas Silva Borges / Olympique de Marseille | FIFA 16 CSV: exact_unique_full_name | `209749.png`
25430 | Felipe Melo de Carvalho | 135475 | Felipe Melo de Carvalho / Galatasaray SK | FIFA 15 CSV: exact_unique_full_name | `135475.png`
25707 | Francisco Manuel Rico Castro | 174859 | Francisco Manuel Rico Castro / Granada CF | FIFA 16 CSV: exact_unique_full_name | `174859.png`
25881 | Juan Antonio Rodríguez Villamuela | 147305 | Juan Antonio Rodríguez Villamuela / Getafe CF | FIFA 16 CSV: exact_unique_full_name | `147305.png`
25931 | Gonzalo Javier Rodríguez | 142780 | Gonzalo Javier Rodríguez / Fiorentina | FIFA 16 CSV: exact_unique_full_name | `142780.png`
25954 | Enzo Maresca | 10863 | Enzo Maresca / Palermo | FIFA 16 CSV: exact_unique_full_name | `010863.png`
26012 | David Navarro Pedrós | 111022 | David Navarro Pedrós / Levante UD | FIFA 16 CSV: exact_unique_full_name | `111022.png`
26023 | Juan Francisco García García | 10764 | Juan Francisco García García / Levante UD | FIFA 16 CSV: exact_unique_full_name | `010764.png`
26087 | Carlos Gurpegi Nausia | 105803 | Carlos Gurpegi Nausia / Athletic Club de Bilbao | FIFA 16 CSV: exact_unique_full_name | `105803.png`
26207 | Fabricio Coloccini | 48745 | Fabricio Coloccini / Newcastle United | FIFA 16 CSV: exact_unique_full_name | `048745.png`
26222 | José Eduardo Rosa Vale de Castro | 157947 | José Eduardo Rosa Vale e Castro / Rayo Vallecano | FIFA 16 CSV: exact_unique_name | `157947.png`
26481 | Sébastien Squillaci | 51105 | Sébastien Squillaci / Bastia | https://www.fifarosters.com/players?futid=50382753&player=51105&v=16 | `051105.png`
26607 | José Raúl Baena Urdiales | 195687 | José Raúl Baena Urdiales / Rayo Vallecano | FIFA 16 CSV: exact_unique_full_name | `195687.png`
26669 | Weligton Róbson Pena de Oliveira | 177573 | Weligton Róbson Pena de Oliveira / Málaga CF | FIFA 16 CSV: exact_unique_full_name | `177573.png`
26728 | Alberto Facundo Costa | 188791 | Alberto Facundo Costa / Genoa | FIFA 16 CSV: exact_unique_full_name | `188791.png`
26791 | Emir Spahić | 141200 | Emir Spahić / Hamburger SV | FIFA 16 CSV: exact_unique_full_name | `141200.png`
26848 | Roberto Trashorras Gayoso | 159172 | Roberto Trashorras Gayoso / Rayo Vallecano | FIFA 16 CSV: exact_unique_full_name | `159172.png`
27122 | Simão Mate | 188124 | Simão Mate Júnior / Levante UD | FIFA 16 CSV: exact_unique_name | `188124.png`
27144 | Antonio Amaya Carazo | 138497 | Antonio Amaya Carazo / Rayo Vallecano | FIFA 16 CSV: exact_unique_full_name | `138497.png`
27148 | Abraham González Casanova | 159566 | Abraham González Casanova / RCD Espanyol | FIFA 16 CSV: exact_unique_full_name | `159566.png`
27184 | Marcos Alberto Angeleri | 162951 | Marcos Alberto Angeleri / Málaga CF | FIFA 16 CSV: exact_unique_full_name | `162951.png`
27239 | Aleksandar Pantić | 216472 | Aleksandar Pantić / SD Eibar | FIFA 16 CSV: exact_unique_full_name | `216472.png`
27341 | Marcelo Alfonso Díaz Rojas | 176930 | Marcelo Alfonso Díaz Rojas / Hamburger SV | FIFA 16 CSV: exact_unique_full_name | `176930.png`
27346 | Petros Matheus dos Santos Araújo | 222709 | Petros Matheus dos Santos Araujo / Real Betis | FIFA 16 CSV: exact_unique_full_name | `222709.png`
27349 | Heiko Westermann | 52270 | Heiko Westermann / Real Betis | FIFA 16 CSV: exact_unique_full_name | `052270.png`
27403 | Santiago Vergini | 204050 | Santiago Vergini / Getafe CF | FIFA 16 CSV: exact_unique_full_name | `204050.png`
27482 | Aderllan Leandro de Jesus Santos | 213374 | Aderllan de Jesus Santos / Valencia CF | FIFA 16 CSV: exact_unique_name | `213374.png`
27526 | Rachid Aït-Atmane | 225120 | Rachid Aït-Atmane / Real Sporting de Gijón | FIFA 16 CSV: exact_unique_full_name | `225120.png`
27656 | Carl Medjani | 139836 | Carl Medjani / Trabzonspor | FIFA 16 CSV: exact_unique_full_name | `139836.png`
29057 | Renato Civelli | 152993 | Renato Civelli / LOSC Lille | FIFA 16 CSV: exact_unique_full_name | `152993.png`
29245 | Marvin Schulz | 223756 | Marvin Schulz / Borussia Mönchengladbach | FIFA 16 CSV: exact_unique_full_name | `223756.png`
29714 | Yacouba Sylla | 201917 | Yacouba Sylla / Stade Rennais FC | FIFA 16 CSV: exact_unique_full_name | `201917.png`
30287 | Ceyhun Gülselam | 180409 | Ceyhun Gülselam / Hannover 96 | FIFA 16 CSV: exact_unique_full_name | `180409.png`
30439 | Tolga Ciğerci | 200754 | Tolga Ciğerci / Hertha BSC | FIFA 16 CSV: exact_unique_full_name | `200754.png`
30447 | Jean-Armel Kana-Biyik | 183975 | Jean-Armel Kana-Biyik / Toulouse Football Club | FIFA 16 CSV: exact_unique_full_name | `183975.png`
30704 | Gastón Brugman | 205726 | Gaston Brugman / Palermo | FIFA 16 CSV: exact_unique_full_name | `205726.png`
30735 | Mato Jajalo | 192612 | Mato Jajalo / Palermo | FIFA 16 CSV: exact_unique_full_name | `192612.png`
30745 | Daniele Gastaldello | 137410 | Daniele Gastaldello / Bologna | FIFA 16 CSV: exact_unique_full_name | `137410.png`
30829 | Lorenzo Lollo | 209407 | Lorenzo Lollo / Carpi | FIFA 16 CSV: exact_unique_full_name | `209407.png`
30911 | Robert Gucher | 190076 | Robert Gucher / Frosinone | FIFA 16 CSV: exact_unique_full_name | `190076.png`
31174 | Jean-Daniel Akpa Akpro | 205343 | Jean-Daniel Akpa Akpro / Toulouse Football Club | FIFA 16 CSV: exact_unique_full_name | `205343.png`
31273 | Marco Crimi | 199173 | Marco Crimi / Bologna | FIFA 16 CSV: exact_unique_full_name | `199173.png`
31296 | Sébastien Aymar Bassong Nguena | 172949 | Sébastien Aymar Bassong Nguena / Norwich City | FIFA 16 CSV: exact_unique_full_name | `172949.png`
31488 | Vangelis Moras | 150035 | Vangelis Moras / Hellas Verona | FIFA 16 CSV: exact_unique_full_name | `150035.png`
31572 | Luca Marrone | 194753 | Luca Marrone / Carpi | FIFA 16 CSV: exact_unique_full_name | `194753.png`
31911 | Damjan Đoković | 205983 | Damjan Djoković / GFC Ajaccio | FIFA 16 CSV: exact_unique_full_name | `205983.png`
32119 | Leandro Greco | 144511 | Leandro Greco / Hellas Verona | FIFA 16 CSV: exact_unique_full_name | `144511.png`
32807 | Fredy Alejandro Guarín Vásquez | 169051 | Fredy Alejandro Guarín Vásquez / Inter | FIFA 16 CSV: exact_unique_full_name | `169051.png`
33311 | Ogenyi Eddy Onazi | 202934 | Ogenyi Eddy Onazi / Lazio | FIFA 16 CSV: exact_unique_full_name | `202934.png`
34558 | Sereso Geoffroy Gonzaroua Dié | 188768 | Sereso Geoffroy Gonzaroua Dié / VfB Stuttgart | FIFA 16 CSV: exact_unique_full_name | `188768.png`
35033 | Slobodan Rajković | 183606 | Slobodan Rajković / Hamburger SV | FIFA 15 CSV: exact_unique_full_name | `183606.png`
36359 | Carlos Augusto Zambrano Ochandarte | 187132 | Carlos Augusto Zambrano Ochandarte / Eintracht Frankfurt | FIFA 16 CSV: exact_unique_full_name | `187132.png`
36364 | Dávid Ivan | 228516 | David Ivan / Sampdoria | FIFA 16 CSV: exact_unique_full_name | `228516.png`
38172 | Toni Šunjić | 201343 | Toni Šunjić / VfB Stuttgart | FIFA 16 CSV: exact_unique_full_name | `201343.png`
38237 | Gabriel Alejandro Paletta | 165526 | Gabriel Alejandro Paletta / Atalanta | FIFA 16 CSV: exact_unique_full_name | `165526.png`
38412 | Kolo Habib Touré | 119152 | Kolo Habib Touré / Liverpool | FIFA 16 CSV: exact_unique_full_name | `119152.png`
40121 | Philipp Wollscheid | 198202 | Philipp Wollscheid / Stoke City | FIFA 16 CSV: exact_unique_full_name | `198202.png`
40123 | Robert Huth | 137785 | Robert Huth / Leicester City | FIFA 16 CSV: exact_unique_full_name | `137785.png`
40251 | Daniele Croce | 137406 | Daniele Croce / Empoli | FIFA 16 CSV: exact_unique_full_name | `137406.png`
40349 | Ivaylo Chochev | 224202 | Ivaylo Chochev / Palermo | FIFA 16 CSV: exact_unique_full_name | `224202.png`
40350 | Siniša Anđelković | 202058 | Siniša Anđelković / Palermo | FIFA 16 CSV: exact_unique_full_name | `202058.png`
40351 | Alessandro Gazzi | 137378 | Alessandro Gazzi / Torino | FIFA 16 CSV: exact_unique_full_name | `137378.png`
40367 | Francesco Lodi | 120238 | Francesco Lodi / Parma | FIFA 15 CSV: exact_unique_full_name | `120238.png`
40426 | Guglielmo Stendardo | 149147 | Guglielmo Stendardo / Atalanta | FIFA 16 CSV: exact_unique_full_name | `149147.png`
40427 | Cesare Bovo | 105866 | Cesare Bovo / Torino | FIFA 16 CSV: exact_unique_full_name | `105866.png`
40430 | Giuseppe Vives | 178425 | Giuseppe Vives / Torino | FIFA 16 CSV: exact_unique_full_name | `178425.png`
40459 | Roger de Oliveira Bernardo | 193985 | Roger de Oliveira Bernardo / FC Ingolstadt 04 | FIFA 16 CSV: exact_unique_full_name | `193985.png`
40467 | Peter Niemeyer | 54018 | Peter Niemeyer / SV Darmstadt 98 | FIFA 16 CSV: exact_unique_full_name | `054018.png`
40468 | Cleber Janderson Pereira Reis | 208895 | Cleber Janderson Pereira Reis / Hamburger SV | FIFA 16 CSV: exact_unique_full_name | `208895.png`
40470 | Georg Niedermeier | 189922 | Georg Niedermeier / VfB Stuttgart | FIFA 16 CSV: exact_unique_full_name | `189922.png`
40474 | Jens Hegeler | 189235 | Jens Hegeler / Hertha BSC | FIFA 16 CSV: exact_unique_full_name | `189235.png`
40522 | Rio Antonio Zoba Mavuba | 150656 | Rio Antonio Zoba Mavuba / LOSC Lille | FIFA 16 CSV: exact_unique_full_name | `150656.png`
40523 | Marko Baša | 192615 | Marko Baša / LOSC Lille | FIFA 16 CSV: exact_unique_full_name | `192615.png`
40527 | Brou Benjamin Angoua | 196580 | Brou Benjamin Angoua / En Avant de Guingamp | FIFA 16 CSV: exact_unique_full_name | `196580.png`
40543 | Jeong-Ho Hong | 200588 | 홍정호 洪正好 / FC Augsburg | FIFA 16 CSV: exact_unique_name | `200588.png`
40697 | Mounir Obbadi | 158127 | Mounir Obbadi / LOSC Lille | FIFA 16 CSV: exact_unique_full_name | `158127.png`
40698 | Nicolas Seube | 50908 | Nicolas Seube / Stade Malherbe Caen | FIFA 16 CSV: exact_unique_full_name | `050908.png`
40699 | Sylvain Armand | 41674 | Sylvain Armand / Stade Rennais FC | FIFA 16 CSV: exact_unique_full_name | `041674.png`
40945 | Alex Rodrigo Dias da Costa | 136130 | Alex Rodrigo Dias da Costa / Milan | FIFA 16 CSV: exact_unique_full_name | `136130.png`
42422 | Dušan Veškovac | 186538 | Dušan Veškovac / ESTAC Troyes | FIFA 16 CSV: exact_unique_full_name | `186538.png`
42700 | Micah Richards | 169721 | Micah Richards / Aston Villa | FIFA 16 CSV: exact_unique_full_name | `169721.png`
42900 | Cheik Ismaël Tioté | 170783 | Cheik Ismaël Tioté / Newcastle United | FIFA 16 CSV: exact_unique_full_name | `170783.png`
45590 | Nicolò Cherubin | 183365 | Nicolò Cherubin / Atalanta | FIFA 16 CSV: exact_unique_full_name | `183365.png`
46670 | Iván Rodrigo Piris Leguizamón | 204977 | Iván Rodrigo Piris Leguizamón / Udinese | FIFA 16 CSV: exact_unique_full_name | `204977.png`
46801 | Jaba Kankava | 167194 | Jaba Kankava / Stade de Reims | FIFA 16 CSV: exact_unique_full_name | `167194.png`
47881 | Marcel  Hilßner | 231197 | Marcel Hilßner / SG Dynamo Dresden | FIFA 17 CSV: exact_unique_full_name | `231197.png`
51388 | Assani Lukimya-Mulongoti | 184852 | Assani Lukimya-Mulongoti / SV Werder Bremen | FIFA 16 CSV: exact_unique_full_name | `184852.png`
131849 | Antoine Conte | 213021 | Antoine Conte / Stade de Reims | FIFA 16 CSV: exact_unique_full_name | `213021.png`
174418 | Modibo Diakité | 177643 | Modibo Diakité / Frosinone | FIFA 16 CSV: exact_unique_full_name | `177643.png`
352172 | Raffaele Bianco | 184320 | Raffaele Bianco / Carpi | FIFA 16 CSV: exact_unique_full_name | `184320.png`
386509 | Adriano Russo | 137419 | Adriano Russo / Frosinone | FIFA 16 CSV: exact_unique_full_name | `137419.png`
386512 | Alessandro Frara | 101904 | Alessandro Frara / Frosinone | FIFA 16 CSV: exact_unique_full_name | `101904.png`
386657 | Giampiero Pinzi | 164 | Giampiero Pinzi / Udinese | FIFA 15 CSV: exact_unique_full_name | `000164.png`
387300 | Cristian Zaccardo | 49617 | Cristian Zaccardo / Milan | FIFA 15 CSV: exact_unique_full_name | `049617.png`
387417 | Mattia Cassani | 137380 | Mattia Cassani / Sampdoria | FIFA 16 CSV: exact_unique_full_name | `137380.png`
387847 | Leonardo Blanchard | 203745 | Leonardo Blanchard / Frosinone | FIFA 16 CSV: exact_unique_full_name | `203745.png`
400613 | Leon Andreasen | 130687 | Leon Andreasen / Hannover 96 | FIFA 16 CSV: exact_unique_full_name | `130687.png`
400614 | Christian Schulz | 121185 | Christian Schulz / Hannover 96 | FIFA 16 CSV: exact_unique_full_name | `121185.png`
401194 | François Modesto | 105471 | François Modesto / Bastia | https://wefut.com/player/generations/105471 | `105471.png`
401455 | Mohamed Fofana | 173033 | Mohamed Fofana / Stade de Reims | FIFA identity reference CSVs; name variant and recorded club reviewed | `173033.png`
401468 | Moustapha Bayal Sall | 178679 | Moustapha Bayal Sall / AS Saint-Étienne | FIFA 16 CSV: exact_unique_full_name | `178679.png`
401478 | Rémi Gomis | 112352 | Rémi Gomis / FC Nantes | FIFA 16 CSV: exact_unique_full_name | `112352.png`
401479 | Calvin Anele Ngcongca | 186564 | Calvin Anele Ngcongca / ESTAC Troyes | FIFA 16 CSV: exact_unique_full_name | `186564.png`
401507 | Jérôme Le Moigne | 177128 | Jérôme Le Moigne / GFC Ajaccio | FIFA 16 CSV: exact_unique_full_name | `177128.png`
401509 | David Ducourtioux | 117492 | David Ducourtioux / GFC Ajaccio | FIFA 16 CSV: exact_unique_full_name | `117492.png`
401512 | Lionel Mathis | 41634 | Lionel Mathis / En Avant de Guingamp | FIFA 16 CSV: exact_unique_full_name | `041634.png`

Player likenesses and source artwork belong to their respective rights holders.

## Fallback image sources

Player | Edition | Original image URL
--- | --- | ---
Alberto Grassi | FIFA 17 | https://cdn.sofifa.net/players/220/475/17_240.png
Amadou Diawara | FIFA 17 | https://cdn.sofifa.net/players/230/613/17_240.png
Cédric Yambéré | FIFA 17 | https://cdn.sofifa.net/players/225/934/17_240.png
Frédéric Guilbert | FIFA 17 | https://cdn.sofifa.net/players/227/222/17_240.png
Gonzalo Escalante | FIFA 17 | https://cdn.sofifa.net/players/219/391/17_240.png
Hotaru Yamaguchi | FIFA 18 | https://cdn.sofifa.net/players/222/987/18_240.png
Issa Diop | FIFA 17 | https://cdn.sofifa.net/players/231/633/17_240.png
Jaba Kankava | FIFA 17 | https://cdn.sofifa.net/players/167/194/17_240.png
László Kleinheisler | FIFA 17 | https://cdn.sofifa.net/players/231/493/17_240.png
Marcel  Hilßner | FIFA 17 | https://cdn.sofifa.net/players/231/197/17_240.png
Pablo Fornals Malla | FIFA 17 | https://cdn.sofifa.net/players/226/456/17_240.png
Pablo Nascimento Castro | FIFA 17 | https://cdn.sofifa.net/players/201/315/17_240.png
Petros Matheus dos Santos Araújo | FIFA 17 | https://cdn.sofifa.net/players/222/709/17_240.png
